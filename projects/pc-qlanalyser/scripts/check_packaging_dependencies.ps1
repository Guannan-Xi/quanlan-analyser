[CmdletBinding()]
param(
    [string]$VenvDir,
    [string]$ExpectedPythonVersion = "3.12.4",
    [switch]$CheckDist,
    [switch]$AllowBundledLicence
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$Script:Results = @()

function Add-CheckResult {
    param(
        [ValidateSet("PASS", "WARN", "FAIL")]
        [string]$Status,
        [string]$Category,
        [string]$Item,
        [string]$Detail
    )

    $Script:Results += [pscustomobject]@{
        Status   = $Status
        Category = $Category
        Item     = $Item
        Detail   = $Detail
    }

    $color = switch ($Status) {
        "PASS" { "Green" }
        "WARN" { "Yellow" }
        "FAIL" { "Red" }
    }

    Write-Host ("[{0}] {1} - {2}: {3}" -f $Status, $Category, $Item, $Detail) -ForegroundColor $color
}

function Get-FullPathOrOriginal {
    param([string]$Path)

    try {
        return [System.IO.Path]::GetFullPath($Path)
    }
    catch {
        return $Path
    }
}

function Test-RequiredPath {
    param(
        [string]$TargetPath,
        [ValidateSet("File", "Directory", "Any")]
        [string]$Kind,
        [string]$Category,
        [string]$Item
    )

    $exists = Test-Path -LiteralPath $TargetPath
    if (-not $exists) {
        Add-CheckResult "FAIL" $Category $Item ("Missing: {0}" -f $TargetPath)
        return
    }

    if ($Kind -eq "File" -and -not (Test-Path -LiteralPath $TargetPath -PathType Leaf)) {
        Add-CheckResult "FAIL" $Category $Item ("Expected file but found non-file path: {0}" -f $TargetPath)
        return
    }

    if ($Kind -eq "Directory" -and -not (Test-Path -LiteralPath $TargetPath -PathType Container)) {
        Add-CheckResult "FAIL" $Category $Item ("Expected directory but found non-directory path: {0}" -f $TargetPath)
        return
    }

    Add-CheckResult "PASS" $Category $Item $TargetPath
}

function Invoke-Capture {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    $oldErrorActionPreference = $ErrorActionPreference
    $oldNativeErrorPreference = $null
    $hasNativeErrorPreference = Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Local -ErrorAction SilentlyContinue
    if ($hasNativeErrorPreference) {
        $oldNativeErrorPreference = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
    }

    try {
        $ErrorActionPreference = "Continue"
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    catch {
        $output = @($_.Exception.Message)
        $exitCode = 1
    }
    finally {
        $ErrorActionPreference = $oldErrorActionPreference
        if ($hasNativeErrorPreference) {
            $PSNativeCommandUseErrorActionPreference = $oldNativeErrorPreference
        }
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output   = ($output | ForEach-Object { $_.ToString() }) -join "`n"
    }
}

function Test-CommandInsideVenv {
    param(
        [string]$CommandName,
        [string]$VenvRoot,
        [string]$Category
    )

    $cmd = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Add-CheckResult "FAIL" $Category $CommandName "Command not found in current PATH."
        return
    }

    $cmdPath = Get-FullPathOrOriginal $cmd.Source
    $venvPath = (Get-FullPathOrOriginal $VenvRoot).TrimEnd("\")
    if ($cmdPath.StartsWith($venvPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        Add-CheckResult "PASS" $Category $CommandName $cmdPath
    }
    else {
        Add-CheckResult "FAIL" $Category $CommandName ("Current command resolves to {0}; activate {1} before running build.ps1." -f $cmdPath, $venvPath)
    }
}

function Invoke-PythonJsonCheck {
    param(
        [string]$PythonExe,
        [string]$Code,
        [string[]]$Arguments,
        [string]$Category,
        [string]$Item
    )

    $encodedCode = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($Code))
    $wrapperCode = "import base64,sys;code=base64.b64decode(sys.argv[1]).decode('utf-8');sys.argv=[sys.argv[0]]+sys.argv[2:];exec(compile(code,'<preflight>','exec'))"
    $result = Invoke-Capture $PythonExe (@("-c", $wrapperCode, $encodedCode) + $Arguments)
    if ($result.ExitCode -ne 0) {
        Add-CheckResult "FAIL" $Category $Item $result.Output
        return $null
    }

    $lines = @($result.Output -split "`n" | Where-Object { $_.Trim().Length -gt 0 })
    if (-not $lines -or $lines.Count -eq 0) {
        Add-CheckResult "FAIL" $Category $Item "Python check produced no JSON output."
        return $null
    }

    $jsonLine = $lines[-1]
    try {
        return $jsonLine | ConvertFrom-Json
    }
    catch {
        Add-CheckResult "FAIL" $Category $Item ("Cannot parse JSON output: {0}" -f $jsonLine)
        return $null
    }
}

$AppDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RepoRoot = (Resolve-Path (Join-Path $AppDir "..")).Path
if (-not $VenvDir -or $VenvDir.Trim().Length -eq 0) {
    $VenvDir = Join-Path $RepoRoot "venv"
}
$VenvDir = Get-FullPathOrOriginal $VenvDir
$VenvPython = Join-Path $VenvDir "python.exe"
$RequirementsPath = Join-Path $RepoRoot "requirements.txt"
$SitePackages = $null

Write-Host ""
Write-Host "Packaging dependency preflight" -ForegroundColor Cyan
Write-Host ("AppDir   : {0}" -f $AppDir)
Write-Host ("RepoRoot : {0}" -f $RepoRoot)
Write-Host ("VenvDir  : {0}" -f $VenvDir)
Write-Host ""

Test-RequiredPath $AppDir "Directory" "project" "AR_analyser_PC directory"
Test-RequiredPath (Join-Path $AppDir "AR_analyser.py") "File" "project" "entry point"
Test-RequiredPath (Join-Path $AppDir "build.ps1") "File" "project" "build script"
Test-RequiredPath (Join-Path $AppDir "QLanalyser.iss") "File" "project" "Inno Setup script"
Test-RequiredPath $RequirementsPath "File" "project" "requirements.txt"
Test-RequiredPath $VenvDir "Directory" "environment" "venv directory"
Test-RequiredPath $VenvPython "File" "environment" "venv python.exe"

if (Test-Path -LiteralPath $VenvPython -PathType Leaf) {
    $versionResult = Invoke-Capture $VenvPython @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3]))); print(sys.executable)")
    if ($versionResult.ExitCode -ne 0) {
        Add-CheckResult "FAIL" "environment" "python version" $versionResult.Output
    }
    else {
        $versionLines = $versionResult.Output -split "`n"
        $actualVersion = $versionLines[0].Trim()
        if ($actualVersion -eq $ExpectedPythonVersion) {
            Add-CheckResult "PASS" "environment" "python version" $actualVersion
        }
        else {
            Add-CheckResult "FAIL" "environment" "python version" ("Expected {0}, actual {1}" -f $ExpectedPythonVersion, $actualVersion)
        }
    }

    Test-CommandInsideVenv "python" $VenvDir "active shell"
    Test-CommandInsideVenv "pyinstaller" $VenvDir "active shell"

    $pathsCode = @'
