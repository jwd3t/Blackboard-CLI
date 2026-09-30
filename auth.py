"""
Módulo de autenticación y manejo de sesión para Blackboard Ultra Multi-Universidad.
Utiliza Playwright con un perfil persistente por institución para permitir inicio de sesión SSO/2FA
y extrae las cookies de sesión para consultas API rápidas.
"""
from __future__ import annotations

import sys
import json
import time
import urllib.parse
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import (
    get_base_url,
    get_cookies_file,
    get_browser_session_dir,
    get_active_institution,
    SESSION_DIR,
)


def extract_cookies_for_domain(cookies_list: list[dict], target_url: str) -> dict[str, str]:
    """
    Filtra y prioriza cookies para la URL de destino de Blackboard:
    1. Acepta cookies de dominio padre (.blackboard.com).
    2. Da máxima prioridad a cookies de dominio exacto (ej: senati.blackboard.com o aulavirtual.upc.edu.pe).
    3. Descarta cookies de otros subdominios (ej: alt-*.blackboard.com) o servicios externos (Microsoft/Google).
    """
    domain = urllib.parse.urlparse(target_url).netloc.lower()
    matched = {}

    # 1. Cookies de dominio padre (.blackboard.com)
    for c in cookies_list:
        c_dom = c.get("domain", "").lstrip(".").lower()
        if c_dom and domain.endswith(c_dom) and c_dom != domain:
            matched[c["name"]] = c["value"]

    # 2. Cookies de dominio exacto (ej: senati.blackboard.com) - sobrescriben con máxima prioridad
    for c in cookies_list:
        c_dom = c.get("domain", "").lstrip(".").lower()
        if c_dom == domain:
            matched[c["name"]] = c["value"]

    # 3. Si no hubo coincidencia estricta (ej: IP o dominio local), incluir cookies sin dominio
    if not matched:
        for c in cookies_list:
            if not c.get("domain"):
                matched[c["name"]] = c["value"]

    return matched


def get_stored_cookies(cookies_file: Path | None = None, base_url: str | None = None) -> dict[str, str] | None:
    """Lee y filtra las cookies almacenadas en disco para la institución activa."""
    target_file = cookies_file or get_cookies_file()
    if not target_file.exists():
        return None
    target_base = base_url or get_base_url()
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return extract_cookies_for_domain(data, target_base)
            elif isinstance(data, dict):
                return data
    except Exception:
        return None
    return None


def verify_session(
    cookies: dict[str, str] | None = None,
    base_url: str | None = None,
    debug: bool = False
) -> dict | None:
    """
    Verifica si la sesión actual sigue siendo válida contra la API de Blackboard.
    Retorna los datos del usuario si es válida, o None si expiró.
    """
    target_base = base_url or get_base_url()
    if cookies is None:
        cookies = get_stored_cookies(base_url=target_base)
    if not cookies:
        return None

    try:
        url = f"{target_base}/learn/api/public/v1/users/me"
        xsrf = cookies.get("XSRF-TOKEN", "")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": f"{target_base}/ultra",
        }
        if xsrf:
            headers["X-Blackboard-XSRF"] = xsrf
            headers["X-XSRF-TOKEN"] = xsrf

        resp = httpx.get(
            url,
            cookies=cookies,
            headers=headers,
            follow_redirects=True,
            timeout=10.0
        )
        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                pass
        elif debug:
            print(f"[debug] verify_session status: {resp.status_code}, body: {resp.text[:150]}")
    except Exception as e:
        if debug:
            print(f"[debug] verify_session error: {e}")
    return None


