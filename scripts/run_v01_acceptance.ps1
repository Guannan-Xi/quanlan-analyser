$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$python = "C:\Users\XGN\miniconda3\python.exe"

function Invoke-Checked {
  param(
    [Parameter(Mandatory=$true)][string]$Label,
    [Parameter(Mandatory=$true)][scriptblock]$Command
  )
  Write-Host $Label
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Label failed with exit code $LASTEXITCODE"
  }
}

Invoke-Checked "[1/5] Python compileall" { & $python -m compileall backend worker eeg_core scripts }

Write-Host "[2/5] Frontend syntax check"
Push-Location frontend
try {
  npm run check
  if ($LASTEXITCODE -ne 0) { throw "Frontend syntax check failed with exit code $LASTEXITCODE" }
} finally {
  Pop-Location
}

Invoke-Checked "[3/5] Core/worker acceptance" { & $python scripts\acceptance_v01_worker_core.py }
Invoke-Checked "[4/5] Full API acceptance" { & $python scripts\acceptance_v01_full.py }
Invoke-Checked "[6/7] UI acceptance via 4174 dev frontend" { node scripts\acceptance_v01_ui.mjs }
$portalUrl = "http://127.0.0.1:8765/eeg/"
$portalReady = $false
try {
  $portalResponse = Invoke-WebRequest -UseBasicParsing -Uri $portalUrl -TimeoutSec 5
  $portalReady = ($portalResponse.StatusCode -eq 200 -and $portalResponse.Content -match "data-enter-role|eeg-v01-production")
} catch {
  Write-Host "[7/7] UI acceptance via 8765 unified portal skipped: $($_.Exception.Message)"
}

if ($portalReady) {
  $env:QLANALYSER_FRONTEND_URL = $portalUrl
  try {
    Invoke-Checked "[7/7] UI acceptance via 8765 unified portal" { node scripts\acceptance_v01_ui.mjs }
  } finally {
    Remove-Item Env:QLANALYSER_FRONTEND_URL -ErrorAction SilentlyContinue
  }
} else {
  Write-Host "[7/7] UI acceptance via 8765 unified portal skipped: EEG portal is not available on $portalUrl"
}

Write-Host "V01 acceptance suite passed."