import json
import sysconfig
paths = sysconfig.get_paths()
print(json.dumps({"purelib": paths.get("purelib"), "platlib": paths.get("platlib")}))
'@
    $paths = Invoke-PythonJsonCheck -PythonExe $VenvPython -Code $pathsCode -Arguments @() -Category "environment" -Item "site-packages"
    if ($paths) {
        $candidates = @(@($paths.purelib, $paths.platlib) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) })
        if ($candidates.Count -gt 0) {
            $SitePackages = $candidates[0]
            Add-CheckResult "PASS" "environment" "site-packages" $SitePackages
        }
        else {
            Add-CheckResult "FAIL" "environment" "site-packages" "Cannot locate site-packages from python sysconfig."
        }
    }
}

if ($SitePackages) {
    $pyMajorMinor = ($ExpectedPythonVersion -split "\.")[0..1] -join ""
    $expectedAbi = "cp{0}" -f $pyMajorMinor

    $privatePaths = @(
        @{ Item = "AR_neurokit2 package"; Kind = "Directory"; Path = Join-Path $SitePackages "AR_neurokit2" },
        @{ Item = "AR_neurokit2 CUDA pyd"; Kind = "File"; Path = Join-Path $SitePackages ("AR_neurokit2_cuda_fullscale.{0}-win_amd64.pyd" -f $expectedAbi) },
        @{ Item = "cuda_cpp_fullscale package"; Kind = "Directory"; Path = Join-Path $SitePackages "cuda_cpp_fullscale" },
        @{ Item = "ar_neurokit2_rust package"; Kind = "Directory"; Path = Join-Path $SitePackages "ar_neurokit2_rust" },
        @{ Item = "ECG_analyser package"; Kind = "Directory"; Path = Join-Path $SitePackages "ECG_analyser" },
        @{ Item = "EMG_analyser package"; Kind = "Directory"; Path = Join-Path $SitePackages "EMG_analyser" },
        @{ Item = "LFP_EEG_analyser package"; Kind = "Directory"; Path = Join-Path $SitePackages "LFP_EEG_analyser" },
        @{ Item = "pyeeg package"; Kind = "Directory"; Path = Join-Path $SitePackages "pyeeg" }
    )

    foreach ($p in $privatePaths) {
        Test-RequiredPath $p.Path $p.Kind "site-packages private dependencies" $p.Item
    }
}

