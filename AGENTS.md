# LUMI MCP Server — Agent Guide

이 저장소는 LUMI 팀의 원격 MCP 서버입니다. Python MCP SDK의 Streamable HTTP 전송 방식을 사용하며 Render에 배포됩니다.

## Project layout

- \`server.py\`: MCP 도구, bearer-token 인증, ASGI 앱, health check
- \`scripts/generate_member_token.py\`: 팀원별 원본 토큰 및 SHA-256 해시 생성
- \`tests/test_server.py\`: 인증, health check, MCP 도구 테스트
- \`requirements.txt\`: 서버 런타임 의존성
- \`requirements-dev.txt\`: 테스트 및 개발 의존성
- \`render.yaml\`: Render 배포 설정

## Authentication

팀원별 토큰 인증을 기본 방식으로 사용합니다.

- Render의 \`MCP_TOKENS_JSON\`은 \`member_id\`와 해당 토큰의 SHA-256 해시를 매핑합니다.
- 각 팀원은 원본 토큰을 개인 환경변수 \`LUMI_MCP_TOKEN\`으로 보관합니다.
- MCP 클라이언트는 \`Authorization: Bearer <token>\` 헤더를 전송합니다.
- 인증 미들웨어는 원본 토큰을 저장하지 않고, 검증된 팀원 ID를 \`scope["state"]["mcp_member_id"]\`에 설정합니다.
- \`MCP_TOKENS_JSON\`이 설정되면 기존 \`MCP_API_TOKEN\` 공용 토큰은 거부됩니다.
- 팀원 토큰을 회수할 때는 Render의 \`MCP_TOKENS_JSON\`에서 해당 ID/해시 항목을 제거합니다.
- 현재 모든 팀원은 동일한 도구 권한을 가집니다. 역할별 권한이 구현된 것처럼 설명하지 않습니다.

\`MCP_TOKENS_JSON\`이 없을 때만 \`MCP_API_TOKEN\`을 이전 호환 방식으로 사용합니다. \`/health\`는 Render health check를 위해 공개되어 있습니다. Render에서는 인증 설정이 없으면 서버가 시작되지 않도록 유지합니다.

원본 토큰을 코드, 로그, 테스트, 문서 또는 커밋에 넣지 않습니다.

## Adding a tool

\`server.py\`의 기존 도구 정의 아래, \`/health\` custom route 위에 \`@mcp.tool()\` 함수를 추가합니다.

\`\`\`python
@mcp.tool()
def your_tool_name(param: str, count: int = 10) -> str:
    """도구의 기능을 한 문장으로 설명합니다."""
    return "result"
\`\`\`

- 함수명은 snake_case를 사용합니다.
- 모든 매개변수와 반환값에 타입 힌트를 작성합니다.
- LLM에 노출되는 기능 설명을 docstring에 작성합니다.
- 구조화된 결과는 필요에 따라 JSON 문자열로 반환합니다.

## Deployment

\`render.yaml\`은 \`autoDeploy: true\`로 설정되어 있습니다. 변경사항을 \`main\` 브랜치에 push하면 Render가 자동 배포합니다. Render 환경변수 변경은 Dashboard에서 별도로 저장·배포해야 합니다.

## Tests

개발 의존성을 설치하고 테스트를 실행합니다.

\`\`\`powershell
pip install -r requirements-dev.txt
pytest
\`\`\`

인증을 변경할 때는 유효한 팀원 토큰, 잘못된 토큰, 팀원별 모드에서의 공용 토큰 거부, 공개 health endpoint 테스트를 함께 확인합니다.
