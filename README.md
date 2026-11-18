# LUMI MCP Server

LUMI 팀이 함께 사용하는 원격 MCP 서버입니다. Python MCP SDK의 Streamable HTTP 전송 방식을 사용하며 Render에서 실행합니다.

## 서버 주소

- MCP endpoint: https://my-mcp-server-3n1j.onrender.com/mcp
- Health check: https://my-mcp-server-3n1j.onrender.com/health

Render 무료 플랜은 일정 시간 요청이 없으면 서버가 잠들 수 있습니다. 다시 요청하면 서버가 깨어나는 동안 첫 연결이 지연될 수 있습니다.

## 팀원 설치 안내

원격 MCP 서버를 사용하는 팀원은 [TEAM_INSTALL.md](TEAM_INSTALL.md)를 참고하세요. 팀원은 같은 공용 Bearer 토큰을 전달받아 각자 사용하는 MCP 클라이언트에 등록합니다.

## 인증 방식: 공용 Bearer 토큰

모든 팀원이 하나의 `MCP_API_TOKEN`을 공유합니다.

- Render의 Environment에 `MCP_API_TOKEN` 하나를 설정합니다.
- `render.yaml`은 Render에서 최초 생성 시 강력한 값을 자동 생성하도록 `generateValue: true`로 설정되어 있습니다.
- 관리자는 Render Dashboard에서 공용 토큰을 확인해 팀원에게 안전한 경로로 전달합니다.
- 각 팀원은 자신의 PC에서 `LUMI_MCP_TOKEN` 환경변수로 보관합니다.
- MCP 클라이언트는 `Authorization: Bearer <token>` 헤더를 전송합니다.
- 서버는 `hmac.compare_digest`로 전달된 토큰과 `MCP_API_TOKEN`을 비교합니다.
- `MCP_TOKENS_JSON` 및 팀원별 토큰/해시 등록은 사용하지 않습니다.

### 공용 토큰 설정 및 교체

1. Render Dashboard → `my-mcp-server` → Environment에서 `MCP_API_TOKEN`을 확인합니다.
2. 최초 생성 시 `render.yaml`의 `generateValue: true`가 Render에 토큰을 생성합니다. 기존 서비스에 이미 값이 있다면 그 값을 그대로 사용합니다.
3. 토큰을 팀원에게 개별적으로 안전하게 전달합니다. 공개 채팅, 이슈, README, GitHub 파일에 토큰을 기록하지 않습니다.
4. 토큰을 교체할 때는 Render에서 `MCP_API_TOKEN` 값을 새 값으로 바꾸고 저장·배포한 다음, 새 토큰을 모든 팀원에게 전달합니다. 교체 즉시 이전 토큰은 더 이상 유효하지 않습니다.

공용 토큰 방식에서는 특정 팀원 한 명만 따로 차단할 수 없습니다. 토큰이 유출되거나 팀원 접근을 일괄 회수해야 할 때는 공용 토큰을 교체하고 모든 팀원의 클라이언트 설정을 갱신합니다.

## 클라이언트 설정 예시

클라이언트별 설정 파일 위치와 형식은 다를 수 있습니다. 아래는 Claude Code의 프로젝트 루트 `.mcp.json` 예시입니다.

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

각 팀원의 `LUMI_MCP_TOKEN`은 개인 PC에만 저장합니다. `.env` 파일을 사용하는 경우 반드시 `.gitignore`에 포함하고, 사용하는 MCP 클라이언트가 해당 환경변수를 읽도록 설정합니다.

## 로컬 개발

Python 가상환경을 만든 뒤 개발용 의존성을 설치합니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:MCP_API_TOKEN = "local-test-token"
python server.py
```

서버는 기본적으로 `http://localhost:10000`에서 실행됩니다. 로컬 실행에서는 인증 환경변수가 없을 경우 인증이 비활성화되지만, Render에서는 인증 설정이 없으면 서버가 시작되지 않습니다.

`.env.example`은 환경변수의 예시일 뿐 자동으로 로드되지 않습니다. PowerShell 세션에 환경변수를 직접 설정하거나 별도의 dotenv 로더를 사용해야 합니다.

## 테스트

```powershell
pip install -r requirements-dev.txt
pytest
```

## 배포

Render는 저장소의 `render.yaml`을 사용합니다. 현재 `autoDeploy: true`이므로 `main` 브랜치에 변경사항을 push하면 Render가 자동 배포합니다.

Render 환경변수 변경은 코드 푸시와 별개로 Dashboard에서 저장하고 배포해야 합니다.

## 보안 주의사항

- 실제 공용 토큰을 소스 코드, 문서, 테스트 또는 GitHub 커밋에 넣지 않습니다.
- 토큰을 전달할 때는 개인 메시지 등 안전한 경로를 사용합니다.
- 공용 토큰은 팀원 모두가 공유하므로 유출 시 즉시 교체하고 모든 팀원의 클라이언트 설정을 갱신합니다.
- `.env`와 개인용 MCP 클라이언트 설정 파일은 GitHub에 올리지 않습니다.
- Render Dashboard 접근 권한은 서버 배포·관리 권한이 필요한 사람에게만 부여합니다.

## 로컬 영상 분석 도구

로컬 PC에 있는 영상을 분석하는 별도 stdio MCP 서버는 [local-pse/README.md](local-pse/README.md)를 참고하세요. 기존 Render 서버와 별도로 실행되며, 팀원 영상 엔진 체크아웃이 필요합니다.