if ((Test-Path -LiteralPath $VenvPython -PathType Leaf) -and (Test-Path -LiteralPath $RequirementsPath -PathType Leaf)) {
    $reqCode = @'
import importlib.metadata as md
import json
import pathlib
import sys
from packaging.requirements import Requirement

req_path = pathlib.Path(sys.argv[1])
missing = []
mismatch = []
invalid = []
checked = 0

for line_no, raw_line in enumerate(req_path.read_text(encoding="utf-8").splitlines(), 1):
    text = raw_line.split("#", 1)[0].strip()
    if not text:
        continue
    try:
        req = Requirement(text)
    except Exception as exc:
        invalid.append({"line": line_no, "text": text, "error": str(exc)})
        continue
    checked += 1
    try:
        installed = md.version(req.name)
    except md.PackageNotFoundError:
        missing.append({"line": line_no, "name": req.name, "required": str(req.specifier)})
        continue
    if req.specifier and not req.specifier.contains(installed, prereleases=True):
        mismatch.append({"line": line_no, "name": req.name, "installed": installed, "required": str(req.specifier)})

print(json.dumps({"checked": checked, "missing": missing, "mismatch": mismatch, "invalid": invalid}, ensure_ascii=False))
'@

    $req = Invoke-PythonJsonCheck -PythonExe $VenvPython -Code $reqCode -Arguments @($RequirementsPath) -Category "requirements" -Item "parse requirements.txt"
    if ($req) {
        $invalidReqs = @($req.invalid)
        $missingReqs = @($req.missing)
        $mismatchedReqs = @($req.mismatch)

        if ($invalidReqs.Count -gt 0) {
            foreach ($item in $invalidReqs) {
                Add-CheckResult "FAIL" "requirements" ("invalid line {0}" -f $item.line) ("{0} ({1})" -f $item.text, $item.error)
            }
        }
        if ($missingReqs.Count -gt 0) {
            foreach ($item in $missingReqs) {
                Add-CheckResult "FAIL" "requirements" $item.name ("Missing requirement from line {0}: {1}" -f $item.line, $item.required)
            }
        }
        if ($mismatchedReqs.Count -gt 0) {
            foreach ($item in $mismatchedReqs) {
                Add-CheckResult "FAIL" "requirements" $item.name ("Installed {0}, required {1} from line {2}" -f $item.installed, $item.required, $item.line)
            }
        }
        if ($invalidReqs.Count -eq 0 -and $missingReqs.Count -eq 0 -and $mismatchedReqs.Count -eq 0) {
            Add-CheckResult "PASS" "requirements" "requirements.txt" ("Checked {0} pinned requirements." -f $req.checked)
        }
    }

    $pipCheck = Invoke-Capture $VenvPython @("-m", "pip", "check")
    if ($pipCheck.ExitCode -eq 0) {
        Add-CheckResult "PASS" "requirements" "pip check" $pipCheck.Output.Trim()
    }
    else {
        Add-CheckResult "FAIL" "requirements" "pip check" $pipCheck.Output
    }

    $importCode = @'
import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

checks = [
    ("PyInstaller", "import PyInstaller"),
    ("PyQt5", "import PyQt5"),
    ("PyQt5.QtWebEngineWidgets", "from PyQt5.QtWebEngineWidgets import QWebEngineView"),
    ("numpy", "import numpy"),
    ("pandas", "import pandas"),
    ("scipy", "import scipy"),
    ("sklearn", "import sklearn"),
    ("mne", "import mne"),
    ("lspopt", "import lspopt"),
    ("lightgbm", "import lightgbm"),
    ("xgboost", "import xgboost"),
    ("cv2", "import cv2"),
    ("pyedflib", "import pyedflib"),
    ("openpyxl", "import openpyxl"),
    ("OpenGL", "import OpenGL"),
    ("OpenGL_accelerate", "import OpenGL_accelerate"),
    ("pyqtgraph", "import pyqtgraph"),
    ("Crypto", "import Crypto"),
    ("yaml", "import yaml"),
    ("WMI", "import wmi"),
    ("pyeeg forrestbao api", "import pyeeg; assert hasattr(pyeeg, 'hjorth') and hasattr(pyeeg, 'pfd')"),
    ("AR_neurokit2", "import AR_neurokit2"),
    ("AR_neurokit2 rust wrapper", "from AR_neurokit2.complexity import _rust_backend"),
    ("AR_neurokit2 cuda wrapper", "from AR_neurokit2.complexity import _cuda_cpp_fullscale_backend"),
    ("AR_neurokit2_cuda_fullscale pyd", "import AR_neurokit2_cuda_fullscale"),
    ("ar_neurokit2_rust", "import ar_neurokit2_rust"),
    ("cuda_cpp_fullscale", "import cuda_cpp_fullscale"),
    ("ECG_analyser process", "from ECG_analyser.ECG_analyser3 import process_ecg_file"),
    ("EMG_analyser process", "from EMG_analyser.EMG_analyser_utils.EMG_analyser import analyze_emg_data"),
    ("LFP_EEG_analyser bandpower", "from LFP_EEG_analyser.LFP_EEG_analyser.bandpower_analysis import calculate_bandpower"),
]

results = []
for name, code in checks:
    try:
        ns = {}
        exec(code, ns, ns)
        results.append({"name": name, "ok": True})
    except Exception as exc:
        results.append({"name": name, "ok": False, "error": type(exc).__name__ + ": " + str(exc)})

print(json.dumps(results, ensure_ascii=False))
'@

    $imports = Invoke-PythonJsonCheck -PythonExe $VenvPython -Code $importCode -Arguments @() -Category "imports" -Item "critical imports"
    if ($imports) {
        foreach ($item in @($imports)) {
            if ($item.ok) {
                Add-CheckResult "PASS" "imports" $item.name "Import OK"
            }
            else {
                Add-CheckResult "FAIL" "imports" $item.name $item.error
            }
        }
    }
}

