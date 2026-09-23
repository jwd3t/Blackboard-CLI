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

BASE_DIR = Path(__file__).resolve().parent
ZIP_NAME = BASE_DIR / "Blackboard-CLI.zip"

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
    print("[*] Empaquetando Blackboard CLI...")
    if ZIP_NAME.exists():
        ZIP_NAME.unlink()

    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_name in FILES_TO_INCLUDE:
            p = BASE_DIR / file_name
            if p.exists():
                zipf.write(p, arcname=f"Blackboard-CLI/{file_name}")
                print(f"  + Incluido: {file_name}")
            else:
                print(f"  - No encontrado: {file_name}")

    print(f"\n[✓] Paquete listo para compartir: {ZIP_NAME}")
    print("[✓] Totalmente seguro: no contiene tus contraseñas, cookies ni archivos personales.")

if __name__ == "__main__":
    create_package()
