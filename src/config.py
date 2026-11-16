"""
Configuraciones globales para Blackboard CLI (Multi-Universidad).
Compatible con Blackboard Learn Ultra de UPC, UCV, UPN y cualquier universidad.
"""
from __future__ import annotations

import os
import sys
import json
import urllib.parse
from pathlib import Path

# Versión del software
VERSION = "3.2.0"

# Repositorio y Actualizaciones
RELEASES_URL = "https://github.com/jwd3t/Blackboard-CLI/releases/"
API_LATEST_RELEASE = "https://api.github.com/repos/jwd3t/Blackboard-CLI/releases/latest"

# Rutas de almacenamiento local (la raíz del proyecto es el padre de src/)
BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_DIR = BASE_DIR / ".session_data"
ACTIVE_INSTITUTION_FILE = SESSION_DIR / "active_institution.json"
UPDATE_CACHE_FILE = SESSION_DIR / "update_check.json"
OUTPUT_DIR_CONFIG_FILE = SESSION_DIR / "output_dir.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "cuadernos"

# Instituciones preconfiguradas
DEFAULT_INSTITUTIONS: dict[str, dict] = {
    "upc": {
        "id": "upc",
        "name": "Universidad Peruana de Ciencias Aplicadas (UPC)",
        "short_name": "UPC",
        "base_url": "https://aulavirtual.upc.edu.pe",
        "domain": "aulavirtual.upc.edu.pe",
        "color": "bright_red",
    },
    "ucv": {
        "id": "ucv",
        "name": "Universidad César Vallejo (UCV)",
        "short_name": "UCV",
        "base_url": "https://ucv.blackboard.com",
        "domain": "ucv.blackboard.com",
        "color": "bright_blue",
    },
    "upn": {
        "id": "upn",
        "name": "Universidad Privada del Norte (UPN)",
        "short_name": "UPN",
        "base_url": "https://upn.blackboard.com",
        "domain": "upn.blackboard.com",
        "color": "bright_yellow",
    },
    "senati": {
        "id": "senati",
        "name": "Servicio Nacional de Adiestramiento en Trabajo Industrial (SENATI)",
        "short_name": "SENATI",
        "base_url": "https://senati.blackboard.com",
        "domain": "senati.blackboard.com",
        "color": "bright_blue",
    },
    "custom": {
        "id": "custom",
        "name": "Otra Universidad (URL Personalizada)",
        "short_name": "Personalizada",
        "base_url": "",
        "domain": "",
        "color": "bright_cyan",
    },
}


def normalize_url(url: str) -> str:
    """Normaliza y limpia la URL del aula virtual con soporte de atajos comunes."""
    clean = url.strip()
    if not clean:
        return ""

    clean_lower = clean.lower()
    # Atajos de instituciones conocidas
    if clean_lower in ["senati", "senati.pe", "senati.edu.pe", "aulavirtual.senati.edu.pe"]:
        return "https://senati.blackboard.com"
    if clean_lower in ["upc", "upc.edu.pe", "aulavirtual.upc.edu.pe"]:
        return "https://aulavirtual.upc.edu.pe"
    if clean_lower in ["ucv", "ucv.edu.pe", "ucv.blackboard.com"]:
        return "https://ucv.blackboard.com"
    if clean_lower in ["upn", "upn.edu.pe", "upn.blackboard.com"]:
        return "https://upn.blackboard.com"

    if not clean.startswith("http://") and not clean.startswith("https://"):
        clean = f"https://{clean}"
    return clean.rstrip("/")