def _launch_browser_context(playwright_instance, target_browser_dir: Path):
    """
    Inicia un contexto de navegador persistente con fallback progresivo:
    1. Chromium oficial de Playwright.
    2. Microsoft Edge del sistema (canal 'msedge', preinstalado en el 100% de PCs con Windows).
    3. Google Chrome del sistema (canal 'chrome').
    4. Búsqueda directa de ejecutables conocidos en Windows.
    Retorna (context, browser_name) o (None, None).
    """
    abs_dir = str(target_browser_dir.resolve())
    base_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    candidates = [
        ("Chromium (Playwright)", {"args": base_args}),
        ("Microsoft Edge (Sistema)", {"channel": "msedge", "args": base_args}),
        ("Google Chrome (Sistema)", {"channel": "chrome", "args": base_args}),
    ]

    if sys.platform == "win32":
        # Rutas físicas por si el canal de Playwright no resuelve en la instalación local
        system_paths = [
            ("Microsoft Edge (Ruta)", Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")),
            ("Microsoft Edge (Ruta)", Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe")),
            ("Google Chrome (Ruta)", Path("C:/Program Files/Google/Chrome/Application/chrome.exe")),
            ("Google Chrome (Ruta)", Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe")),
        ]
        for name, p in system_paths:
            if p.exists():
                candidates.append((name, {"executable_path": str(p), "args": base_args}))

    errors = []
    for name, kwargs in candidates:
        try:
            ctx = playwright_instance.chromium.launch_persistent_context(
                user_data_dir=abs_dir,
                headless=False,
                viewport={"width": 1280, "height": 800},
                **kwargs
            )
            return ctx, name
        except Exception as e:
            err_line = str(e).splitlines()[0] if str(e) else "Error desconocido"
            errors.append((name, err_line))

    print("\n[✖] Error: No se pudo abrir ninguna instancia de navegador.")
    print("    Detalles de los intentos:")
    for name, err in errors:
        print(f"    - {name}: {err[:100]}")
    print("\n    Sugerencias:")
    print("    1. Comprueba si tu antivirus o Windows Defender bloqueó la ejecución de Chromium.")
    print("    2. Asegúrate de tener Microsoft Edge o Google Chrome instalados en tu sistema.")
    print("    3. Intenta reinstalar Chromium ejecutando: python -m playwright install chromium")
    return None, None


def interactive_login(
    timeout_seconds: int = 180,
    base_url: str | None = None,
    cookies_file: Path | None = None,
    session_dir: Path | None = None
) -> bool:
    """
    Abre una ventana de navegador para que el estudiante inicie sesión
    con sus credenciales institucionales y confirme el 2FA si corresponde.
    Guarda las cookies una vez completado el acceso.
    """
    target_base = base_url or get_base_url()
    target_cookies = cookies_file or get_cookies_file()
    target_browser_dir = session_dir or get_browser_session_dir()
    inst = get_active_institution()
    inst_name = inst.get("name", "Blackboard Ultra")
    domain = urllib.parse.urlparse(target_base).netloc.lower()

    target_browser_dir.mkdir(parents=True, exist_ok=True)
    target_cookies.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[!] Abriendo navegador para inicio de sesión en Blackboard Ultra ({inst_name})...")
    print(f"[*] Servidor: {target_base}")
    print("[!] Por favor ingresa tus credenciales institucionales y confirma el 2FA si te lo solicita.")

    with sync_playwright() as p:
        context, b_name = _launch_browser_context(p, target_browser_dir)
        if not context:
            return False

        print(f"[✓] Navegador iniciado ({b_name})")

        try:
            page = context.new_page() if not context.pages else context.pages[0]
            page.goto(target_base)
        except Exception as e:
            print(f"[!] Nota al cargar página inicial: {e}")

        print("[*] Esperando a que completes el inicio de sesión en el navegador...")
        print("[*] (Si ya ves tu aula virtual en la pantalla, puedes presionar ENTER en esta consola para continuar)\n")

        import threading

        user_pressed_enter = False

        def wait_for_enter():
            nonlocal user_pressed_enter
            try:
                input()
                user_pressed_enter = True
            except Exception:
                pass

        enter_thread = threading.Thread(target=wait_for_enter, daemon=True)
        enter_thread.start()

        start_time = time.time()
        logged_in = False
        user_info = None

        try:
            while time.time() - start_time < timeout_seconds:
                # 1. Si el usuario presionó ENTER manualmente
                if user_pressed_enter:
                    print("\n[i] Capturando sesión a solicitud del usuario...")
                    raw_cookies = context.cookies()
                    cookie_dict = extract_cookies_for_domain(raw_cookies, target_base)
                    user_info = verify_session(cookie_dict, base_url=target_base)
                    logged_in = True
                    break

                # 2. Revisar si la ventana sigue abierta
                try:
                    pages = context.pages
                    if not pages:
                        print("\n[!] Se cerró la ventana del navegador.")
                        break
                except Exception:
                    print("\n[!] Se cerró la ventana del navegador.")
                    break

                # 3. Validar activamente las cookies actuales contra la API de Blackboard
                # Esta es la comprobación más confiable: sólo confirma si la API responde 200 OK con el usuario
                try:
                    raw_cookies = context.cookies()
                    cookie_dict = extract_cookies_for_domain(raw_cookies, target_base)
                    if "BbRouter" in cookie_dict or "XSRF-TOKEN" in cookie_dict:
                        user_info = verify_session(cookie_dict, base_url=target_base)
                        if user_info:
                            user_name = (
                                f"{user_info.get('name', {}).get('given', '')} {user_info.get('name', {}).get('family', '')}".strip()
                                or user_info.get("userName")
                                or "Estudiante"
                            )
                            print(f"\n[✓] ¡Sesión API validada exitosamente para {user_name}!")
                            logged_in = True
                            break
                except Exception:
                    pass

                # 4. Comprobar si el navegador ya llegó a una URL definitiva de Ultra (Cursos, Institución, etc.)
                all_urls = [page_item.url for page_item in pages]
                for u in all_urls:
                    u_lower = u.lower()
                    if (domain and domain in u_lower) or "blackboard" in u_lower or "senati" in u_lower or "aulavirtual" in u_lower:
                        if any(path in u_lower for path in ["/ultra/course", "/ultra/institution-page", "/ultra/stream", "tab_tab_group_id"]):
                            if "login" not in u_lower and "microsoft" not in u_lower and "auth" not in u_lower:
                                raw_cookies = context.cookies()
                                cookie_dict = extract_cookies_for_domain(raw_cookies, target_base)
                                user_info = verify_session(cookie_dict, base_url=target_base)
                                if user_info:
                                    user_name = (
                                        f"{user_info.get('name', {}).get('given', '')} {user_info.get('name', {}).get('family', '')}".strip()
                                        or user_info.get("userName")
                                        or "Estudiante"
                                    )
                                    print(f"\n[✓] ¡Inicio de sesión confirmado para {user_name} en: {u}!")
                                    logged_in = True
                                    break
                if logged_in:
                    break

                time.sleep(1.5)

            if not logged_in:
                print("\n[X] El tiempo de espera para iniciar sesión ha expirado o se cerró el navegador.")
                return False

            # Esperar 2 segundos para asegurar sincronización de cookies
            time.sleep(2)
            try:
                cookies = context.cookies()
                with open(target_cookies, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, indent=2)
                print(f"[✓] Credenciales y sesión guardadas con éxito en {target_cookies.name}")
                return True
            except Exception as e:
                print(f"[!] Error al guardar cookies: {e}")
                return False

        finally:
            try:
                context.close()
            except Exception:
                pass


def logout(cookies_file: Path | None = None, session_dir: Path | None = None) -> bool:
    """Elimina la sesión y cookies de la institución activa de forma segura."""
    import shutil
    target_cookies = cookies_file or get_cookies_file()
    target_browser = session_dir or get_browser_session_dir()
    try:
        if target_cookies.exists():
            target_cookies.unlink()
        if target_browser.exists():
            shutil.rmtree(target_browser, ignore_errors=True)
        return True
    except Exception as e:
        print(f"Error al cerrar sesión: {e}")
        return False
