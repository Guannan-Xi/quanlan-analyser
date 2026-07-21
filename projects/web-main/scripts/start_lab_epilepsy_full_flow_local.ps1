param(
  [string]$SampleRoot = "D:\Quanlan\Data\HE脑电\HE脑电",
  [string]$PythonExe = "C:\Users\XGN\miniconda3\python.exe",
  [int]$BackendPort = 8001,
  [int]$FrontendPort = 4176,
  [switch]$StartFrontend
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
  throw "Python not found: $PythonExe"
}

if (-not (Test-Path -LiteralPath $SampleRoot -PathType Container)) {
  throw "HE sample root not found: $SampleRoot"
}

$supportedExtensions = @(".edf", ".bdf", ".fif", ".fiff")
$edfFiles = Get-ChildItem -LiteralPath $SampleRoot -File | Where-Object {
  $supportedExtensions -contains $_.Extension.ToLowerInvariant()
}
if (-not $edfFiles) {
  throw "No supported EEG sample files found under: $SampleRoot"
}

$env:QLANALYSER_ENV = "local"
$env:QLANALYSER_LAB_EPILEPSY_FULL_FLOW_ENABLED = "1"
$env:QLANALYSER_LAB_HE_SAMPLE_ROOT = $SampleRoot

Write-Host "QLanalyser lab epilepsy full-flow local environment"
Write-Host "Repo:        $RepoRoot"
Write-Host "SampleRoot:  $SampleRoot"
Write-Host "Backend:     http://127.0.0.1:$BackendPort/api"
Write-Host "Frontend:    http://127.0.0.1:$FrontendPort/epilepsy-full-flow-preview.html?api=http://127.0.0.1:$BackendPort/api"
Write-Host ""
Write-Host "Required env has been set for this process:"
Write-Host "  QLANALYSER_ENV=$env:QLANALYSER_ENV"
Write-Host "  QLANALYSER_LAB_EPILEPSY_FULL_FLOW_ENABLED=$env:QLANALYSER_LAB_EPILEPSY_FULL_FLOW_ENABLED"
Write-Host "  QLANALYSER_LAB_HE_SAMPLE_ROOT=$env:QLANALYSER_LAB_HE_SAMPLE_ROOT"
Write-Host ""

if ($StartFrontend) {
  $frontendDir = Join-Path $RepoRoot "frontend"
  Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$frontendDir'; npx http-server . -p $FrontendPort -c-1"
  ) -WindowStyle Hidden
  Write-Host "Frontend static server requested on port $FrontendPort."
}

& $PythonExe -m uvicorn backend.main:app --host 127.0.0.1 --port $BackendPort
