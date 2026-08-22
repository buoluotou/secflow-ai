# =====================================================================
# SecFlow AI — Windows install (spec §59)
#   .\scripts\windows\install.ps1
#
# 前置条件: Docker Desktop + WSL2 (wsl --install -d Ubuntu)
# =====================================================================
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Write-Host "[SecFlow] >>> Windows 安装脚本" -ForegroundColor Cyan

# 1. Docker Desktop
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "未检测到 Docker Desktop。请先安装: https://www.docker.com/products/docker-desktop/"
    Write-Host "并确保使用 WSL2 后端 (Settings -> General -> Use the WSL 2 based engine)"
    exit 1
}

# 2. WSL2 内核参数 (spec §7 — Wazuh 要求)
wsl -e sh -c 'sysctl -w vm.max_map_count=262144 && echo "vm.max_map_count=262144" >> /etc/sysctl.conf' 2>$null
Write-Host "vm.max_map_count 已设置 (WSL2)"

# 3. Docker 网络 (spec §10)
docker network inspect secflow-net 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker network create secflow-net
    Write-Host "已创建 secflow-net"
}

# 4. 环境文件
Set-Location $RepoRoot
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "已生成 .env —— 请修改 POSTGRES_PASSWORD / SECRET_KEY 等敏感项" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[SecFlow] 安装完成。接下来:" -ForegroundColor Green
Write-Host "  1) 编辑 .env"
Write-Host "  2) .\scripts\windows\start.ps1"
Write-Host "  3) 可选: WSL2 中执行 ./deploy/wazuh/deploy.sh 与 ./deploy/misp/deploy.sh"
