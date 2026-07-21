# 定义配置文件路径
Set-Location $PSScriptRoot
$preflightScript = Join-Path $PSScriptRoot ".\scripts\check_packaging_dependencies.ps1"
if (Test-Path $preflightScript) {
    & $preflightScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "err: packaging dependency preflight failed!" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
$configDevPath = Join-Path $PSScriptRoot ".\config\config.dat"
$configProductionPath = Join-Path $PSScriptRoot ".\config\config_production.dat"

# 检查配置文件是否存在
if (-not (Test-Path $configProductionPath)) {
    Write-Host "err: config_production.dat does not exist!" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $configDevPath)) {
    Write-Host "err: config.dat does not exist!" -ForegroundColor Red
    exit 1
}

do{
    Write-Host "Please select the environment you want to keep: ('d' for development or 'p' for production):" -NoNewline
    $env = Read-Host
    $selectedFile = $null
    switch ($env.ToLower().Trim()) {
        { $_ -in "d" } {
            $selectedFile = $configDevPath
            $lines = Get-Content $selectedFile

            # 确认 ip 环境和版本号
            Write-Host $($lines[0])
            Write-Host $($lines[1])
            Write-Host $($lines[2])
            Write-Host $($lines[3])
            Write-Host "Confirm to continue? (y/n):" -NoNewline
            $confirm = Read-Host
            if ($confirm.ToLower().Trim() -ne 'y') {
                Write-Host "User canceled, exiting script." -ForegroundColor Yellow
                exit 0
            }

            # 保留开发环境：仅删除生产配置
            Remove-Item -Path $configProductionPath -Force
            break
        }
        { $_ -in "p" } {
            $selectedFile = $configProductionPath

            # 保留生产环境
            $devLines = Get-Content $configDevPath
            $proLines = Get-Content $configProductionPath

            # 替换 ip 
            $devLines[0] = $proLines[0]
            $devLines[3] = $proLines[3]

            # 确认 ip 环境和版本号
            Write-Host $($devLines[0])
            Write-Host $($devLines[1])
            Write-Host $($devLines[2])
            Write-Host $($devLines[3])
            Write-Host "Confirm to continue? (y/n):" -NoNewline
            $confirm = Read-Host
            if ($confirm.ToLower().Trim() -ne 'y') {
                Write-Host "User canceled, exiting script." -ForegroundColor Yellow
                exit 0
            }

            # 将修改后的内容写回 config.dat
            # Set-Content -Path $configDevPath -Value $devLines -Encoding UTF8
            # 使用 UTF8 编码（不带 BOM）创建 StreamWriter
            $utf8NoBom = New-Object System.Text.UTF8Encoding $false
            # 使用 StreamWriter 写入文件
            $writer = [System.IO.StreamWriter]::new($configDevPath, $false, $utf8NoBom)
            try {
                # 写入内容（自动处理换行符）
                $writer.Write(($devLines -join "`r`n"))
            } finally {
                $writer.Close()
            }

            # 删除生产配置文件
            Remove-Item -Path $configProductionPath -Force
            break
        }
        Default {
            Write-Host "err: Invalid input. Please enter 'd' for development or 'p' for production." -ForegroundColor Red
        }
    }
} until ($selectedFile)

Write-Host "Config setup complete." -ForegroundColor Green
    