$requiredProjectPaths = @(
    @{ Item = "config.dat"; Kind = "File"; Path = Join-Path $AppDir "config\config.dat" },
    @{ Item = "config_production.dat"; Kind = "File"; Path = Join-Path $AppDir "config\config_production.dat" },
    @{ Item = "licence_core.dll"; Kind = "File"; Path = Join-Path $AppDir "resource\licence_core.dll" },
    @{ Item = "QL1.ico"; Kind = "File"; Path = Join-Path $AppDir "QL1.ico" },
    @{ Item = "update.bat"; Kind = "File"; Path = Join-Path $AppDir "update.bat" },
    @{ Item = "Qlass 1EEG model"; Kind = "File"; Path = Join-Path $AppDir "src\Qlass\models\2_LightGBM-1EEG.pkl" },
    @{ Item = "Qlass feature order"; Kind = "File"; Path = Join-Path $AppDir "src\Qlass\models\feature_order.csv" },
    @{ Item = "newEpilepsy model_n1814_5s"; Kind = "File"; Path = Join-Path $AppDir "src\newEpilepsy\model_n1814_5s.sav" },
    @{ Item = "newEpilepsy model_n762_3s"; Kind = "File"; Path = Join-Path $AppDir "src\newEpilepsy\model_n762_3s.sav" },
    @{ Item = "newEpilepsy scaler_n1814_5s"; Kind = "File"; Path = Join-Path $AppDir "src\newEpilepsy\scaler_n1814_5s.sav" },
    @{ Item = "newEpilepsy scaler_n762_3s"; Kind = "File"; Path = Join-Path $AppDir "src\newEpilepsy\scaler_n762_3s.sav" },
    @{ Item = "qEEG EEGnorms"; Kind = "Directory"; Path = Join-Path $AppDir "src\qeeg_algorithm-main\EEGnorms" },
    @{ Item = "qEEG qeeg"; Kind = "Directory"; Path = Join-Path $AppDir "src\qeeg_algorithm-main\qeeg" }
)

