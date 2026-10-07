param([int]$Port=8787)
$ErrorActionPreference='Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$env:PORT = [string]$Port
$env:KERNEL_INSIGHT_DATA_DIR = Join-Path $projectDirectory 'data\windows-local'
$env:KERNEL_BENCHMARK_DIR = Join-Path $projectDirectory 'data\datasets\openharmony-lkdtm-lab-v2'
Remove-Item Env:KERNEL_AGENT_MODE -ErrorAction SilentlyContinue
Set-Location -LiteralPath $projectDirectory
node (Join-Path $projectDirectory 'server\index.js')
