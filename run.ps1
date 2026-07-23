# 启动人机协作决策实验平台
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "[run] 启动 Flask 服务..." -ForegroundColor Cyan
python app.py
