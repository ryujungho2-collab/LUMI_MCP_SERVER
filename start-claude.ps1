
$envFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $envFile)) {
    throw ".env 파일을 찾을 수 없습니다."
}

$entry = Get-Content $envFile |
    Where-Object { $_ -match '^\s*LUMI_MCP_TOKEN\s*=' } |
    Select-Object -First 1

if (-not $entry) {
    throw "LUMI_MCP_TOKEN이 .env에 없습니다."
}

$token = ($entry -split '=', 2)[1].Trim().Trim('"').Trim("'")

if ([string]::IsNullOrWhiteSpace($token)) {
    throw "LUMI_MCP_TOKEN 값이 비어 있습니다."
}

$env:LUMI_MCP_TOKEN = $token

Set-Location $PSScriptRoot
claude
