# SecFlow AI — Windows update
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

Write-Host "[SecFlow] 拉取最新代码并重建镜像..."
git pull --ff-only
docker compose pull
docker compose up -d --build
Write-Host "[SecFlow] 更新完成" -ForegroundColor Green
