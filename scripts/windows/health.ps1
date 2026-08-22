# SecFlow AI — Windows health check
$ErrorActionPreference = "Continue"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

Write-Host "[SecFlow] 组件状态:"
docker compose ps

Write-Host ""
Write-Host "[SecFlow] API 健康检查:"
$port = $env:API_PORT ?? "8000"
try {
    Invoke-RestMethod "http://localhost:$port/api/health" | ConvertTo-Json
} catch {
    Write-Host "API 不可用: $_" -ForegroundColor Red
}
foreach ($ep in @("db", "redis", "wazuh", "misp", "llm")) {
    try {
        $r = Invoke-RestMethod "http://localhost:$port/api/health/$ep"
        Write-Host "  /api/health/$ep : ok=$($r.ok)"
    } catch {
        Write-Host "  /api/health/$ep : unavailable" -ForegroundColor Red
    }
}
