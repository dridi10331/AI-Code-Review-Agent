@echo off
echo ============================================================
echo AI Code Review Agent - Quick Start
echo ============================================================
echo.

echo [1/4] Starting Docker services...
docker-compose up -d postgres redis
if %errorlevel% neq 0 (
    echo ERROR: Failed to start Docker services
    echo Make sure Docker Desktop is running
    pause
    exit /b 1
)
echo SUCCESS: Docker services started
echo.

echo [2/4] Waiting for services to be ready...
timeout /t 5 /nobreak >nul
echo.

echo [3/4] Starting FastAPI backend...
start "AI Review API" cmd /k "python -m uvicorn backend.app.main:app --reload --port 8000"
echo SUCCESS: API starting on http://localhost:8000
echo.

echo [4/4] Starting Streamlit dashboard...
timeout /t 3 /nobreak >nul
start "AI Review Dashboard" cmd /k "python -m streamlit run dashboard/app.py --server.port 8501"
echo SUCCESS: Dashboard starting on http://localhost:8501
echo.

echo ============================================================
echo All services started!
echo ============================================================
echo.
echo API:       http://localhost:8000
echo Docs:      http://localhost:8000/docs
echo Dashboard: http://localhost:8501
echo.
echo Press any key to open dashboard in browser...
pause >nul

start http://localhost:8501

echo.
echo Services are running in separate windows.
echo Close those windows to stop the services.
echo.
pause
