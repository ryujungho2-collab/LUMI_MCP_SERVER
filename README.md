# LUMI MCP Server

LUMI 팀이 함께 사용하는 원격 MCP 서버입니다. Python MCP SDK의 Streamable HTTP 전송 방식을 사용하며 Render에서 실행합니다.

## 서버 주소

- MCP endpoint: https://my-mcp-server-3n1j.onrender.com/mcp
- Health check: https://my-mcp-server-3n1j.onrender.com/health

Render 무료 플랜은 일정 시간 요청이 없으면 서버가 잠들 수 있습니다. 다시 요청하면 서버가 깨어나는 동안 첫 연결이 지연될 수 있습니다.

## 저장소 구성

```text
LUMI_MCP_SERVER/
├── server.py                       # MCP 도구, 인증, health check
├── render.yaml                     # Render 배포 설정
├── requirements.txt                # 서버 실행에 필요한 패키지
├── requirements-dev.txt            # 테스트 및 개발용 패키지
├── .env.example                    # 로컬 서버 개발용 환경변수 예시
├── .gitignore                      # 비밀정보 및 로컬 파일 제외
├── scripts/
│   └── generate_member_token.py    # 팀원별 인증 토큰 생성
└── tests/
    └── test_server.py              # 인증 및 MCP 동작 테스트
```

클라이언트별 `.mcp.json`은 이 저장소에 넣지 않습니다. 각 개발자는 자신이 사용하는 프로젝트에서 별도로 설정합니다.

## 인증 방식

서버는 두 가지 인증 방식을 지원합니다.

1. **팀원별 토큰**: Render의 `MCP_TOKENS_JSON`에 `member_id: SHA-256 해시`를 저장합니다.
2. **기존 공용 토큰**: `MCP_API_TOKEN` 하나를 공유하는 이전 방식입니다. 팀원별 토큰이 설정되기 전의 호환 모드입니다.

`MCP_TOKENS_JSON`이 설정되면 팀원별 인증이 우선 적용되고 기존 공용 토큰은 거부됩니다. 서버에는 원본 토큰이 아니라 SHA-256 해시만 저장합니다.

### 팀원 추가

1. 저장소를 클론한 뒤 프로젝트 루트에서 토큰을 생성합니다.

   ```powershell
   python scripts/generate_member_token.py member_id
   ```

   `member_id`는 `alice`, `member_02`처럼 팀원별로 겹치지 않는 식별자를 사용합니다.

2. 스크립트가 출력하는 두 값을 구분합니다.
   - `LUMI_MCP_TOKEN=...`: 해당 팀원에게 개인적으로 전달합니다.
   - JSON 해시 항목: Render의 `MCP_TOKENS_JSON`에 추가합니다.

3. Render Dashboard → `my-mcp-server` → Environment에서 `MCP_TOKENS_JSON`을 설정합니다. 예시:

   ```json
   {"owner":"owner_sha256_hash","member_02":"member_02_sha256_hash"}
   ```

   기존 팀원의 항목을 지우지 말고, 활성 팀원 전체를 하나의 JSON 객체에 유지합니다. 환경변수를 바꾼 뒤에는 Render에서 변경사항을 배포해야 합니다.

4. 팀원은 전달받은 원본 토큰을 자신의 개발 환경에 `LUMI_MCP_TOKEN`으로 설정합니다. 원본 토큰을 GitHub에 올리거나 공개 채팅에 붙여넣지 않습니다.

### 클라이언트 설정 예시

Claude Code의 프로젝트 루트 `.mcp.json` 예시입니다. 다른 클라이언트는 해당 도구의 MCP 설정 형식에 맞춰 등록합니다.

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

각 팀원의 `LUMI_MCP_TOKEN`은 개인 PC에만 저장합니다. `.env`를 사용하는 경우 반드시 `.gitignore`에 포함되어야 하며, 사용하는 클라이언트가 해당 환경변수를 읽도록 설정해야 합니다.

### 팀원 토큰 회수

Render의 `MCP_TOKENS_JSON`에서 회수할 팀원의 ID와 해시 항목만 제거한 뒤 변경사항을 배포합니다. 해당 팀원의 토큰만 거부되고 나머지 팀원의 토큰은 유지됩니다.

현재 개인별 토큰은 사용자 식별과 개별 회수를 지원합니다. 모든 팀원에게 동일한 MCP 도구 권한이 적용되며, 역할별·도구별 권한 제어는 아직 구현되어 있지 않습니다.

### 기존 공용 토큰에서 이전

`MCP_TOKENS_JSON`이 없으면 서버는 기존 `MCP_API_TOKEN`을 사용합니다. 팀원별 토큰으로 전환하고 모든 팀원의 연결을 확인한 뒤에는 Render에서 기존 `MCP_API_TOKEN`을 제거하는 것을 권장합니다.

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

Render는 저장소의 `render.yaml`을 사용합니다. 현재 `autoDeploy: true`이므로 `main` 브랜치에 변경사항을 `git push`하면 Render가 자동으로 배포합니다.

Render 환경변수 변경은 코드 푸시와 별개로 Dashboard에서 저장하고 배포해야 합니다.

## 보안 주의사항

- 실제 토큰이나 `MCP_TOKENS_JSON`의 해시 목록을 소스 코드에 넣지 않습니다.
- 개인 토큰이 노출되면 해당 팀원의 항목을 Render에서 제거하고 새 토큰을 발급합니다.
- `.env`와 개인용 MCP 클라이언트 설정 파일은 GitHub에 올리지 않습니다.
- Render Dashboard 접근 권한은 서버 배포·관리 권한이 필요한 사람에게만 부여합니다.
