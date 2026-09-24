#!/usr/bin/env bash
# ==============================================================================
# Blackboard CLI (UPC) - Script de inicio para macOS y Linux
# ==============================================================================

set -e

# Asegurar que el script se ejecute siempre desde la raíz del proyecto
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 1. Buscar un intérprete de Python 3 adecuado
PY_CMD=""

# Prioridad 1: Versiones de Python 3.10+ (Homebrew, oficiales, pyenv)
for candidate in python3.13 python3.12 python3.11 python3.10 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
            PY_CMD="$candidate"
            break
        fi
    fi
done

# Prioridad 2: Cualquier python3 o python disponible (mínimo Python 3.9)
if [ -z "$PY_CMD" ]; then
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
                PY_CMD="$candidate"
                break
            fi
        fi
    done
fi

# Si no se encuentra ningún Python compatible
if [ -z "$PY_CMD" ]; then
    echo ""
    echo "========================================================"
    echo "  Blackboard CLI - Error al iniciar Python en macOS"
    echo "========================================================"
    echo ""
    echo "No se encontró una instalación compatible de Python 3 en tu Mac."
    echo ""
    echo "CÓMO INSTALARLO EN 1 MINUTO:"
    echo "  Opción 1: Con Homebrew (recomendada):"
    echo "    brew install python"
    echo ""
    echo "  Opción 2: Descargador oficial de Python:"
    echo "    https://www.python.org/downloads/macos/"
    echo ""
    exit 1
fi

VENV_DIR="$DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"

# Verificar si existe una carpeta .venv incompatible (creada en Windows)
if [ -d "$VENV_DIR" ] && [ ! -f "$VENV_PY" ]; then
    echo "[!] Se detectó una carpeta .venv incompatible (posiblemente creada en Windows)."
    echo "[*] Recreando el entorno virtual para macOS..."
    rm -rf "$VENV_DIR"
fi

# 2. Si el entorno virtual ya existe y está configurado, ejecutar directamente
if [ -f "$VENV_PY" ]; then
    exec "$VENV_PY" "$DIR/cli.py" "$@"
fi

# 3. Crear entorno virtual (.venv) por primera vez
echo "[*] Configurando entorno virtual aislado (.venv)..."
echo "[*] Esto se realiza solo una vez y no dejará residuos en tu sistema."
echo ""

if ! "$PY_CMD" -m venv "$VENV_DIR"; then
    echo "[!] No se pudo crear el entorno virtual automáticamente con $PY_CMD."
    echo "[!] Intentando ejecutar directamente con el Python del sistema..."
    exec "$PY_CMD" "$DIR/cli.py" "$@"
fi

# 4. Instalar librerías requeridas en .venv
echo "[*] Instalando dependencias en .venv..."
"$VENV_PY" -m pip install --upgrade pip >/dev/null 2>&1 || true

if ! "$VENV_PY" -m pip install -r "$DIR/requirements.txt"; then
    echo "[X] Error al instalar las dependencias en .venv."
    exit 1
fi

# 5. Instalar navegador para inicio de sesión (Playwright Chromium)
echo "[*] Preparando navegador para inicio de sesión (Playwright Chromium)..."
"$VENV_PY" -m playwright install chromium || {
    echo "[!] Advertencia: Playwright no pudo descargar Chromium automáticamente."
    echo "[!] Si falla el login, ejecuta: $VENV_PY -m playwright install chromium"
}

echo ""
echo "[✓] Entorno virtual listo. Iniciando Blackboard CLI..."
echo ""

# 6. Iniciar la aplicación
exec "$VENV_PY" "$DIR/cli.py" "$@"
