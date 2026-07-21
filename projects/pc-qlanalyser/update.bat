@echo off
setlocal enabledelayedexpansion

:: 检查参数数量是否为3
if "%~3"=="" (
    echo "参数非法，请勿手工执行，以免导致损坏文件影响程序正常运行。"
    pause
    exit /b 1
)


set "source_dir=%~f1"
set "target_dir=%~f2"
set "exe_file=%~f3"
set "exe_name=%~nx3"

if not exist "%source_dir%" (
    echo "Source directory does not exist: %source_dir%"
    pause
    exit /b 1
)


if not exist "%target_dir%" (
    echo "Target directory does not exist: %target_dir%"
    pause
    exit /b 1
)

if not exist "%exe_file%" (
    echo "Target file does not exist: %exe_file%"
    pause
    exit /b 1
)

:: 首先检查目标程序是否正在运行
echo Checking if program is still running...
timeout /t 2 /nobreak >nul

set "processFound=false"
for /f "tokens=1" %%a in ('tasklist /fi "imagename eq %exe_name%" 2^>nul ^| find /i "%exe_name%"') do (
    set "processFound=true"
)

if "!processFound!"=="true" (
    echo.
    echo ===================================================================================================
    echo WARNING: The program is still running. Please manually close the analyser program before upgrading.
    echo ===================================================================================================
    echo.
    
    :: 等待用户关闭程序
    :waitForClose
    echo Waiting for program to close... (Press Ctrl+C to cancel upgrade)
    timeout /t 5 /nobreak >nul
    
    set "processFound=false"
    for /f "tokens=1" %%a in ('tasklist /fi "imagename eq %exe_name%" 2^>nul ^| find /i "%exe_name%"') do (
        set "processFound=true"
    )
    
    if "!processFound!"=="true" (
        goto waitForClose
    )
    
    echo Program closed successfully.
    echo.
)


echo Starting upgrade preparation, please wait...
timeout /t 3 /nobreak


echo Copying files from "%source_dir%" to "%target_dir%"...
robocopy "%source_dir%" "%target_dir%" /B /E /z /r:10 /w:3

set resultcode=!ERRORLEVEL!

if !resultcode! GEQ 8 (
    echo [ERROR] Error occurred during copying, error code: !resultcode!
    pause
    exit /b 2
)

if exist "%source_dir%" (
    echo Deleting directory: "%source_dir%"
    rd /S /Q "%source_dir%"

    set resultcode=!ERRORLEVEL!

    if !resultcode! neq 0 (
        if exist "%source_dir%" (
            echo [ERROR] Failed to delete "%source_dir%" ^(but it won't affect the upgrade^), error code: !resultcode!
        ) else (
            echo [INFO] "%source_dir%" was partially deleted, code: !resultcode!
        )
    ) else (
        echo [SUCCESS] "%source_dir%" was successfully deleted.
    )
)

echo [SUCCESS]Upgrade completed successfully, starting program...
start "" "%exe_file%"
endlocal
pause
exit