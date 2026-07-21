$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$python = "C:\Users\XGN\miniconda3\python.exe"
$apiUrl = $env:QLANALYSER_API_URL
if (-not $apiUrl) { $apiUrl = "http://127.0.0.1:8001/api" }
$frontendUrl = $env:QLANALYSER_FRONTEND_URL
if (-not $frontendUrl) { $frontendUrl = "http://127.0.0.1:4174/?api=$apiUrl" }
$uiEvidencePath = Join-Path $root "work\release_evidence\20260620-report-zip-evidence-matrix\acceptance_v01_ui_report_zip_download.json"
$opsUiEvidencePath = Join-Path $root "work\release_evidence\20260620-v01-acceptance\acceptance_ops_ui.json"
$customerLoginEvidencePath = Join-Path $root "work\release_evidence\20260620-v01-acceptance\acceptance_customer_login_demo.json"
$opsBillingEvidencePath = Join-Path $root "work\release_evidence\20260620-v01-acceptance\acceptance_ops_billing_invoice.json"
$queueCapacityEvidencePath = Join-Path $root "work\release_evidence\20260620-v01-acceptance\acceptance_task_queue_capacity.json"
$largeUploadLowerEvidencePath = Join-Path $root "work\release_evidence\20260620-v01-acceptance\acceptance_large_upload_10x200mb.json"
$largeUploadUpperEvidencePath = Join-Path $root "work\release_evidence\20260620-v01-acceptance\acceptance_large_upload_1x1gb.json"
$pageVisualQaEvidencePath = Join-Path $root "work\release_evidence\20260620-page-visual-qa\page_visual_qa.json"
$pageVisualQaScreenshotDir = Join-Path $root "work\release_evidence\20260620-page-visual-qa\screenshots"
$capacityTemp = Join-Path $root "work\release_evidence\20260620-capacity-temp"
New-Item -ItemType Directory -Force -Path $capacityTemp | Out-Null

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

function Invoke-WithCapacityTemp {
  param([Parameter(Mandatory=$true)][scriptblock]$Command)
  $oldTemp = $env:TEMP
  $oldTmp = $env:TMP
  try {
    $env:TEMP = $capacityTemp
    $env:TMP = $capacityTemp
    & $Command
  } finally {
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
  }
}

Invoke-Checked "[1/16] Python compileall" { & $python -m compileall backend worker eeg_core scripts }

Write-Host "[2/16] Frontend syntax check"
Push-Location frontend
try {
  npm run check
} finally {
  Pop-Location
}

Invoke-Checked "[3/16] Running backend contract check ($apiUrl)" { & $python scripts\check_running_backend_contract.py --base-url $apiUrl }
Invoke-Checked "[4/16] Core/worker acceptance" { & $python scripts\acceptance_v01_worker_core.py }
Invoke-Checked "[5/16] Full API acceptance" { & $python scripts\acceptance_v01_full.py }
Invoke-Checked "[6/16] Ops billing/invoice API acceptance" { & $python scripts\acceptance_ops_billing_invoice.py --evidence-path $opsBillingEvidencePath }
Invoke-Checked "[7/16] Report ZIP contract" { & $python scripts\acceptance_report_zip_contract.py }
Invoke-Checked "[8/16] Report ZIP evidence matrix" { & $python scripts\report_zip_evidence_matrix.py }
Invoke-Checked "[9/16] Lab demo backend acceptance" { & $python scripts\acceptance_lab_demo_backend.py }
Invoke-Checked "[10/16] QC preview service acceptance" { & $python scripts\acceptance_qc_preview_service.py }
Invoke-Checked "[11/16] QC browser gate" { node scripts\acceptance_qc_browser_gate.mjs }
Invoke-Checked "[12/16] Queue capacity contract (10 users / 50 tasks)" { & $python scripts\acceptance_task_queue_capacity.py --users 10 --tasks 50 --evidence-path $queueCapacityEvidencePath }
Invoke-Checked "[13/16] Large upload lower bound (10 users / 200MB)" {
  Invoke-WithCapacityTemp { & $python scripts\acceptance_large_uploads.py --users 10 --min-mb 200 --max-mb 200 --actual-mb-cap 200 --chunk-kb 1024 --evidence-path $largeUploadLowerEvidencePath }
}
Invoke-Checked "[14/16] Large upload upper bound (1 user / 1GB)" {
  Invoke-WithCapacityTemp { & $python scripts\acceptance_large_uploads.py --users 1 --min-mb 1024 --max-mb 1024 --actual-mb-cap 1024 --chunk-kb 1024 --evidence-path $largeUploadUpperEvidencePath }
}
Invoke-Checked "[15/16] Customer login demo acceptance" {
  $env:QLANALYSER_API_URL = $apiUrl
  $env:QLANALYSER_TARGET_URL = $frontendUrl
  $env:QLANALYSER_CUSTOMER_LOGIN_EVIDENCE_PATH = $customerLoginEvidencePath
  try {
    node scripts\acceptance_customer_login_demo.mjs
  } finally {
    Remove-Item Env:QLANALYSER_CUSTOMER_LOGIN_EVIDENCE_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_TARGET_URL -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_API_URL -ErrorAction SilentlyContinue
  }
}
Invoke-Checked "[16/16] UI acceptance via configured frontend" {
  $env:QLANALYSER_API_URL = $apiUrl
  $env:QLANALYSER_FRONTEND_URL = $frontendUrl
  $env:QLANALYSER_UI_EVIDENCE_PATH = $uiEvidencePath
  try {
    node scripts\acceptance_v01_ui.mjs
  } finally {
    Remove-Item Env:QLANALYSER_UI_EVIDENCE_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_FRONTEND_URL -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_API_URL -ErrorAction SilentlyContinue
  }
}