# 添加更多 numpy 相关的隐藏导入和数据文件
pyinstaller  --noconsole --paths=. `
    --icon=QL1.ico `
    --add-data="QL1.ico;." `
    --add-data="src/newEpilepsy;src/newEpilepsy" `
    --hidden-import=subprocess `
    --hidden-import=pyedfilb `
    --hidden-import=markdown `
    --hidden-import=openai `
    --hidden-import=lazy_loader `
    --hidden-import=lightgbm `
    --hidden-import=numpy `
    --hidden-import=numpy.core `
    --hidden-import=numpy.core._methods `
    --hidden-import=numpy.lib.format `
    --hidden-import=numpy.random `
    --hidden-import=numpy._core `
    --hidden-import=numpy.core.multiarray `
    --hidden-import=numpy.core.numeric `
    --hidden-import=numpy.core.umath `
    --hidden-import=numpy.linalg.linalg `
    --hidden-import=numpy.random `
    --hidden-import=openpyxl `
    --hidden-import=openpyxl.cell._writer `
    --hidden-import=OpenGL_accelerate `
    --hidden-import=OpenGL.arrays `
    --hidden-import=et_xmlfile `
    --hidden-import=pandas.io.excel._openpyxl `
    --hidden-import=openpyxl.workbook `
    --hidden-import=openpyxl.writer.excel `
    --hidden-import=pandas.io.formats.excel `
    --hidden-import=pandas.io.excel._base `
    --hidden-import=matplotlib.backends.backend_svg `
    --hidden-import=matplotlib.backends.backend_eps `
    --hidden-import=matplotlib.backends.backend_ps `
    --hidden-import=matplotlib.backends.backend_pdf `
    --hidden-import=matplotlib.backends.backend_pgf `
    --hidden-import=matplotlib.backends.backend_cairo `
    --hidden-import=matplotlib.backends.backend_agg `
    --hidden-import=matplotlib.backends.backend_qt5agg `
    --hidden-import=matplotlib.backends._backend_pdf_ps `
    --hidden-import=ar_neurokit2_rust `
    --hidden-import=ar_neurokit2_rust.ar_neurokit2_rust `
    --hidden-import=AR_neurokit2_cuda_fullscale `
    --hidden-import=AR_neurokit2.complexity._cuda_cpp_fullscale_backend `
    --collect-all=pandas `
    --collect-all=numpy `
    --collect-all=scipy `
    --collect-all=sklearn `
    --collect-all=openpyxl `
    --collect-all=OpenGL `
    --collect-all=OpenGL_accelerate `
    --collect-all=xgboost `
    --collect-all=ar_neurokit2_rust `
    --add-binary="resource\licence_core.dll;resource" `
    --add-binary="..\venv\Lib\site-packages\AR_neurokit2_cuda_fullscale.cp312-win_amd64.pyd;." `
    --add-data="..\venv\Lib\site-packages\cuda_cpp_fullscale;cuda_cpp_fullscale" `
    AR_analyser.py

$targetDir = ".\dist\AR_analyser\_internal"
$targetDir_icon = ".\dist\AR_analyser"
if (!(Test-Path $targetDir)) {
    New-Item -ItemType Directory -Force -Path $targetDir
}

# 复制 HRV Rust 加速计算的相关文件
$rustPkgPath = "..\venv\Lib\site-packages\ar_neurokit2_rust"
if (Test-Path $rustPkgPath) {
    Copy-Item -Path $rustPkgPath -Destination "$targetDir\ar_neurokit2_rust" -Recurse -Force
}

# 复制 HRV CUDA C++ 加速计算的相关文件
$cudaCppPydPath = "..\venv\Lib\site-packages\AR_neurokit2_cuda_fullscale.cp312-win_amd64.pyd"
if (Test-Path $cudaCppPydPath) {
    Copy-Item -Path $cudaCppPydPath -Destination "$targetDir\AR_neurokit2_cuda_fullscale.cp312-win_amd64.pyd" -Force
}

$cudaCppPkgPath = "..\venv\Lib\site-packages\cuda_cpp_fullscale"
if (Test-Path $cudaCppPkgPath) {
    Copy-Item -Path $cudaCppPkgPath -Destination "$targetDir\cuda_cpp_fullscale" -Recurse -Force
}

# 复制 numpy 相关文件
$numpyPath = "..\venv\Lib\site-packages\numpy"
if (Test-Path $numpyPath) {
    Copy-Item -Path $numpyPath -Destination "$targetDir\numpy" -Recurse -Force
}

