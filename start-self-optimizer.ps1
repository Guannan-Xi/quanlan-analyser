param(
  [string]$Root = "D:\Quanlan\Codes\Python\quanlan-analyser"
)

$ErrorActionPreference = "Stop"
$Script = Join-Path $Root "work\self_optimizer.js"
if (-not (Test-Path -LiteralPath $Script)) {
  throw "Self optimizer script not found: $Script"
}

Start-Process -FilePath "node" -ArgumentList "work\self_optimizer.js --daemon" -WorkingDirectory $Root -WindowStyle Hidden
Write-Output "QL脑电分析平台 self-optimizer started. Log: $(Join-Path $Root 'outputs\eeglab-mne-dev\assets\realtime_optimizer\self_optimizer_log.jsonl')"
