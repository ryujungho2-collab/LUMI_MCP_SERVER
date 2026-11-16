from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send
import hashlib
import hmac
import json
import os
import re

MCP_API_TOKEN = os.environ.get("MCP_API_TOKEN")
MCP_TOKENS_JSON = os.environ.get("MCP_TOKENS_JSON")
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")


def load_member_token_hashes(raw: str | None) -> dict[str, str]:
    """Load {member_id: sha256(token)} entries from the environment."""
    if raw is None or not raw.strip():
        return {}

    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("MCP_TOKENS_JSON must contain a valid JSON object.") from exc

    if not isinstance(entries, dict) or not entries:
        raise RuntimeError("MCP_TOKENS_JSON must be a non-empty JSON object.")

    validated: dict[str, str] = {}
    for member_id, token_hash in entries.items():
        if not isinstance(member_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]{1,64}", member_id
        ):
            raise RuntimeError("MCP_TOKENS_JSON contains an invalid member ID.")

        if not isinstance(token_hash, str) or not re.fullmatch(
            r"[0-9a-fA-F]{64}", token_hash
        ):
            raise RuntimeError(
                f"MCP_TOKENS_JSON contains an invalid SHA-256 hash for {member_id!r}."
            )

        validated[member_id] = token_hash.lower()

    return validated


MEMBER_TOKEN_HASHES = load_member_token_hashes(MCP_TOKENS_JSON)

mcp = FastMCP(
    "my-mcp-server",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=bool(RENDER_EXTERNAL_HOSTNAME),
        allowed_hosts=[RENDER_EXTERNAL_HOSTNAME] if RENDER_EXTERNAL_HOSTNAME else [],
    ),
)


# Add tools below. The docstring is surfaced to LLMs as the tool description.
# Type hints define the JSON schema for parameters.
@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


# custom_route bypasses auth — use only for public endpoints
@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok"})


class BearerAuthMiddleware:
    """Authenticate either an individual member token or a legacy shared token."""

    def __init__(
        self,
        app: ASGIApp,
        member_token_hashes: dict[str, str] | None = None,
        legacy_token: str | None = None,
    ) -> None:
        self.app = app
        self.member_token_hashes = member_token_hashes or {}
        self.legacy_token = legacy_token

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        scheme, separator, presented_token = auth_header.partition(" ")

        member_id = None
        if separator and scheme.lower() == "bearer" and presented_token:
            if self.member_token_hashes:
                presented_hash = hashlib.sha256(
                    presented_token.encode("utf-8")
                ).hexdigest()

                for candidate_id, stored_hash in self.member_token_hashes.items():
                    if hmac.compare_digest(presented_hash, stored_hash):
                        member_id = candidate_id
                        break
            elif self.legacy_token and hmac.compare_digest(
                presented_token, self.legacy_token
            ):
                # Compatibility mode for the original single shared token.
                member_id = "shared"

        if member_id is not None:
            # Available to downstream ASGI middleware/routes for identity-aware
            # logging or future authorization checks. Never store the raw token.
            scope.setdefault("state", {})["mcp_member_id"] = member_id
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32001, "message": "Unauthorized"},
                "id": None,
            },
            status_code=401,
        )
        await response(scope, receive, send)


def create_app():
    app = mcp.streamable_http_app()

    if MEMBER_TOKEN_HASHES:
        # Per-member mode takes precedence. The legacy shared token is rejected.
        app.add_middleware(
            BearerAuthMiddleware,
            member_token_hashes=MEMBER_TOKEN_HASHES,
        )
    elif MCP_API_TOKEN:
        # Backward compatibility until per-member tokens are configured.
        app.add_middleware(
            BearerAuthMiddleware,
            legacy_token=MCP_API_TOKEN,
        )
    elif RENDER_EXTERNAL_HOSTNAME:
        # Fail closed on Render: never deploy a public unauthenticated MCP server.
        raise RuntimeError(
            "Authentication is not configured. Set MCP_TOKENS_JSON or MCP_API_TOKEN."
        )

    return app


if __name__ == "__main__":
    import uvicorn

    if not MEMBER_TOKEN_HASHES and not MCP_API_TOKEN:
        print(
            "WARNING: No MCP authentication is configured. "
            "Authentication is disabled for local development."
        )

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
