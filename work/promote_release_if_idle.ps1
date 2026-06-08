param(
  [string]$Root = "D:\Quanlan\Codes\Python\quanlan-analyser"
)

$ErrorActionPreference = "Stop"

$dev = Join-Path $Root "outputs\eeglab-mne-dev"
$release = Join-Path $Root "outputs\eeglab-mne-release"
$candidate = Join-Path $dev "release-candidate"
$runtimePath = Join-Path $release "assets\runtime-state.json"
$validateScript = Join-Path $Root "work\validate_release.js"

if (-not (Test-Path -LiteralPath $dev)) {
  throw "Development version not found: $dev"
}
if (-not (Test-Path -LiteralPath $release)) {
  throw "Release version not found: $release"
}

if (-not (Test-Path -LiteralPath $runtimePath)) {
  $runtimeDir = Split-Path -Parent $runtimePath
  if (-not (Test-Path -LiteralPath $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
  }
  $initialRuntime = @{
    runningTasks = @()
    queuedTasks = @()
    completedResults = @()
    upgrade = @{
      status = "idle"
      source = "runtime-state-created-by-promote-script"
      lastPromotedAt = $null
    }
  } | ConvertTo-Json -Depth 8
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($runtimePath, $initialRuntime, $utf8NoBom)
  Write-Output "Release runtime state was missing; created idle runtime-state.json."
}

$runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
$activeCount = @($runtime.runningTasks).Count + @($runtime.queuedTasks).Count
if ($activeCount -gt 0) {
  Write-Output "Release promotion skipped: $activeCount queued/running task(s)."
  exit 0
}

if (Test-Path -LiteralPath $candidate) {
  $temp = Join-Path $Root "outputs\.release-candidate-validation"
  if (Test-Path -LiteralPath $temp) {
    Remove-Item -LiteralPath $temp -Recurse -Force
  }
  Copy-Item -LiteralPath $candidate -Destination $temp -Recurse
  if (-not (Test-Path -LiteralPath (Join-Path $temp "assets\runtime-state.json"))) {
    New-Item -ItemType Directory -Path (Join-Path $temp "assets") -Force | Out-Null
    Copy-Item -LiteralPath $runtimePath -Destination (Join-Path $temp "assets\runtime-state.json") -Force
  }
  node $validateScript $temp | Write-Output

  $preservedRuntime = Get-Content -LiteralPath $runtimePath -Raw
  Get-ChildItem -LiteralPath $release -Force | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Recurse -Force
  }
  Get-ChildItem -LiteralPath $temp -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $release -Recurse -Force
  }
  if (-not (Test-Path -LiteralPath (Split-Path -Parent $runtimePath))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $runtimePath) -Force | Out-Null
  }
  $preservedRuntime | Set-Content -LiteralPath $runtimePath -Encoding UTF8
  Remove-Item -LiteralPath $temp -Recurse -Force
  Write-Output "Release candidate promoted from development."
} else {
  node $validateScript $release | Write-Output
  Write-Output "No development release-candidate found; current release validated only."
}

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
if ($null -eq $runtime.upgrade) {
  $runtime | Add-Member -MemberType NoteProperty -Name upgrade -Value ([pscustomobject]@{}) -Force
}
$runtime.upgrade.status = "idle"
$runtime.upgrade.lastPromotedAt = $stamp
$runtime.upgrade.source = "outputs/eeglab-mne-dev"
$json = $runtime | ConvertTo-Json -Depth 8
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($runtimePath, $json, $utf8NoBom)

Write-Output "Release is idle and validated. Promotion marker updated at $stamp."
