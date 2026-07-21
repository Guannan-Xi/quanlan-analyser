param(
  [string]$Root = "D:\Quanlan\Codes\Python\quanlan-analyser"
)

$ErrorActionPreference = "Stop"
$Script = Join-Path $Root "work\self_optimizer.js"
if (-not (Test-Path -LiteralPath $Script)) {
  throw "Self optimizer script not found: $Script"
}

$existing = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -eq "node.exe" -and
    $_.CommandLine -like "*work\self_optimizer.js --daemon*"
  }
if ($existing) {
  $ids = ($existing | Select-Object -ExpandProperty ProcessId) -join ", "
  Write-Output "QL analyser self-optimizer already running. PID(s): $ids"
  exit 0
}

# Fast learning cadence: scan every 1 minute, idle/role-play learning every 3 minutes.
$env:QL_SELF_OPTIMIZER_INTERVAL_MS = "60000"
$env:QL_SELF_OPTIMIZER_IDLE_UPDATE_MIN_MS = "180000"
$env:QL_SELF_OPTIMIZER_ROLEPLAY_UPDATE_MIN_MS = "180000"
$env:QL_SELF_OPTIMIZER_DEV_IDLE_STABLE_MS = "180000"

Start-Process -FilePath "node" -ArgumentList "work\self_optimizer.js --daemon" -WorkingDirectory $Root -WindowStyle Hidden
Write-Output "QL analyser self-optimizer started. Log: $(Join-Path $Root 'outputs\eeglab-mne-dev\assets\realtime_optimizer\self_optimizer_log.jsonl')"