Invoke-Checked "[post] Ops browser acceptance" {
  $env:QLANALYSER_API_URL = $apiUrl
  $env:QLANALYSER_FRONTEND_URL = $frontendUrl
  $env:QLANALYSER_OPS_UI_EVIDENCE_PATH = $opsUiEvidencePath
  try {
    node scripts\acceptance_ops_ui.mjs
  } finally {
    Remove-Item Env:QLANALYSER_OPS_UI_EVIDENCE_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_FRONTEND_URL -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_API_URL -ErrorAction SilentlyContinue
  }
}

Invoke-Checked "[post] PAGE_VISUAL_QA browser gate" {
  $env:QLANALYSER_FRONTEND_URL = $frontendUrl
  $env:QLANALYSER_API_URL = $apiUrl
  $env:QLANALYSER_PAGE_VISUAL_QA_EVIDENCE_PATH = $pageVisualQaEvidencePath
  $env:QLANALYSER_PAGE_VISUAL_QA_SCREENSHOT_DIR = $pageVisualQaScreenshotDir
  try {
    node scripts\acceptance_page_visual_qa.mjs
  } finally {
    Remove-Item Env:QLANALYSER_PAGE_VISUAL_QA_EVIDENCE_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_PAGE_VISUAL_QA_SCREENSHOT_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_FRONTEND_URL -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_API_URL -ErrorAction SilentlyContinue
  }
}
Invoke-Checked "[post] Aliyun V1 local contract" { & $python scripts\acceptance_aliyun_v1_contracts.py }
Invoke-Checked "[post] Storage lifecycle local contract" { & $python scripts\acceptance_aliyun_storage_contract.py --target local }
Invoke-Checked "[post] Backup restore local drill" { & $python scripts\acceptance_backup_restore_drill.py --target local }

$portalUrl = "http://127.0.0.1:8765/eeg/"
$portalReady = $false
try {
  $portalResponse = Invoke-WebRequest -UseBasicParsing -Uri $portalUrl -TimeoutSec 5
  $portalReady = ($portalResponse.StatusCode -eq 200 -and $portalResponse.Content -match "data-enter-role|eeg-v01-production")
} catch {
  Write-Host "[post] UI acceptance via 8765 unified portal skipped: $($_.Exception.Message)"
}

if ($portalReady) {
  $env:QLANALYSER_FRONTEND_URL = $portalUrl
  try {
    $env:QLANALYSER_API_URL = $apiUrl
    Invoke-Checked "[post] UI acceptance via 8765 unified portal" { node scripts\acceptance_v01_ui.mjs }
  } finally {
    Remove-Item Env:QLANALYSER_FRONTEND_URL -ErrorAction SilentlyContinue
    Remove-Item Env:QLANALYSER_API_URL -ErrorAction SilentlyContinue
  }
} else {
  Write-Host "[post] UI acceptance via 8765 unified portal skipped: EEG portal is not available on $portalUrl"
}

Write-Host "V01 acceptance suite passed."
