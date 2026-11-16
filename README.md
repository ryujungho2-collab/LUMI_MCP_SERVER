# LUMI MCP Server (Python)

A remote MCP server for the LUMI team, built with the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) and deployed on [Render](https://render.com). It uses Streamable HTTP transport and runs stateless.

## What's included

- MCP server using the MCP Python SDK
- Per-member bearer-token authentication, with legacy single-token compatibility
- A `/health` endpoint for Render health checks
- A token generator that prints a member token and its SHA-256 hash
- Example tool (`hello`) to verify connectivity

> **Note:** Render free services spin down after 15 minutes of inactivity. The next request may take 30-60 seconds while the service wakes up.

## Authentication model

The server supports two modes:

1. **Per-member mode:** `MCP_TOKENS_JSON` contains a JSON object mapping each member ID to the SHA-256 hash of that member's token.
2. **Legacy mode:** `MCP_API_TOKEN` is a single shared token. This remains available as a migration fallback until `MCP_TOKENS_JSON` is configured.

When `MCP_TOKENS_JSON` is configured, it takes precedence and the old shared `MCP_API_TOKEN` is no longer accepted.

The server stores only token hashes in `MCP_TOKENS_JSON`; each member keeps their actual token in their own local `.env` file. The `/health` endpoint remains public for Render health checks.

### Add a team member

1. Generate a unique token locally:

   ```powershell
   python scripts/generate_member_token.py member_id
   ```

   Replace `member_id` with a short identifier, such as `alice` or `member_02`.

2. The script prints:
   - The **token**: send this privately to that member. They put it in their local `.env` file as `LUMI_MCP_TOKEN=...`.
   - The **SHA-256 hash**: add this to the `MCP_TOKENS_JSON` value in Render.

3. In **Render Dashboard → my-mcp-server → Environment**, set `MCP_TOKENS_JSON` to a JSON object. For example:

   ```json
   {"alice":"<alice_sha256_hash>","member_02":"<member_02_sha256_hash>"}
   ```

   Keep all active members in the object. Save the variable; Render will restart the service.

4. The member's client configuration references the local environment variable, not the token literal:

   ```json
   {
     "mcpServers": {
       "lumi": {
         "type": "http",
         "url": "https://my-mcp-server-3n1j.onrender.com/mcp",
         "headers": {
           "Authorization": "Bearer ${LUMI_MCP_TOKEN}"
         }
       }
     }
   }
   ```

   The member's local `.env` contains:

   ```env
   LUMI_MCP_TOKEN=their_personal_token
   ```

   Make sure `.env` is in `.gitignore`. Do not commit or post actual tokens.

### Revoke a member

Remove that member's ID/hash pair from `MCP_TOKENS_JSON` in Render and save. The service restarts and that member's token is rejected. Other members' tokens remain valid.

### Current authorization scope

Individual tokens provide identity and individual revocation. At this stage, all authenticated members can use the same MCP tools; role-based or tool-level permissions are not implemented yet.

### Legacy single-token mode

If `MCP_TOKENS_JSON` is not set, the server accepts `MCP_API_TOKEN` as the original shared token. This is useful during migration. Once per-member tokens are configured, the shared token is ignored.

For local server development, you can set `MCP_API_TOKEN` in a local environment. If no token is configured locally, authentication is disabled. On Render, the server refuses to start without authentication configured.

## Deploying

The service is configured in `render.yaml`. This repository uses `autoDeploy: false`, so after pushing changes to GitHub, open Render and select **Manual Deploy → Deploy latest commit**.

The MCP endpoint is:

```
https://my-mcp-server-3n1j.onrender.com/mcp
```

Health check:

```
https://my-mcp-server-3n1j.onrender.com/health
```

## Running locally

```powershell
pip install -r requirements.txt
$env:MCP_API_TOKEN = "local-test-token"
python server.py
```

The server starts on `http://localhost:10000`.

## Running tests

```powershell
pip install -r requirements.txt
pytest
```

## Project structure

```
server.py                         MCP server, tools, auth middleware
scripts/generate_member_token.py  Per-member token generator
tests/test_server.py              Auth, health, and tool tests
requirements.txt                  Python dependencies
render.yaml                       Render deployment configuration
.env.example                      Local server environment example
.gitignore                        Excludes local secrets
AGENTS.md                         Instructions for AI coding assistants
```

## Adding tools

Add tools to `server.py` by decorating a function with `@mcp.tool()`:

```python
@mcp.tool()
def your_tool_name(param: str) -> str:
    """Describe what this tool does."""
    return "result"
```

The docstring becomes the tool description shown to MCP clients. Use type hints for all parameters and return values.

## References

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP specification](https://modelcontextprotocol.io/)
- [Render Environment Variables](https://render.com/docs/configure-environment-variables)
