# LUMI MCP Server — Agent Guide

This repository contains the LUMI team's remote MCP server, built with the MCP Python SDK and deployed on Render. It uses Streamable HTTP transport and runs stateless.

## Project layout

- `server.py` — MCP tools, health check, bearer-token authentication, and ASGI app
- `scripts/generate_member_token.py` — creates a high-entropy member token and prints its SHA-256 hash
- `tests/test_server.py` — auth, health, and tool-call tests
- `requirements.txt` — Python dependencies
- `render.yaml` — Render deployment configuration

## Authentication

The preferred authentication mode is per-member bearer tokens.

- Render environment variable `MCP_TOKENS_JSON` contains a JSON object mapping `member_id` to the SHA-256 hash of that member's token.
- Each member keeps the raw token locally as `LUMI_MCP_TOKEN` in their own `.env` file.
- The MCP client sends `Authorization: Bearer <token>`.
- The middleware validates the hash and sets `scope["state"]["mcp_member_id"]` for downstream identity-aware logic.
- When `MCP_TOKENS_JSON` is configured, it takes precedence over the legacy `MCP_API_TOKEN`; the shared token is rejected.
- Remove a member's mapping from `MCP_TOKENS_JSON` to revoke only that member's token.
- All members currently have the same tool permissions. Do not claim role-based authorization exists unless it is implemented.

The original `MCP_API_TOKEN` remains as a migration fallback when `MCP_TOKENS_JSON` is absent. `/health` is intentionally public for Render health checks. On Render, fail startup if neither authentication mode is configured; do not deploy an unauthenticated public MCP endpoint.

Never commit raw tokens or put them in source code, logs, tests, or documentation.

## Adding a tool

Add tools to `server.py` by decorating a function with `@mcp.tool()`. Insert new tools after the existing tool definitions and before the `@mcp.custom_route` health check.

### Pattern

```python
@mcp.tool()
def your_tool_name(param: str, count: int = 10) -> str:
    """One-line description of what this tool does (shown to LLMs)."""
    return "result"
```

Rules:
- Use snake_case for tool function names.
- Always include a clear docstring.
- Use type hints for all parameters and return values.
- Return strings for simple results; use `json.dumps(...)` for structured data.

## Deployment

Push changes to the GitHub repository. Because `autoDeploy: false` is configured, manually trigger **Render Dashboard → Manual Deploy → Deploy latest commit**.

## Tests

Run:

```bash
pip install -r requirements.txt
pytest
```

When changing authentication, add tests for valid member tokens, invalid tokens, legacy-token rejection in per-member mode, and the public health endpoint.