def validate_blackboard_url(url: str, timeout: float = 6.0) -> tuple[bool, str]:
    """
    Verifica si una URL corresponde a una instancia activa de Blackboard Learn.
    Retorna (es_valido, descripcion_o_error).
    """
    import httpx
    norm = normalize_url(url)
    if not norm:
        return False, "URL vacía"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # 1. Probar endpoint oficial de versión de Blackboard Learn REST API
    try:
        r = httpx.get(
            f"{norm}/learn/api/public/v1/system/version",
            headers=headers,
            follow_redirects=True,
            timeout=timeout
        )
        if r.status_code == 200:
            try:
                data = r.json()
                if "learn" in data:
                    v = data["learn"]
                    return True, f"Blackboard Learn SaaS v{v.get('major', 4000)}.{v.get('minor', 0)}"
            except Exception:
                pass
    except Exception:
        pass

    # 2. Probar portada o endpoint ultra
    try:
        r2 = httpx.get(norm, headers=headers, follow_redirects=True, timeout=timeout)
        text_lower = r2.text.lower()
        if any(k in text_lower for k in ["blackboard", "ultra", "bb-login", "bb-navigation", "senati"]):
            return True, "Blackboard Learn Ultra detectado"
    except Exception as e:
        return False, f"No se pudo conectar a la URL: {e}"

    return False, "El servidor no parece ser una instancia de Blackboard Learn / Ultra"


def parse_version_tuple(v: str) -> tuple[int, ...]:
    """Convierte un string de versión (ej. 'v2.3.0') en tupla numérica (2, 3, 0) para comparar."""
    import re
    nums = re.findall(r"\d+", v)
    return tuple(int(x) for x in nums) if nums else (0,)


def check_for_updates(current_version: str = VERSION, cache_ttl: int = 1800) -> dict | None:
    """
    Consulta GitHub Releases para verificar si hay una nueva versión disponible.
    Utiliza caché local en .session_data/update_check.json para no saturar la API ni ralentizar la CLI.
    Retorna dict con datos de la nueva versión o None si está al día.
    """
    import time
    now = time.time()

    # 1. Leer caché si existe y no ha expirado
    if UPDATE_CACHE_FILE.exists():
        try:
            with open(UPDATE_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if now - data.get("checked_at", 0) < cache_ttl:
                remote_tag = data.get("tag_name", "")
                if parse_version_tuple(remote_tag) > parse_version_tuple(current_version):
                    return {
                        "latest_version": remote_tag,
                        "url": data.get("html_url") or RELEASES_URL,
                        "has_update": True
                    }
                return None
        except Exception:
            pass

    # 2. Consultar endpoint oficial de GitHub Releases
    try:
        import httpx
        r = httpx.get(
            API_LATEST_RELEASE,
            headers={"User-Agent": "Blackboard-CLI"},
            timeout=2.0
        )
        if r.status_code == 200:
            rel = r.json()
            remote_tag = rel.get("tag_name", "")
            html_url = rel.get("html_url", RELEASES_URL)
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            with open(UPDATE_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"checked_at": now, "tag_name": remote_tag, "html_url": html_url}, f)
            if parse_version_tuple(remote_tag) > parse_version_tuple(current_version):
                return {
                    "latest_version": remote_tag,
                    "url": html_url,
                    "has_update": True
                }
    except Exception:
        pass

    return None


def is_institution_configured() -> bool:
    """Retorna True si el usuario ya ha seleccionado y guardado una institución en disco."""
    if ACTIVE_INSTITUTION_FILE.exists():
        try:
            with open(ACTIVE_INSTITUTION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data and isinstance(data, dict) and data.get("base_url"))
        except Exception:
            return False
    return False


