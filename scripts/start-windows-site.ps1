param(
  [int]$Port=8787,
  [ValidateSet('Demo','Full')][string]$Mode='Demo',
  [string]$Distribution='Ubuntu',
  [string]$LinuxProject,
  [string]$Model,
  [string]$ModelBaseUrl
)
$ErrorActionPreference='Stop'
if ($Mode -eq 'Full') {
  if (!$LinuxProject -or !$Model -or !$ModelBaseUrl) {
    throw 'Full mode requires -LinuxProject (WSL ext4 path), -Model and -ModelBaseUrl. See docs/CROSS_PLATFORM_DEPLOYMENT.md.'
  }
  & wsl.exe --distribution $Distribution --exec env "PORT=$Port" "KERNEL_AGENT_MODEL=$Model" "KERNEL_AGENT_BASE_URL=$ModelBaseUrl" bash "$LinuxProject/scripts/start-linux-site.sh"
  if ($LASTEXITCODE -ne 0) { throw "WSL full deployment failed (exit $LASTEXITCODE); no demo fallback." }
  exit
}
Write-Host 'Demo mode: deterministic triage and archived reports. For full Linux tools use -Mode Full.'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$env:PORT = [string]$Port
$env:KERNEL_INSIGHT_DATA_DIR = Join-Path $projectDirectory 'data\windows-local'
$env:KERNEL_BENCHMARK_DIR = Join-Path $projectDirectory 'data\datasets\openharmony-lkdtm-lab-v2'
Remove-Item Env:KERNEL_AGENT_MODE -ErrorAction SilentlyContinue
Set-Location -LiteralPath $projectDirectory
node (Join-Path $projectDirectory 'server\index.js')
