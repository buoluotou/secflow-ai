# SecFlow AI — Windows start (spec §59)
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

if (-not (Test-Path .env)) {
    Write-Host "缺少 .env —— 先执行 .\scripts\windows\install.ps1" -ForegroundColor Red
    exit 1
}

docker network inspect secflow-net 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { docker network create secflow-net }

docker compose up -d --build

Write-Host "[SecFlow] 已启动:" -ForegroundColor Green
Write-Host "  Frontend : http://localhost"
Write-Host "  API      : http://localhost:$($env:API_PORT ?? '8000')/docs"
docker compose ps
