@echo off
chcp 65001 >nul
REM TestPilot PyInstaller Build Script

set "BUILD_MODE=%~1"
if "%BUILD_MODE%"=="" set "BUILD_MODE=full"
if /i "%BUILD_MODE%"=="slim" (
    set "TESTPILOT_BUILD_SLIM=1"
    echo [INFO] Build mode: slim ^(no vector store, smaller size^)
) else (
    set "TESTPILOT_BUILD_SLIM=0"
    if /i not "%BUILD_MODE%"=="full" (
        echo [WARNING] Unknown mode "%~1", using "full"
    )
    echo [INFO] Build mode: full ^(with sqlite-vec + FTS5^)
)

echo ========================================
echo TestPilot PyInstaller Build Script
echo ========================================
echo.

REM Check if running in virtual environment
python -c "import sys; sys.exit(0 if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else 1)"
if %errorlevel% neq 0 (
    echo [WARNING] Virtual environment not detected, recommend running in venv
    echo.
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not installed, installing...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERROR] PyInstaller installation failed
        pause
        exit /b 1
    )
)

echo [INFO] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist TestPilot.spec del /q TestPilot.spec

echo [INFO] Starting build...
echo.

REM Build using spec file (spec reads TESTPILOT_BUILD_SLIM for slim mode)
pyinstaller build.spec

if %errorlevel% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed!
echo ========================================
echo.
echo Executable location: dist\TestPilot.exe
echo.
if "%TESTPILOT_BUILD_SLIM%"=="1" (
    echo Notes ^(slim build^):
    echo 1. Set ENABLE_VECTOR_STORE=false in .env or environment before run
    echo 2. Knowledge base and RAG features will be disabled
    echo 3. Make sure .env file is configured before first run
) else (
    echo Notes:
    echo 1. Make sure .env file is configured before first run
    echo 2. Ensure target machine has necessary runtime libraries
    echo 3. Recommend packaging the entire dist directory for distribution
)
echo.
pause