def get_active_institution() -> dict:
    """Retorna la configuración de la institución actualmente seleccionada."""
    if ACTIVE_INSTITUTION_FILE.exists():
        try:
            with open(ACTIVE_INSTITUTION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and "base_url" in data:
                    return data
        except Exception:
            pass
    return dict(DEFAULT_INSTITUTIONS["upc"])


def set_active_institution(inst_id: str, custom_url: str = "", custom_name: str = "") -> dict:
    """Cambia la institución activa y actualiza variables de entorno."""
    global BASE_URL, COOKIES_FILE, DOWNLOADS_CACHE_FILE

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    inst_key = inst_id.lower().strip()

    if inst_key in DEFAULT_INSTITUTIONS and inst_key != "custom":
        inst = dict(DEFAULT_INSTITUTIONS[inst_key])
    else:
        norm_url = normalize_url(custom_url)
        domain = urllib.parse.urlparse(norm_url).netloc
        short = custom_name.strip() or domain or "Personalizada"
        inst = {
            "id": "custom",
            "name": custom_name.strip() or f"Blackboard ({domain})",
            "short_name": short[:15],
            "base_url": norm_url,
            "domain": domain,
            "color": "bright_cyan"
        }

    with open(ACTIVE_INSTITUTION_FILE, "w", encoding="utf-8") as f:
        json.dump(inst, f, indent=2, ensure_ascii=False)

    # Actualizar variables dinámicas
    BASE_URL = inst["base_url"]
    COOKIES_FILE = get_cookies_file()
    DOWNLOADS_CACHE_FILE = get_downloads_cache_file()

    return inst


def get_base_url() -> str:
    """Retorna la URL base activa."""
    return get_active_institution().get("base_url", DEFAULT_INSTITUTIONS["upc"]["base_url"])


def get_cookies_file() -> Path:
    """Retorna la ruta del archivo de cookies de la institución activa (aislado por universidad)."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    inst = get_active_institution()
    inst_id = inst.get("id", "upc")

    if inst_id == "upc":
        # Retrocompatibilidad con v2.x
        legacy_file = SESSION_DIR / "cookies.json"
        inst_file = SESSION_DIR / "cookies_upc.json"
        if not inst_file.exists() and legacy_file.exists():
            return legacy_file
        return inst_file

    return SESSION_DIR / f"cookies_{inst_id}.json"


def get_downloads_cache_file() -> Path:
    """Retorna la ruta del archivo de caché de descargas de la institución activa."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    inst = get_active_institution()
    inst_id = inst.get("id", "upc")

    if inst_id == "upc":
        # Retrocompatibilidad con v2.x
        legacy_file = SESSION_DIR / "downloads_cache.json"
        inst_file = SESSION_DIR / "downloads_cache_upc.json"
        if not inst_file.exists() and legacy_file.exists():
            return legacy_file
        return inst_file

    return SESSION_DIR / f"downloads_cache_{inst_id}.json"


def get_browser_session_dir() -> Path:
    """Retorna la carpeta persistente del navegador de Playwright para la institución activa."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    inst = get_active_institution()
    inst_id = inst.get("id", "upc")
    return SESSION_DIR / f"browser_{inst_id}"


def open_in_file_manager(path: Path) -> bool:
    """Abre una ruta (carpeta o archivo) en el explorador de archivos nativo del sistema operativo."""
    import subprocess
    try:
        path = path.resolve()
        if path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(path))
            return True
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
            return True
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
            return True
    except Exception:
        return False


def clean_user_path(raw: str) -> str:
    """Limpia rutas pegadas o arrastradas a la terminal (comillas simples/dobles, '& ' de PowerShell)."""
    s = (raw or "").strip()
    if s.startswith("& "):
        s = s[2:].strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1].strip()
    return s


def get_desktop_dir() -> Path:
    """Detecta la ruta real del Escritorio del usuario (incluyendo redirecciones de OneDrive en Windows)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            CSIDL_DESKTOPDIRECTORY = 0x0010
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf) == 0:
                p = Path(buf.value)
                if p.exists():
                    return p
        except Exception:
            pass
        for cand in [
            Path.home() / "OneDrive" / "Desktop",
            Path.home() / "OneDrive" / "Escritorio",
            Path.home() / "Desktop",
            Path.home() / "Escritorio",
        ]:
            if cand.exists():
                return cand
        return Path.home() / "Desktop"

    for cand in [Path.home() / "Desktop", Path.home() / "Escritorio"]:
        if cand.exists():
            return cand
    return Path.home()


