$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "QLanalyser ECS Static Frontend Deploy"

$server = "39.97.248.225"
$remote = "/opt/qlanalyser"
$workspace = "D:\Quanlan\Codes\Python\quanlan-analyser\outputs\eeglab-mne-mvp"
$stage = "C:\Users\XGN\Documents\Codex\2026-06-11\mne\outputs\deploy_stage\outputs\aliyun-static-lite"
$pkg = Join-Path $env:TEMP "qlanalyser-static-lite.zip"

function Run-Native($description, $file, [string[]]$arguments) {
  Write-Host ""
  Write-Host "============================================================"
  Write-Host $description
  Write-Host "============================================================"
  & $file @arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$description failed with exit code $LASTEXITCODE"
  }
}

Write-Host ""
Write-Host "QLanalyser static frontend deploy to ECS $server"
Write-Host "Password input is hidden by SSH. Type the root password and press Enter."
Write-Host "This deploy only updates /opt/qlanalyser/outputs/aliyun-static-lite."
Write-Host ""
Read-Host "Press Enter to start"

if (Test-Path -LiteralPath $pkg) { Remove-Item -LiteralPath $pkg -Force }
Push-Location (Split-Path -Parent $stage)
try {
  Compress-Archive -LiteralPath ".\aliyun-static-lite" -DestinationPath $pkg -Force
} finally {
  Pop-Location
}

Run-Native "1/3 Upload static package" "scp" @(
  "-o", "PreferredAuthentications=password",
  "-o", "PubkeyAuthentication=no",
  "-o", "StrictHostKeyChecking=accept-new",
  $pkg,
  "root@${server}:$remote/qlanalyser-static-lite.zip"
)

Run-Native "2/3 Replace static frontend and restart service" "ssh" @(
  "-o", "PreferredAuthentications=password",
  "-o", "PubkeyAuthentication=no",
  "-o", "StrictHostKeyChecking=accept-new",
  "root@$server",
  "cd $remote && mkdir -p outputs && rm -rf outputs/aliyun-static-lite && unzip -o qlanalyser-static-lite.zip -d outputs && systemctl restart qlanalyser && sleep 2 && curl -fsS http://127.0.0.1/health"
)

Write-Host ""
Write-Host "============================================================"
Write-Host "3/3 Public verification"
Write-Host "============================================================"
Invoke-WebRequest -UseBasicParsing "http://$server/health" -TimeoutSec 20 | Select-Object -ExpandProperty Content
Write-Host ""
Write-Host "DEPLOY DONE: http://$server/"
Read-Host "Press Enter to close"
