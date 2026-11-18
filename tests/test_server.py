import os
import json
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

os.environ["MCP_API_TOKEN"] = "test-token"

import server as server_module  # noqa: E402
from server import create_app  # noqa: E402

TOKEN = "test-token"
BASE_URL = "http://localhost"
MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
INIT_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0.0"},
    },
}


def parse_sse_data(text: str) -> dict:
    """Extract the JSON payload from an SSE response."""
    for line in text.strip().splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise ValueError(f"No data line in SSE response: {text}")


@pytest.fixture(scope="module")
async def managed_app():
    """Single app with lifespan for the entire test module."""
    app = create_app()
    async with LifespanManager(app):
        yield app


@pytest.fixture
def authed_headers():
    return {**MCP_HEADERS, "Authorization": f"Bearer {TOKEN}"}


@pytest.mark.anyio
async def test_health(managed_app):
    async with AsyncClient(
        transport=ASGITransport(app=managed_app), base_url=BASE_URL
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_mcp_no_token_when_required(managed_app):
    async with AsyncClient(
        transport=ASGITransport(app=managed_app), base_url=BASE_URL
    ) as client:
        resp = await client.post("/mcp", headers=MCP_HEADERS, json=INIT_BODY)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == -32001


@pytest.mark.anyio
async def test_mcp_wrong_token(managed_app):
    headers = {**MCP_HEADERS, "Authorization": "Bearer wrong-token"}
    async with AsyncClient(
        transport=ASGITransport(app=managed_app), base_url=BASE_URL
    ) as client:
        resp = await client.post("/mcp", headers=headers, json=INIT_BODY)
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_mcp_correct_token(managed_app, authed_headers):
    async with AsyncClient(
        transport=ASGITransport(app=managed_app), base_url=BASE_URL
    ) as client:
        resp = await client.post("/mcp", headers=authed_headers, json=INIT_BODY)
    assert resp.status_code == 200
    data = parse_sse_data(resp.text)
    assert data["result"]["serverInfo"]["name"] == "my-mcp-server"


@pytest.mark.anyio
async def test_create_app_requires_token_on_render():
    saved_token = server_module.MCP_API_TOKEN
    saved_hostname = server_module.RENDER_EXTERNAL_HOSTNAME
    try:
        server_module.MCP_API_TOKEN = None
        server_module.RENDER_EXTERNAL_HOSTNAME = "example.onrender.com"
        with pytest.raises(RuntimeError, match="Set MCP_API_TOKEN"):
            create_app()
    finally:
        server_module.MCP_API_TOKEN = saved_token
        server_module.RENDER_EXTERNAL_HOSTNAME = saved_hostname


@pytest.mark.anyio
async def test_create_app_allows_local_development_without_token():
    saved_token = server_module.MCP_API_TOKEN
    saved_hostname = server_module.RENDER_EXTERNAL_HOSTNAME
    saved_mcp = server_module.mcp
    try:
        server_module.MCP_API_TOKEN = None
        server_module.RENDER_EXTERNAL_HOSTNAME = None
        # Each MCP session manager can only be started once.
        server_module.mcp = server_module.FastMCP("test-local", stateless_http=True, transport_security=server_module.TransportSecuritySettings(enable_dns_rebinding_protection=False))
        app = create_app()
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE_URL
            ) as client:
                resp = await client.post(
                    "/mcp", headers=MCP_HEADERS, json=INIT_BODY
                )
        assert resp.status_code == 200
    finally:
        server_module.MCP_API_TOKEN = saved_token
        server_module.RENDER_EXTERNAL_HOSTNAME = saved_hostname
        server_module.mcp = saved_mcp


@pytest.mark.anyio
async def test_tool_call(managed_app, authed_headers):
    async with AsyncClient(
        transport=ASGITransport(app=managed_app), base_url=BASE_URL
    ) as client:
        resp = await client.post(
            "/mcp", headers=authed_headers, json=INIT_BODY
        )
        assert resp.status_code == 200

        tool_body = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "hello", "arguments": {"name": "World"}},
        }
        resp = await client.post(
            "/mcp", headers=authed_headers, json=tool_body
        )
        assert resp.status_code == 200
        data = parse_sse_data(resp.text)
        assert data["result"]["content"][0]["text"] == "Hello, World!"


@pytest.mark.anyio
async def test_verify_connection_list_and_call(managed_app, authed_headers):
    """공용 토큰으로 임시 검증 도구를 조회하고 호출할 수 있어야 한다."""
    async with AsyncClient(
        transport=ASGITransport(app=managed_app), base_url=BASE_URL
    ) as client:
        resp = await client.post("/mcp", headers=authed_headers, json=INIT_BODY)
        assert resp.status_code == 200

        resp = await client.post(
            "/mcp",
            headers=authed_headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        assert resp.status_code == 200
        tools = parse_sse_data(resp.text)["result"]["tools"]
        assert any(tool["name"] == "verify_connection" for tool in tools)

        resp = await client.post(
            "/mcp",
            headers=authed_headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "verify_connection",
                    "arguments": {"message": "team-test-123"},
                },
            },
        )
        assert resp.status_code == 200
        result = parse_sse_data(resp.text)["result"]
        assert not result.get("isError", False)
        assert result["content"][0]["text"] == "LUMI_CONNECTION_OK: team-test-123"


@pytest.mark.anyio
@pytest.mark.parametrize("token", [None, "wrong-token"])
async def test_verify_connection_rejects_unauthorized(managed_app, token):
    """토큰이 없거나 틀리면 임시 도구도 실행할 수 없다."""
    headers = dict(MCP_HEADERS)
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    async with AsyncClient(
        transport=ASGITransport(app=managed_app), base_url=BASE_URL
    ) as client:
        resp = await client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "verify_connection", "arguments": {}},
            },
        )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == -32001

@pytest.mark.anyio
async def test_video_tools_require_auth_and_are_listed(managed_app, authed_headers):
    async with AsyncClient(transport=ASGITransport(app=managed_app), base_url=BASE_URL) as client:
        body = {"jsonrpc": "2.0", "id": 4, "method": "tools/list"}
        assert (await client.post("/mcp", headers=MCP_HEADERS, json=body)).status_code == 401
        resp = await client.post("/mcp", headers=authed_headers, json=body)
        names = {t["name"] for t in parse_sse_data(resp.text)["result"]["tools"]}
        assert {"recommend_video_input", "analyze_pse_clip", "dim_pse_clip"} <= names


def test_input_recommendation_classifies_without_download():
    youtube = server_module.recommend_video_input("https://youtu.be/abc", 2, True)
    assert youtube["source_type"] == "youtube"
    assert "boundaries" in youtube["boundary_warning"]
    assert server_module.recommend_video_input("C:/video.mp4")["source_type"] == "local_file"


def test_oversized_clip_is_rejected_without_worker():
    with pytest.raises(ValueError, match="limit"):
        server_module.analyze_pse_clip("x" * 1398105)