foreach ($p in $requiredProjectPaths) {
    Test-RequiredPath $p.Path $p.Kind "project resources" $p.Item
}

$sourceLicence = Join-Path $AppDir "resource\licence.lic"
if (Test-Path -LiteralPath $sourceLicence -PathType Leaf) {
    Add-CheckResult "WARN" "release hygiene" "source licence.lic" ("Release-sensitive auth file exists: {0}" -f $sourceLicence)
}
else {
    Add-CheckResult "PASS" "release hygiene" "source licence.lic" "No source licence.lic found."
}

$DistDirForLicenceCheck = Join-Path $AppDir "dist\AR_analyser"
$InternalDirForLicenceCheck = Join-Path $DistDirForLicenceCheck "_internal"
$bundledLicences = @(
    (Join-Path $DistDirForLicenceCheck "resource\licence.lic"),
    (Join-Path $InternalDirForLicenceCheck "resource\licence.lic")
)
foreach ($lic in $bundledLicences) {
    if (Test-Path -LiteralPath $lic -PathType Leaf) {
        if ($AllowBundledLicence) {
            Add-CheckResult "WARN" "release hygiene" "bundled licence.lic" ("Allowed by parameter: {0}" -f $lic)
        }
        else {
            Add-CheckResult "FAIL" "release hygiene" "bundled licence.lic" ("Remove before installer build: {0}" -f $lic)
        }
    }
}

