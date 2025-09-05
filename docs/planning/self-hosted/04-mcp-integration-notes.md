# MCP Integration Notes (Planning)

Goal
- Clear guidance for using external MCP servers in self-hosted, multi-tenant deployments.

Key Points
- Prefer SHTTP/SSE MCP servers for multi-tenant web deployments so auth tokens stay with the external MCP service, not in OpenHands process env.
- Use stdio MCP only for local CLI users.

Configuration
- Global via config.toml under [mcp]: sse_servers, shttp_servers.
- Per-user via Settings.secrets_store and Settings.mcp_config merge.

Gitea MCP
- External: run gitea-mcp as an SHTTP/SSE service; add to config or user settings.
- CLI convenience: GITEA_MCP_ENABLE=1 auto-injects stdio (OpenHandsMCPConfig).

Security
- Avoid injecting provider tokens into OpenHands env when multi-tenant; prefer external MCP with its own auth.

Testing
- Confirm MCP tool discovery and usage inside agent sessions (RemoteRuntime). Verify masking of secrets in EventStream.
