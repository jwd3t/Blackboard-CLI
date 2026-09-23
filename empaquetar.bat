@echo off
chcp 65001 > nul
echo ======================================================
echo    Empaquetador de Blackboard CLI
echo ======================================================
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe package.py
) else (
    python package.py
)

echo.
pause
