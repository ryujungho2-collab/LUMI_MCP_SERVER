from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send
import hmac
import os
import json
import subprocess
import sys
import threading
from urllib.parse import urlparse
from pathlib import Path
from typing import Literal

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


# Limit concurrent work so small Render instances do not run multiple video engines at once.
_video_lock = threading.Lock()


@mcp.tool()
def recommend_video_input(source: str, clip_count: int = 1, contiguous: bool = False) -> dict:
    """Classify a YouTube link, HTTP video URL or local file and recommend a clip workflow; does not download video."""
    if not source or clip_count < 1 or clip_count > 10000:
        raise ValueError("source must not be empty and clip_count must be 1–10000")
    parsed = urlparse(source)
    host = (parsed.hostname or "").lower()
    if parsed.scheme in ("http", "https") and (host in ("youtu.be", "youtube.com", "www.youtube.com", "m.youtube.com") or host.endswith(".youtube.com")):
        kind = "youtube"
    elif parsed.scheme in ("http", "https"):
        kind = "url"
    else:
        kind = "local_file"
    return {"source_type": kind, "clip_count": clip_count, "contiguous": contiguous,
            "recommended": "Obtain authorized MP4 clip bytes and send each as base64 to analyze_pse_clip or dim_pse_clip.",
            "limits": "At most 1 MiB, 120 frames, 76,800 pixels per frame, and 60 fps per clip.",
            "youtube": "A YouTube URL is not a video clip; this server does not download YouTube videos.",
            "boundary_warning": "Independent clips do not detect events spanning clip boundaries. 5-second extended detection requires temporal context. Overlap helps but is not equivalent to continuous analysis." if clip_count > 1 else "A short clip may not contain sufficient temporal context.",
            "remote_tools_available": True}


def _run_video_clip(video_base64: str, action: str, l_max: float, profile: str, mode: str = "base") -> dict:
    if len(video_base64) > 1398104:
        raise ValueError("Base64-encoded clip exceeds the 1 MiB input limit.")
    if not _video_lock.acquire(blocking=False):
        raise ValueError("A video job is already running; try again later.")
    try:
        request = json.dumps({"video_base64": video_base64, "action": action, "l_max": l_max, "profile": profile, "mode": mode})
        try:
            proc = subprocess.run([sys.executable, str(Path(__file__).with_name("remote_worker.py"))],
                                  input=request, text=True, capture_output=True, timeout=180,
                                  env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        except subprocess.TimeoutExpired:
            raise ValueError("Video analysis timed out after 180 seconds.") from None
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise ValueError("Video worker failed; the server may lack resources or required dependencies.") from None
        if proc.returncode or "error" in result:
            raise ValueError(result.get("error", "Video worker failed."))
        return result
    finally:
        _video_lock.release()


@mcp.tool()
def analyze_pse_clip(video_base64: str, l_max: float = 200.0,
                     profile: Literal["laptop", "desktop", "tv"] = "laptop") -> dict:
    """Analyze one base64 MP4 clip using the enhanced partial B2 detector. Experimental SDR model; no safety guarantee. See recommend_video_input for limits."""
    return _run_video_clip(video_base64, "analyze", l_max, profile)


@mcp.tool()
def dim_pse_clip(video_base64: str, l_max: float = 200.0,
                 profile: Literal["laptop", "desktop", "tv"] = "laptop",
                 mode: Literal["base", "hold", "safe"] = "base") -> dict:
    """Dim one MP4 with partial B2 and return output_mp4_base64 with the first source audio stream as AAC when present."""
    return _run_video_clip(video_base64, "dim", l_max, profile, mode)


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
