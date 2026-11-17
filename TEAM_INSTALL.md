# 팀원 설치 및 연결 안내

이 문서는 Render에 배포된 LUMI 원격 MCP 서버를 사용하는 팀원용 안내입니다.

## 1. 먼저 준비할 것

팀원은 다음 두 가지를 준비하면 됩니다.

1. 사용할 MCP 클라이언트 하나: Claude Code, Cursor, Codex 또는 VS Code의 MCP 지원 확장
2. 관리자에게 전달받은 **공용 Bearer 토큰**

**LUMI_MCP_SERVER 저장소를 클론하거나 서버용 Python 패키지를 설치할 필요가 없습니다.** 서버는 Render에서 실행됩니다.

| 사용하는 도구 | 필요한 프로그램 |
|---|---|
| Claude Code | Claude Code CLI |
| Cursor | Cursor 데스크톱 앱 |
| Codex | Codex CLI |
| VS Code | VS Code 및 원격 MCP를 지원하는 에이전트/확장 |

Git은 별도의 프로젝트 저장소를 clone할 때만 필요합니다.

## 2. 공용 토큰 등록

모든 팀원이 동일한 공용 토큰을 사용합니다. 관리자는 Render의 `MCP_API_TOKEN` 값을 안전한 경로로 전달합니다.

Windows에서 사용자 환경변수로 등록하는 방법:

1. 시작 메뉴에서 **환경 변수 편집**을 검색합니다.
2. **환경 변수** 버튼을 누릅니다.
3. 위쪽 **사용자 변수** 영역에서 **새로 만들기**를 누릅니다.
4. 변수 이름에 `LUMI_MCP_TOKEN`, 변수 값에 관리자에게 받은 공용 토큰을 입력합니다.
5. 저장한 뒤 MCP 클라이언트와 VS Code/Cursor/터미널을 완전히 종료하고 다시 실행합니다.

PowerShell에서 현재 터미널 세션에만 등록하려면 다음을 실행할 수도 있습니다.

```powershell
$env:LUMI_MCP_TOKEN = "관리자에게_받은_공용_토큰"
```

등록 여부 확인(토큰 값 자체는 출력하지 않음):

```powershell
if ([string]::IsNullOrWhiteSpace($env:LUMI_MCP_TOKEN)) {
  "LUMI_MCP_TOKEN이 등록되지 않았습니다."
} else {
  "LUMI_MCP_TOKEN이 등록되어 있습니다."
}
```

> `.env` 파일을 반드시 만들 필요는 없습니다. `.env`는 일반 텍스트 파일일 뿐이며, 모든 클라이언트가 자동으로 읽는 것은 아닙니다. 이 안내에서는 Windows 사용자 환경변수 `LUMI_MCP_TOKEN`을 사용합니다.

## 3. 사용하는 클라이언트에 서버 연결 등록

서버 주소는 모두 같습니다.

`https://my-mcp-server-3n1j.onrender.com/mcp`

아래에서 본인이 사용하는 도구의 방법 하나만 진행하세요.

### A. Claude Code

1. 프로젝트 최상위 폴더에 `.mcp.json` 파일을 만듭니다.
2. 아래 내용을 붙여 넣고 저장합니다.

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

3. 해당 프로젝트 폴더에서 Claude Code를 실행합니다.
4. MCP 서버 연결을 승인하라는 안내가 나오면 내용을 확인하고 승인합니다.
5. Claude Code에서 `/mcp` 명령으로 LUMI 연결 상태를 확인합니다.

### B. Cursor

1. 프로젝트 최상위 폴더에 `.cursor` 폴더를 만들고, 그 안에 `mcp.json` 파일을 만듭니다.
2. 아래 내용을 붙여 넣고 저장합니다.

```json
{
  "mcpServers": {
    "lumi": {
      "url": "https://my-mcp-server-3n1j.onrender.com/mcp",
      "headers": {
        "Authorization": "Bearer ${env:LUMI_MCP_TOKEN}"
      }
    }
  }
}
```

3. Cursor를 완전히 종료한 뒤 다시 실행합니다.
4. Cursor 설정의 MCP 항목에서 `lumi` 서버가 표시되고 활성화되어 있는지 확인합니다.

### C. Codex CLI

새로 연 PowerShell에서 아래 명령을 실행합니다.

```powershell
codex mcp add lumi --url https://my-mcp-server-3n1j.onrender.com/mcp --bearer-token-env-var LUMI_MCP_TOKEN
```