Copy-Item -Path "..\venv\Lib\site-packages\mne" -Destination "$targetDir\mne" -Recurse -Force
Copy-Item -Path "..\venv\Lib\site-packages\lspopt" -Destination "$targetDir\lspopt" -Recurse -Force
Copy-Item -Path "..\venv\Lib\site-packages\lightgbm" -Destination "$targetDir\lightgbm" -Recurse -Force
Copy-Item -Path "QL1.ico" -Destination "$targetDir_icon" -Recurse -Force
Copy-Item -path "update.bat" -Destination "$targetDir_icon" -Recurse -Force
Copy-Item -path "config\" -Destination "$targetDir_icon" -Recurse -Force
Copy-Item -path "resource\" -Destination "$targetDir_icon" -Recurse -Force
Remove-Item -Path (Join-Path $targetDir_icon "resource\html_reports") -Recurse -Force -ErrorAction SilentlyContinue

# Copy XGBoost files
$xgboostPath = "..\venv\Lib\site-packages\xgboost"
if (Test-Path $xgboostPath) {
    Copy-Item -Path $xgboostPath -Destination "$targetDir\xgboost" -Recurse -Force
    
    # Create lib directory if it doesn't exist
    $libDir = "$targetDir\lib"
    if (!(Test-Path $libDir)) {
        New-Item -ItemType Directory -Force -Path $libDir
    }
    
    # Create bin directory if it doesn't exist
    $binDir = "$targetDir\bin"
    if (!(Test-Path $binDir)) {
        New-Item -ItemType Directory -Force -Path $binDir
    }
    
    # Copy XGBoost DLL to multiple locations to ensure it's found
    if (Test-Path "$xgboostPath\lib\xgboost.dll") {
        Copy-Item -Path "$xgboostPath\lib\xgboost.dll" -Destination "$libDir" -Force
        Copy-Item -Path "$xgboostPath\lib\xgboost.dll" -Destination "$binDir" -Force
    }
}

# 添加以下命令来复制 src/Qlass/models 目录
$modelsDir = "$targetDir\src\Qlass\models"
if (!(Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Force -Path $modelsDir
}
Copy-Item -Path ".\src\Qlass\models\2_LightGBM-1EEG.pkl" -Destination "$modelsDir" -Recurse -Force
Copy-Item -Path ".\src\Qlass\models\feature_order.csv" -Destination "$modelsDir" -Recurse -Force

# 复制癫痫检测新算法的模型文件
$newEpilepsyModelDir = "$targetDir\src\newEpilepsy" 
if (!(Test-Path $newEpilepsyModelDir)) {
    New-Item -ItemType Directory -Force -Path $newEpilepsyModelDir
}
Copy-Item -Path ".\src\newEpilepsy\*" -Destination "$newEpilepsyModelDir" -Recurse -Force

# qEEG算法的模型文件打包脚本（终极修复版，解决同名冲突+保留目录结构）
$qEEGDir = "$targetDir\src\qeeg_algorithm-main" 

# 1. 确保目标主目录存在，屏蔽冗余输出
if (!(Test-Path $qEEGDir)) {
    New-Item -ItemType Directory -Force -Path $qEEGDir | Out-Null
}

# 定义两个子目录的目标路径（规范路径拼接）
$eegNormsTarget = Join-Path -Path $qEEGDir -ChildPath "EEGnorms"
$qeegTarget = Join-Path -Path $qEEGDir -ChildPath "qeeg"

# 核心修复：复制前清理目标子目录（先删后建，彻底消除同名冲突）
# 清理EEGnorms目标子目录
if (Test-Path $eegNormsTarget) {
    # 删除现有子目录及所有内容，-Force强制删除，无提示
    Remove-Item -Path $eegNormsTarget -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $eegNormsTarget | Out-Null # 重建空目录

# 清理qeeg目标子目录（解决你当前的zscore、__pycache__冲突问题）
if (Test-Path $qeegTarget) {
    Remove-Item -Path $qeegTarget -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $qeegTarget | Out-Null # 重建空目录

# 2. 复制EEGnorms所有内容到目标子目录（无冲突，完整保留结构）
Copy-Item -Path ".\src\qeeg_algorithm-main\EEGnorms\*" -Destination $eegNormsTarget -Recurse -Force

# 3. 复制qeeg所有内容到目标子目录（彻底解决zscore、__pycache__同名冲突）
Copy-Item -Path ".\src\qeeg_algorithm-main\qeeg\*" -Destination $qeegTarget -Recurse -Force

