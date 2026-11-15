"""rae-mcp-shell: one `run` tool that executes allowlisted commands inside /workspace.

Defence in depth: this module checks the command, its arguments and the working
directory; docker-compose adds a read-only workspace mount, read-only root
filesystem, dropped capabilities and a pid limit. The tool is *not* marked
read-only, so the chat UI asks the user before every call.
"""

import asyncio
import os
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

ALLOWED = frozenset({"ls", "cat", "head", "tail", "grep", "rg", "find", "wc", "git"})
GIT_SUBCOMMANDS = frozenset({"status", "log", "diff", "show", "grep", "branch"})
# find can execute or write via these; the read-only mount makes them fail anyway,
# but refusing is clearer than a cryptic error.
FIND_FORBIDDEN = frozenset(
    {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
)
ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "C.UTF-8",
    "PAGER": "cat",
    "GIT_PAGER": "cat",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
}


class Rejected(ToolError):
    """The request violates the sandbox rules. ToolError subclasses keep their message
    when the SDK turns them into an is_error result; anything else is masked."""


def validate(command: str, args: list[str]) -> list[str]:
    if command not in ALLOWED:
        raise Rejected(f"'{command}' is not allowed. Allowed: {', '.join(sorted(ALLOWED))}")
    if command == "git" and (not args or args[0] not in GIT_SUBCOMMANDS):
        allowed = ", ".join(sorted(GIT_SUBCOMMANDS))
        raise Rejected(f"git needs one of these subcommands first: {allowed}")
    if command == "find":
        bad = FIND_FORBIDDEN.intersection(args)
        if bad:
            raise Rejected(f"find options not allowed: {', '.join(sorted(bad))}")
    return [command, *args]


def resolve_inside(workspace: Path, cwd: Path, candidate: str) -> Path:
    """`candidate` resolved against `cwd`; must stay inside the workspace."""
    path = (cwd / candidate).resolve()
    if path != workspace and workspace not in path.parents:
        raise Rejected(f"'{candidate}' is outside the workspace")
    return path


def check_paths(workspace: Path, cwd: Path, args: list[str]) -> None:
    """Any argument that looks like a path must resolve inside the workspace."""
    for arg in args:
        if arg.startswith("-"):
            continue
        if arg.startswith("/") or "/" in arg or arg in {".", ".."} or arg.startswith(".."):
            resolve_inside(workspace, cwd, arg)


def create_server(workspace: Path, *, timeout: float = 30.0, output_cap: int = 20_000) -> MCPServer:
    workspace = workspace.resolve()
    mcp = MCPServer(
        "rae-shell",
        instructions=(
            "Runs read-only shell commands inside the project workspace. "
            f"Allowed commands: {', '.join(sorted(ALLOWED))}. No pipes, no redirects, "
            "no shell syntax: pass arguments as a list."
        ),
    )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Run shell command",
            read_only_hint=False,  # every call asks the user first
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        )
    )
    async def run(command: str, args: list[str] | None = None, cwd: str = ".") -> str:
        """Run an allowlisted command (ls, cat, head, tail, grep, rg, find, wc, git) inside
        the workspace. `args` is the argument list, `cwd` a directory relative to the
        workspace root. Output is capped; a non-zero exit code is appended."""
        args = args or []
        argv = validate(command, args)
        directory = resolve_inside(workspace, workspace, cwd)
        if not directory.is_dir():
            raise Rejected(f"'{cwd}' is not a directory")
        check_paths(workspace, directory, args)

        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=directory,
            env=ENV,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            async with asyncio.timeout(timeout):
                raw, _ = await proc.communicate()
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise Rejected(f"'{command}' did not finish within {timeout:g}s") from None

        text = raw.decode("utf-8", errors="replace")
        if len(text) > output_cap:
            text = text[:output_cap] + f"\n…[truncated, {len(text)} chars total]"
        if command in {"grep", "rg"} and proc.returncode == 1 and not text:
            return "(no matches)"  # exit 1 is grep for "nothing found", not an error
        if proc.returncode:
            text += f"\n[exit {proc.returncode}]"
        return text or "(no output)"

    return mcp


def main() -> None:
    workspace = Path(os.environ.get("WORKSPACE", "/workspace"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104 — container-internal listener
    port = int(os.environ.get("PORT", "8000"))
    server = create_server(workspace)
    # Only other compose services reach this; the Host header is the service name.
    security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    server.run(
        "streamable-http", host=host, port=port, stateless_http=True, transport_security=security
    )


if __name__ == "__main__":
    main()
