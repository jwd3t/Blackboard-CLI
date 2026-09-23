"""
Script para empaquetar de forma segura Blackboard CLI en un archivo ZIP limpio.
Excluye credenciales, cookies, entorno virtual y materiales privados.
"""
import sys
import zipfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import VERSION

BASE_DIR = Path(__file__).resolve().parent
ZIP_NAME = BASE_DIR / f"Blackboard-CLI-v{VERSION}.zip"
LEGACY_ZIP_NAME = BASE_DIR / "Blackboard-CLI.zip"

FILES_TO_INCLUDE = [
    "cli.py",
    "ultra_client.py",
    "organizer.py",
    "auth.py",
    "config.py",
    "requirements.txt",
    "run.bat",
    "package.py",
    "README.md",
    ".gitignore"
]

def create_package():
    print(f"[*] Empaquetando Blackboard CLI v{VERSION}...")
    if ZIP_NAME.exists():
        ZIP_NAME.unlink()
    if LEGACY_ZIP_NAME.exists():
        LEGACY_ZIP_NAME.unlink()

    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_name in FILES_TO_INCLUDE:
            p = BASE_DIR / file_name
            if p.exists():
                zipf.write(p, arcname=f"Blackboard-CLI-v{VERSION}/{file_name}")
                print(f"  + Incluido: {file_name}")
            else:
                print(f"  - No encontrado: {file_name}")

    # Crear copia con nombre estándar para compatibilidad
    import shutil
    shutil.copyfile(ZIP_NAME, LEGACY_ZIP_NAME)

    print(f"\n[✓] Paquete de versión listo: {ZIP_NAME.name}")
    print(f"[✓] Paquete genérico listo:   {LEGACY_ZIP_NAME.name}")
    print("[✓] Totalmente seguro: no contiene tus contraseñas, cookies ni archivos personales.")

if __name__ == "__main__":
    create_package()
