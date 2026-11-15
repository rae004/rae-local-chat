from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.server import MCPServer
from mcp.types import TextContent

from rae_mcp_shell.server import create_server


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "notes.txt").write_text("buy milk\nTODO call mom\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("# TODO fix\nprint(1)\n")
    (tmp_path / "big.txt").write_text("x" * 5000)
    (tmp_path.parent / "secret.txt").write_text("outside\n")
    return tmp_path


@pytest.fixture
def client(workspace: Path) -> MCPServer:
    """The in-process server; `call` opens a client per call (anyio scopes stay in one task)."""
    return create_server(workspace, timeout=0.5, output_cap=1000)


async def call(server: MCPServer, **args: Any) -> tuple[bool, str]:
    async with Client(server) as c:
        res = await c.call_tool("run", args)
    text = "".join(c.text for c in res.content if isinstance(c, TextContent))
    return bool(res.is_error), text


async def test_tool_is_not_read_only(client: MCPServer) -> None:
    async with Client(client) as c:
        tools = (await c.list_tools()).tools
    assert [t.name for t in tools] == ["run"]
    assert tools[0].annotations is not None and tools[0].annotations.read_only_hint is False


async def test_ls_and_grep(client: MCPServer) -> None:
    err, out = await call(client, command="ls")
    assert not err and "notes.txt" in out and "src" in out
    err, out = await call(client, command="grep", args=["-rn", "TODO", "."])
    assert not err and "notes.txt:2:TODO call mom" in out and "src/a.py:1:# TODO fix" in out


async def test_grep_no_match_is_not_an_error(client: MCPServer) -> None:
    err, out = await call(client, command="grep", args=["-rn", "UNICORN", "."])
    assert not err and out == "(no matches)"


async def test_cwd_inside_workspace(client: MCPServer) -> None:
    err, out = await call(client, command="cat", args=["a.py"], cwd="src")
    assert not err and "print(1)" in out


@pytest.mark.parametrize("cwd", ["..", "../", "/", "/etc", "src/../.."])
async def test_cwd_escape_rejected(client: MCPServer, cwd: str) -> None:
    err, out = await call(client, command="ls", cwd=cwd)
    assert err and "outside the workspace" in out


@pytest.mark.parametrize("arg", ["../secret.txt", "/etc/passwd", "src/../../secret.txt"])
async def test_path_argument_escape_rejected(client: MCPServer, arg: str) -> None:
    err, out = await call(client, command="cat", args=[arg])
    assert err and "outside the workspace" in out


async def test_disallowed_command(client: MCPServer) -> None:
    err, out = await call(client, command="rm", args=["-rf", "."])
    assert err and "not allowed" in out
    err, out = await call(client, command="sh", args=["-c", "echo hi"])
    assert err and "not allowed" in out


async def test_git_subcommands(client: MCPServer) -> None:
    err, out = await call(client, command="git", args=["push"])
    assert err and "subcommands" in out
    err, out = await call(client, command="git", args=["-c", "x=y", "status"])
    assert err and "subcommands" in out
    # Not a repo, so git fails — but it was *allowed* to run.
    err, out = await call(client, command="git", args=["status"])
    assert not err and "[exit 128]" in out


async def test_find_exec_rejected(client: MCPServer) -> None:
    bad = [".", "-name", "*.py", "-exec", "rm", "{}", ";"]
    err, out = await call(client, command="find", args=bad)
    assert err and "-exec" in out
    err, out = await call(client, command="find", args=[".", "-name", "*.py"])
    assert not err and "./src/a.py" in out


async def test_output_cap_and_exit_code(client: MCPServer) -> None:
    err, out = await call(client, command="cat", args=["big.txt"])
    assert not err and "truncated, 5000 chars total" in out and len(out) < 1200
    err, out = await call(client, command="cat", args=["missing.txt"])
    assert not err and "[exit 1]" in out


async def test_timeout(client: MCPServer) -> None:
    err, out = await call(client, command="tail", args=["-f", "notes.txt"])
    assert err and "did not finish within 0.5s" in out


async def test_no_shell_interpretation(client: MCPServer) -> None:
    err, out = await call(client, command="ls", args=["; cat /etc/passwd"])
    # Treated as a literal filename, which doesn't exist.
    assert not err and "[exit" in out and "root:" not in out
