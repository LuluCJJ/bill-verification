@echo off
chcp 65001 >nul

echo =================================================
echo    Bill Verification Demo Launcher
echo =================================================

echo [Status] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python 3.10+ first.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [Status] Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [Error] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [Status] Syncing backend dependencies into .venv...
.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [Error] Failed to install backend dependencies.
    pause
    exit /b 1
)

echo [Status] Starting backend service...
if exist "demo\backend\app\main.py" (
    start "BillVerificationBackend" cmd /c ".venv\Scripts\python.exe -m uvicorn demo.backend.app.main:app --host 127.0.0.1 --port 8000 --reload"
) else (
    echo [Info] Backend code is not created yet. Use this launcher after demo backend scaffolding is ready.
)

echo =================================================
echo    READY
echo =================================================
pause

