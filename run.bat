@echo off
setlocal enabledelayedexpansion

set "PY_CMD="

:: 1. Probar py -3
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :run
)

:: 2. Probar python en PATH
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :run
)

:: 3. Buscar en rutas habituales de Windows (pythoncore, Programs, ProgramFiles, etc.)
for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-*") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD="%%~D\python.exe""
            goto :run
        )
    )
)

if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    "%LOCALAPPDATA%\Python\bin\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD="%LOCALAPPDATA%\Python\bin\python.exe""
        goto :run
    )
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD="%%~D\python.exe""
            goto :run
        )
    )
)

for /d %%D in ("%ProgramFiles%\Python*") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD="%%~D\python.exe""
            goto :run
        )
    )
)

for /d %%D in ("%ProgramFiles(x86)%\Python*") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD="%%~D\python.exe""
            goto :run
        )
    )
)

for /d %%D in ("C:\Python*") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD="%%~D\python.exe""
            goto :run
        )
    )
)

for /d %%D in ("%USERPROFILE%\anaconda3", "%USERPROFILE%\miniconda3") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD="%%~D\python.exe""
            goto :run
        )
    )
)

:run
if "%PY_CMD%"=="" goto :not_found

if exist ".venv\Scripts\python.exe" goto :execute_venv

echo [*] Configurando entorno virtual aislado (.venv)...
echo [*] Esto se realiza solo una vez y no dejara residuos en tu sistema.
echo.

%PY_CMD% -m venv .venv
if errorlevel 1 (
    echo [!] No se pudo crear el entorno virtual automaticamente.
    echo [!] Ejecutando con el Python del sistema...
    %PY_CMD% cli.py %*
    goto :finish
)

echo [*] Instalando librerias necesarias en .venv...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [X] Error al instalar las dependencias en .venv.
    pause
    goto :eof
)

echo [*] Preparando navegador para inicio de sesion (Playwright)...
".venv\Scripts\python.exe" -m playwright install chromium

echo.
echo [v] Entorno virtual listo. Iniciando Blackboard CLI...
echo.

:execute_venv
".venv\Scripts\python.exe" cli.py %*

:finish
if errorlevel 1 (
    echo.
    pause
)
goto :eof

:not_found

echo.
echo ========================================================
echo   Blackboard CLI - Error al iniciar Python
echo ========================================================
echo.
echo Windows no pudo ejecutar Python automaticamente.
echo.
echo MOTIVO MAS FRECUENTE EN WINDOWS 10/11:
echo   Los "Alias de ejecucion de aplicaciones" de Microsoft Store
echo   estan interceptando el comando python.
echo.
echo PASOS PARA SOLUCIONARLO EN 1 MINUTO:
echo   1. Abre el menu Inicio y escribe:
echo      "Alias de ejecucion de aplicaciones"
echo   2. Desactiva (OFF) los dos interruptores que dicen:
echo      - Instalador de la aplicacion de Python (python.exe)
echo      - Instalador de la aplicacion de Python (python3.exe)
echo   3. Vuelve a hacer doble clic en run.bat
echo.
echo Si aun no lo tienes instalado, descargalo desde:
echo   https://www.python.org/downloads/
echo   (Asegurate de marcar la casilla "Add python.exe to PATH")
echo.
pause
