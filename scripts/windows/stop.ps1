# SecFlow AI — Windows stop
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

docker compose down
Write-Host "[SecFlow] 已停止（数据卷保留）" -ForegroundColor Yellow
