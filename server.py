from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send
import hmac
import os

MCP_API_TOKEN = os.environ.get("MCP_API_TOKEN")
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

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


# 팀원 온보딩용 임시 도구: 인증된 MCP 요청이 실제로 실행되는지 확인한다.
@mcp.tool()
def verify_connection(message: str = "ping") -> str:
    """LUMI MCP 연결 검증용 임시 도구. 토큰이 아닌 임의의 테스트 메시지를 전달하세요."""
    return f"LUMI_CONNECTION_OK: {message}"


# custom_route bypasses auth — use only for public endpoints
@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok"})


class BearerAuthMiddleware:
    """Authenticate requests with one shared Bearer token."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        scheme, separator, presented_token = auth_header.partition(" ")

        if (
            separator
            and scheme.lower() == "bearer"
            and presented_token
            and hmac.compare_digest(presented_token, self.token)
        ):
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

    if MCP_API_TOKEN:
        app.add_middleware(BearerAuthMiddleware, token=MCP_API_TOKEN)
    elif RENDER_EXTERNAL_HOSTNAME:
        # Fail closed on Render: never deploy a public unauthenticated MCP server.
        raise RuntimeError(
            "Authentication is not configured. Set MCP_API_TOKEN."
        )

    return app


if __name__ == "__main__":
    import uvicorn

    if not MCP_API_TOKEN:
        print(
            "WARNING: No MCP authentication is configured. "
            "Authentication is disabled for local development."
        )

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
