@echo off
echo ============================================================
echo AI Code Review Agent - Stopping Services
echo ============================================================
echo.

echo [1/2] Stopping Docker services...
docker-compose down
echo SUCCESS: Docker services stopped
echo.

echo [2/2] Stopping Python processes...
echo Please close the API and Dashboard windows manually
echo (Look for "AI Review API" and "AI Review Dashboard" windows)
echo.

echo ============================================================
echo Services stopped!
echo ============================================================
echo.
pause