def get_output_dir() -> Path:
    """Retorna la carpeta configurada para guardar los cuadernos (o la ruta por defecto)."""
    if OUTPUT_DIR_CONFIG_FILE.exists():
        try:
            with open(OUTPUT_DIR_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            custom = str(data.get("output_dir", "")).strip()
            if custom:
                return Path(custom)
        except Exception:
            pass
    return DEFAULT_OUTPUT_DIR


def set_output_dir(new_path: str | Path | None = None, create_dir: bool = True) -> Path:
    """Guarda una ubicación personalizada para los cuadernos o restaura la ruta por defecto."""
    global OUTPUT_DIR

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    if new_path is None or str(new_path).strip().lower() in ("", "default", "defecto"):
        if OUTPUT_DIR_CONFIG_FILE.exists():
            try:
                OUTPUT_DIR_CONFIG_FILE.unlink()
            except Exception:
                pass
        OUTPUT_DIR = DEFAULT_OUTPUT_DIR
        if create_dir:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return OUTPUT_DIR

    cleaned = clean_user_path(str(new_path)) if isinstance(new_path, str) else str(new_path)
    target = Path(cleaned).expanduser().resolve()
    if create_dir:
        target.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"output_dir": str(target)}, f, indent=2, ensure_ascii=False)

    OUTPUT_DIR = target
    return target


def pick_folder_dialog(initial_dir: Path | None = None) -> Path | None:
    """Abre el selector nativo de carpetas del sistema operativo (tkinter)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
            root.update()
        except Exception:
            pass
        start_dir = str(initial_dir) if initial_dir and initial_dir.exists() else str(get_desktop_dir())
        chosen = filedialog.askdirectory(
            parent=root,
            title="Selecciona la carpeta donde guardar o actualizar tus cuadernos",
            initialdir=start_dir,
        )
        root.destroy()
        if chosen:
            return Path(chosen).resolve()
    except Exception:
        pass
    return None


def detect_course_folders(folder: Path) -> list[Path]:
    """Detecta carpetas de cursos existentes dentro de una ruta dada."""
    if not folder or not folder.exists() or not folder.is_dir():
        return []
    found = []
    try:
        for item in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if not item.is_dir() or item.name.startswith("."):
                continue
            if (
                item.name.startswith("[")
                or (item / "CUADERNO_CURSO.md").exists()
                or (item / DIR_MATERIALES).exists()
                or (item / DIR_INFO_GENERAL).exists()
            ):
                found.append(item)
    except Exception:
        pass
    return found


# Inicialización de variables para compatibilidad directa
_current_inst = get_active_institution()
BASE_URL = _current_inst.get("base_url", DEFAULT_INSTITUTIONS["upc"]["base_url"])
COOKIES_FILE = get_cookies_file()
DOWNLOADS_CACHE_FILE = get_downloads_cache_file()
OUTPUT_DIR = get_output_dir()

# Estructura del cuaderno por curso
DIR_INFO_GENERAL = "00_INFORMACION_GENERAL"
DIR_EVALUACIONES = "01_EVALUACIONES_Y_EXAMENES"
DIR_MATERIALES = "02_MATERIALES_Y_CLASES"
DIR_ANUNCIOS = "03_ANUNCIOS"
DIR_GEMINI_NOTEBOOK = "gemini_notebook"  # Carpeta plana unificada para Gemini Notebook / NotebookLM

# Palabras clave para clasificar automáticamente archivos en 00_INFORMACION_GENERAL
KEYWORDS_INFO_GENERAL = [
    "silabo", "sílabo", "syllabus",
    "plan calendario", "calendario", "cronograma",
    "guia del estudiante", "guía del estudiante",
    "reglamento", "presentacion del curso", "presentación del curso",
    "formula", "fórmula de evaluacion", "evaluaciones del curso"
]

# Extensiones de archivos de interés para descarga
SUPPORTED_EXTENSIONS = {
    ".pdf", ".pptx", ".ppt", ".docx", ".doc",
    ".xlsx", ".xls", ".zip", ".rar", ".txt", ".csv", ".md"
}

# Extensiones de documentos convertibles a Markdown vía AnyDoc
ANYDOC_SUPPORTED_EXTENSIONS = {
    ".pdf", ".pptx", ".ppt", ".docx", ".doc",
    ".xlsx", ".xls", ".csv", ".rtf", ".epub",
    ".odt", ".ods", ".odp"
}