if ($CheckDist) {
    $DistDir = Join-Path $AppDir "dist\AR_analyser"
    $InternalDir = Join-Path $DistDir "_internal"

    $distPaths = @(
        @{ Item = "dist AR_analyser.exe"; Kind = "File"; Path = Join-Path $DistDir "AR_analyser.exe" },
        @{ Item = "dist _internal"; Kind = "Directory"; Path = $InternalDir },
        @{ Item = "dist config.dat"; Kind = "File"; Path = Join-Path $DistDir "config\config.dat" },
        @{ Item = "dist QL1.ico"; Kind = "File"; Path = Join-Path $DistDir "QL1.ico" },
        @{ Item = "dist update.bat"; Kind = "File"; Path = Join-Path $DistDir "update.bat" },
        @{ Item = "dist licence_core.dll"; Kind = "File"; Path = Join-Path $InternalDir "resource\licence_core.dll" },
        @{ Item = "dist AR_neurokit2 CUDA pyd"; Kind = "File"; Path = Join-Path $InternalDir ("AR_neurokit2_cuda_fullscale.{0}-win_amd64.pyd" -f ("cp" + (($ExpectedPythonVersion -split "\.")[0..1] -join ""))) },
        @{ Item = "dist cuda_cpp_fullscale"; Kind = "Directory"; Path = Join-Path $InternalDir "cuda_cpp_fullscale" },
        @{ Item = "dist ar_neurokit2_rust"; Kind = "Directory"; Path = Join-Path $InternalDir "ar_neurokit2_rust" },
        @{ Item = "dist numpy"; Kind = "Directory"; Path = Join-Path $InternalDir "numpy" },
        @{ Item = "dist mne"; Kind = "Directory"; Path = Join-Path $InternalDir "mne" },
        @{ Item = "dist lspopt"; Kind = "Directory"; Path = Join-Path $InternalDir "lspopt" },
        @{ Item = "dist lightgbm"; Kind = "Directory"; Path = Join-Path $InternalDir "lightgbm" },
        @{ Item = "dist xgboost"; Kind = "Directory"; Path = Join-Path $InternalDir "xgboost" },
        @{ Item = "dist xgboost.dll lib"; Kind = "File"; Path = Join-Path $InternalDir "lib\xgboost.dll" },
        @{ Item = "dist Qlass model"; Kind = "File"; Path = Join-Path $InternalDir "src\Qlass\models\2_LightGBM-1EEG.pkl" },
        @{ Item = "dist Qlass feature order"; Kind = "File"; Path = Join-Path $InternalDir "src\Qlass\models\feature_order.csv" },
        @{ Item = "dist newEpilepsy"; Kind = "Directory"; Path = Join-Path $InternalDir "src\newEpilepsy" },
        @{ Item = "dist qEEG EEGnorms"; Kind = "Directory"; Path = Join-Path $InternalDir "src\qeeg_algorithm-main\EEGnorms" },
        @{ Item = "dist qEEG qeeg"; Kind = "Directory"; Path = Join-Path $InternalDir "src\qeeg_algorithm-main\qeeg" }
    )

    foreach ($p in $distPaths) {
        Test-RequiredPath $p.Path $p.Kind "dist" $p.Item
    }

    $issPath = Join-Path $AppDir "QLanalyser.iss"
    if (Test-Path -LiteralPath $issPath -PathType Leaf) {
        $issText = Get-Content -LiteralPath $issPath -Raw
        $exeName = "AR_analyser.exe"
        $exeDefine = [regex]::Match($issText, '#define\s+MyAppExeName\s+"([^"]+)"')
        if ($exeDefine.Success) {
            $exeName = $exeDefine.Groups[1].Value
        }

        $sourceMatches = [regex]::Matches($issText, 'Source:\s*"([^"]+)"')
        foreach ($match in $sourceMatches) {
            $rawSource = $match.Groups[1].Value.Replace("{#MyAppExeName}", $exeName)
            $sourceToCheck = $rawSource
            if (-not [System.IO.Path]::IsPathRooted($sourceToCheck)) {
                $sourceToCheck = Join-Path $AppDir $sourceToCheck
            }
            if ($sourceToCheck.EndsWith("\*")) {
                $sourceToCheck = Split-Path $sourceToCheck -Parent
            }
            if (Test-Path -LiteralPath $sourceToCheck) {
                Add-CheckResult "PASS" "installer script" $rawSource $sourceToCheck
            }
            else {
                Add-CheckResult "FAIL" "installer script" $rawSource ("Source path does not exist: {0}" -f $sourceToCheck)
            }
        }
    }
}

Write-Host ""
$failCount = @($Script:Results | Where-Object { $_.Status -eq "FAIL" }).Count
$warnCount = @($Script:Results | Where-Object { $_.Status -eq "WARN" }).Count
$passCount = @($Script:Results | Where-Object { $_.Status -eq "PASS" }).Count

Write-Host ("Summary: PASS={0}, WARN={1}, FAIL={2}" -f $passCount, $warnCount, $failCount) -ForegroundColor Cyan
if ($failCount -gt 0) {
    Write-Host "Preflight failed. Fix FAIL items before packaging." -ForegroundColor Red
    exit 1
}

if ($warnCount -gt 0) {
    Write-Host "Preflight passed with warnings. Review WARN items before release." -ForegroundColor Yellow
}
else {
    Write-Host "Preflight passed." -ForegroundColor Green
}

exit 0
