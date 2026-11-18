# LUMI PSE MCP 서버

팀원 프로젝트의 A1 영상 판별·전체 화면 감광을 로컬 MCP 도구로 제공합니다. 원본 코드와 별도의 래퍼이며 원본 저장소가 필요합니다.

## 도구

- `analyze_video`: 로컬 영상의 위험 구간 분석. 기본 SDR 백색 휘도 가정 200 cd/m²; `l_max`로 변경.
- `dim_fullscreen_a1`: A1 전체 화면 감광 MP4를 새 경로에 저장하고, 인코딩된 파일을 다시 열어 분석. 기존 파일은 덮어쓰지 않습니다. 출력에는 원본 오디오가 포함되지 않습니다.

연구용 규칙 기반 추정으로 의학적 안전을 보장하지 않습니다. sRGB/SDR 가정이며 HDR/PQ/HLG를 지원하지 않습니다. GitHub에 코드를 올리는 것과 서버를 실행·호스팅하는 것은 별개입니다.

## 설치 및 실행

Python 3.11 이상과 원본 프로젝트 `lumi-lab-rockrovks`의 체크아웃이 필요합니다. 원본 `Fullscreen/A1` 모듈을 그대로 사용합니다. 원본 사용 권한과 라이선스는 배포 전에 확인하세요.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LUMI_ENGINE_DIR = 'C:\path\to\lumi-lab-rockrovks'
python server.py
```

stdio MCP 서버이므로 마지막 명령은 MCP 클라이언트가 실행하는 것이 일반적입니다. 클라이언트 설정 예시는 경로를 실제 절대 경로로 바꿔 사용합니다.

```json
{
  "mcpServers": {
    "lumi-pse": {
      "command": "C:\\path\\to\\lumi-pse-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\lumi-pse-mcp\\server.py"],
      "env": {"LUMI_ENGINE_DIR": "C:\\path\\to\\lumi-lab-rockrovks"}
    }
  }
}
```

영상 경로는 MCP 서버가 실행되는 컴퓨터의 로컬 경로입니다. 영상 분석은 오래 걸릴 수 있고, 색상·밝기 가정 및 해상도에 따라 결과가 달라집니다. 위험 영상은 실제로 재생하지 않고 처리할 수 있습니다.