등록 여부는 다음 명령으로 확인합니다.

```powershell
codex mcp list
```

Codex가 실행 중이었다면 종료 후 다시 실행하세요. Codex CLI는 지정한 환경변수 값을 원격 MCP 서버의 Bearer 인증 토큰으로 사용합니다.

### D. VS Code

VS Code는 사용하는 에이전트/확장에 따라 MCP 설정 위치와 형식이 다릅니다.

해당 확장이 **원격 Streamable HTTP MCP**와 **Authorization 헤더의 환경변수 참조**를 지원하는지 확인한 뒤 다음 정보를 등록하세요.

- 이름: `lumi`
- 전송 방식: Streamable HTTP
- URL: `https://my-mcp-server-3n1j.onrender.com/mcp`
- Header: `Authorization: Bearer <LUMI_MCP_TOKEN 환경변수 참조>`

확장마다 설정 형식이 다르므로 Claude Code나 Cursor의 설정 파일을 그대로 복사하지 마세요. 확장 이름과 버전에 맞는 MCP 설정 문서를 확인하세요.

## 4. 연결 확인 및 문제 해결

서버 상태 확인 주소:

- 헬스 체크: https://my-mcp-server-3n1j.onrender.com/health
- MCP 연결 주소: https://my-mcp-server-3n1j.onrender.com/mcp

### 실제 MCP 도구 호출 검증

클라이언트에서 LUMI 서버에 연결한 뒤 에이전트 채팅에 아래와 같이 입력하세요.

> LUMI MCP 서버의 verify_connection 도구를 실제로 호출해 줘. message는 team-test-123으로 설정하고 도구가 반환한 원문을 보여줘.

실제 도구 호출 결과가 다음과 같으면 연결, 인증 및 MCP 도구 실행이 성공한 것입니다.

```text
LUMI_CONNECTION_OK: team-test-123
```

클라이언트의 도구 호출 기록에서 `verify_connection`이 실제 실행되었는지 확인하세요. 에이전트가 결과를 추측해서 답한 것은 성공으로 간주하지 않습니다. 테스트 메시지는 임의로 바꿀 수 있으며, 공용 토큰이나 개인정보를 입력하지 마세요. `/health`는 공개 상태 확인용이므로 그것만으로 인증 성공을 확인할 수 없습니다.

연결이 안 될 때는 다음 순서로 확인하세요.

1. 환경변수 이름이 정확히 `LUMI_MCP_TOKEN`인지 확인합니다.
2. 토큰을 등록한 뒤 클라이언트와 터미널을 완전히 종료하고 다시 실행했는지 확인합니다.
3. 관리자에게 받은 공용 토큰을 공백이나 따옴표 없이 정확히 등록했는지 확인합니다.
4. 관리자가 Render의 `MCP_API_TOKEN`에 해당 토큰을 설정하고 배포했는지 확인합니다.
5. `/health`가 응답하는지 확인합니다.

Render 무료 플랜은 일정 시간 사용하지 않으면 서버가 잠들 수 있습니다. 첫 연결에서 서버가 깨어나는 데 시간이 걸릴 수 있으니 잠시 기다린 뒤 다시 시도하세요.

## 5. 설치하지 않아도 되는 것

원격 서버를 사용하는 팀원은 다음 항목을 설치할 필요가 없습니다.

- Python 및 pip
- Node.js
- Docker
- `requirements.txt` 또는 `requirements-dev.txt`의 패키지
- 로컬 MCP 서버 실행 환경
- LUMI_MCP_SERVER 저장소

위 항목은 서버를 직접 개발하거나 로컬에서 실행할 때만 필요합니다.

## 6. 팀원과 관리자 역할 구분

| 작업 | 팀원 | 관리자 |
|---|:---:|:---:|
| MCP 클라이언트 설치 | ✓ | ✓ |
| 공용 토큰 수령 및 보관 | ✓ | ✓ |
| 환경변수 및 클라이언트 연결 설정 | ✓ |  |
| 공용 토큰 관리 및 교체 |  | ✓ |
| Render 배포 및 관리 |  | ✓ |

**모든 팀원은 동일한 토큰 하나로 접속합니다.** 특정 팀원 한 명만 차단할 수는 없습니다. 토큰을 교체하면 모든 팀원이 새 토큰으로 클라이언트 설정을 갱신해야 합니다.
