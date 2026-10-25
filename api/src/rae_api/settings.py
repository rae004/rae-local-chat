from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from rae_api.services.mcp import McpServerConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://workhorse:11434"
    ollama_model: str = "qwen2.5-coder:latest"
    # Seconds between bytes before we give up; None = wait forever for a slow model.
    ollama_read_timeout: float | None = 120.0
    cors_origins: list[str] = ["http://localhost:5173"]

    # MCP servers reachable over Streamable HTTP, as JSON:
    #   MCP_SERVERS='[{"name":"filesystem","url":"http://mcp-filesystem:8000/mcp"}]'
    mcp_servers: list[McpServerConfig] = []
    # GitHub's hosted MCP server is added automatically when a PAT is set.
    github_personal_access_token: str | None = None
    github_mcp_url: str = "https://api.githubcopilot.com/mcp/"
    tools_enabled: bool = True
    tool_result_max_chars: int = 16_000
    agent_max_rounds: int = 10

    def all_mcp_servers(self) -> list[McpServerConfig]:
        servers = list(self.mcp_servers)
        if self.github_personal_access_token:
            servers.append(
                McpServerConfig(
                    name="github",
                    url=self.github_mcp_url,
                    headers={"Authorization": f"Bearer {self.github_personal_access_token}"},
                )
            )
        return servers


@lru_cache
def get_settings() -> Settings:
    return Settings()
