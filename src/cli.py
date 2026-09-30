"""
Blackboard CLI (UPC) - Asistente de Aula Virtual y Cuadernos de Estudio para IA.
Diseñado con una interfaz moderna inspirada en CLI de agentes de IA (Claude Code, Antigravity).
"""
from __future__ import annotations

import sys
import subprocess
import time
from pathlib import Path

# Asegurar que el directorio de src/ esté en sys.path para importaciones entre módulos
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Asegurar codificación UTF-8 en consola de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def auto_setup():
    """Instala automáticamente dependencias y navegador si faltan."""
    try:
        import rich
        import httpx
        import playwright
        import bs4
        import html2text
        import pypdf
        import dateutil
    except ImportError:
        print("[!] Instalando librerias requeridas de Blackboard CLI...")
        req_file = _SRC_DIR / "requirements.txt"
        if not req_file.exists():
            req_file = _SRC_DIR.parent / "requirements.txt"
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            if not Path(p.chromium.executable_path).exists():
                raise FileNotFoundError()
    except Exception:
        print("[!] Descargando navegador Chromium para Playwright...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


auto_setup()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, InvalidResponse, Confirm as _RichConfirm
from rich import box

class SpanishConfirm(_RichConfirm):
    """Confirmación interactiva estandarizada en español [s/n]."""
    choices = ["s", "n"]
    validate_error_message = "[prompt.invalid]Por favor ingresa 's' para sí o 'n' para no"

    def render_default(self, default) -> Text:
        return Text("(s)" if default else "(n)", style="prompt.default")

    def process_response(self, value: str) -> bool:
        val = value.strip().lower()
        if val in ["s", "si", "sí", "y", "yes"]:
            return True
        elif val in ["n", "no"]:
            return False
        raise InvalidResponse(self.validate_error_message)

Confirm = SpanishConfirm
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn
)

console = Console(force_terminal=True, color_system="truecolor")

from config import (
    BASE_URL,
    OUTPUT_DIR,
    VERSION,
    RELEASES_URL,
    get_base_url,
    get_active_institution,
    set_active_institution,
    is_institution_configured,
    check_for_updates,
    DEFAULT_INSTITUTIONS,
    validate_blackboard_url,
    normalize_url,
    open_in_file_manager,
)
from terminal_ui import hybrid_select, get_random_tip
from auth import verify_session, interactive_login, logout
from ultra_client import UltraClient
from organizer import CourseNotebookOrganizer, format_date, generate_gemini_notebook

TEXT_FULL = r"""[bold bright_cyan]
 ██████╗ ██╗      █████╗  ██████╗██╗  ██╗██████╗  ██████╗  █████╗ ██████╗ ██████╗
 ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗██╔══██╗██╔══██╗██╔══██╗
 ██████╔╝██║     ███████║██║     █████╔╝ ██████╔╝██║   ██║███████║██████╔╝██║  ██║
 ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██╔══██╗██║   ██║██╔══██║██╔══██╗██║  ██║
 ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
 ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝[/bold bright_cyan]
[bold white]                                             C  L  I[/bold white]"""

TEXT_COMPACT = r"""[bold bright_cyan]
 ██████╗ ██████╗        ██████╗██╗     ██╗
 ██╔══██╗██╔══██╗      ██╔════╝██║     ██║
 ██████╔╝██████╔╝█████╗██║     ██║     ██║
 ██╔══██╗██╔══██╗╚════╝██║     ██║     ██║
 ██████╔╝██████╔╝      ╚██████╗███████╗██║
 ╚═════╝ ╚═════╝        ╚═════╝╚══════╝╚═╝[/bold bright_cyan]"""

def _get_terminal_width() -> int:
    """Obtiene el ancho de la terminal de forma segura."""
    try:
        return console.width
    except Exception:
        return 80


def generate_gradient_logo():
    MASK = [
        "                      ",
        "          ██          ",
        "         ████         ",
        "        ██  ██        ",
        "       ██    ██       ",
        "      ██      ██      ",
        "     ██        ██     ",
        "    ██          ██    ",
        "   ██            ██   ",
        "                      ",
    ]
    logo = Text()
    for y, row in enumerate(MASK):
        for x, char in enumerate(row):
            factor = (x / len(row) + (len(MASK) - y) / len(MASK)) / 2
            r = int(0 + (165 - 0) * factor)
            g = int(77 + (255 - 77) * factor)
            b = int(230 + (0 - 230) * factor)
            fg_color = f"#{r:02x}{g:02x}{b:02x}"
            
            # Un solo carácter de bloque para un aspecto cuadrado
            if char == "█":
                logo.append("█", style="white")
            else:
                logo.append("█", style=fg_color)
        if y < len(MASK) - 1:
            logo.append("\n")
    return logo

def print_header(user: dict | None = None):
    """Muestra el banner profesional con ASCII art estilo AI CLI."""
    console.clear()

    width = _get_terminal_width()
    use_full_logo = width >= 115

    logo_text = generate_gradient_logo()
    
    if use_full_logo:
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Logo", justify="right", no_wrap=True)
        table.add_column("Text", vertical="middle", no_wrap=True)
        table.add_row(logo_text, TEXT_FULL)
        console.print(table)
    else:
        # Terminal estrecha: apilar el logo y el nombre completo, forzando no_wrap para evitar ruptura de ASCII
        logo_text.justify = "center"
        console.print(logo_text)
        
        fallback_table = Table(box=None, show_header=False, padding=(0, 0))
        fallback_table.add_column("Text", justify="center", no_wrap=True)
        fallback_table.add_row(TEXT_FULL)
        console.print(fallback_table, justify="center")

    inst_configured = is_institution_configured()
    if inst_configured:
        inst = get_active_institution()
        short_name = inst.get("short_name", "Blackboard")
        inst_color = inst.get("color", "bright_cyan")
        base_url = get_base_url()
    else:
        short_name = "Blackboard Ultra"
        inst_color = "bright_cyan"
        base_url = ""

    # Tagline + versión (sin resaltado de fondo)
    tagline = Text(justify="center")
    tagline.append(f"Aula Virtual • {short_name}", style="dim white")
    tagline.append("  •  ", style="dim grey50")
    tagline.append("Sincronizador de Cuadernos para IA", style="dim italic grey70")
    tagline.append("  •  ", style="dim grey50")
    tagline.append(f"v{VERSION}", style="bold cyan")
    console.print(tagline)

    # Línea separadora
    console.print(f"[dim grey30]  {'─' * min(width - 4, 78)}[/dim grey30]")

    # Status bar
    status_bar = Text()
    if user and inst_configured:
        name = f"{user.get('name', {}).get('given', '')} {user.get('name', {}).get('family', '')}".strip()
        student_id = user.get("studentId") or user.get("userName") or "ID N/A"
        status_bar.append("  ● ", style="bold green")
        status_bar.append(f"{name} ", style="bold white")
        status_bar.append(f"({student_id})", style="dim cyan")
        status_bar.append("  │  ", style="dim grey42")
        status_bar.append(f"{short_name} ", style=f"bold {inst_color}")
        status_bar.append("Conectado", style="green")
        status_bar.append("  │  ", style="dim grey42")
        status_bar.append(f"{base_url.replace('https://', '')}", style="dim grey50")
    elif inst_configured:
        status_bar.append("  ○ ", style="bold yellow")
        status_bar.append(f"Sesión no iniciada ({short_name})", style="yellow")
        status_bar.append("  │  ", style="dim grey42")
        status_bar.append("Ejecuta ", style="dim")
        status_bar.append("login", style="bold cyan")
        status_bar.append(f" para conectar tu cuenta de {short_name}", style="dim")
    else:
        status_bar.append("  ○ ", style="bold bright_cyan")
        status_bar.append("Configuración inicial pendiente", style="bold bright_cyan")
        status_bar.append("  │  ", style="dim grey42")
        status_bar.append("Selecciona tu universidad para continuar", style="dim")

    console.print(status_bar)
    console.print()


def timed_pause(seconds: int = 3) -> None:
    """
    Pausa con temporizador visual simple de cuenta regresiva (3s por defecto).
    Avanza automáticamente al terminar el tiempo o inmediatamente si el usuario presiona ENTER o cualquier tecla.
    """
    console.print()
    is_tty = hasattr(sys.stdin, "isatty") and sys.stdin.isatty()
    try:
        if not is_tty:
            time.sleep(min(seconds, 1))
            return

        for remaining in range(seconds, 0, -1):
            text = f"\r[dim grey50]  Continuando en [bold cyan]{remaining}s[/bold cyan]... (o presiona ENTER)[/dim grey50]   "
            console.print(text, end="")
            start_chunk = time.time()
            while time.time() - start_chunk < 1.0:
                if sys.platform == "win32":
                    import msvcrt
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        if ch in (b"\x00", b"\xe0") and msvcrt.kbhit():
                            msvcrt.getch()
                        while msvcrt.kbhit():
                            msvcrt.getch()
                        console.print("\r" + " " * 65 + "\r", end="")
                        return
                else:
                    import select
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if rlist:
                        sys.stdin.readline()
                        console.print("\r" + " " * 65 + "\r", end="")
                        return
                time.sleep(0.05)

        console.print("\r" + " " * 65 + "\r", end="")
    except KeyboardInterrupt:
        console.print("\r" + " " * 65 + "\r", end="")
        raise


def check_auth_or_prompt():
    """Verifica si hay una sesión activa con fallback interactivo."""
    user = verify_session()
    if user:
        return user
    inst = get_active_institution()
    short_name = inst.get("short_name", "tu universidad")
    console.print(f"[yellow]⚠️  No se detectó una sesión activa en Blackboard Ultra ({short_name}).[/yellow]")
    if Confirm.ask(f"   ¿Deseas iniciar sesión en {short_name} ahora mismo?", default=True):
        cmd_login()
        return verify_session()
    return None


def cmd_login():
    """Flujo de autenticación con navegador persistente."""
    user = verify_session()
    print_header(user)
    if user:
        name = f"{user.get('name', {}).get('given', '')} {user.get('name', {}).get('family', '')}".strip()
        console.print(f"[bold green]✔ Sesión actualmente válida para:[/bold green] [bold white]{name}[/bold white]")
        if not Confirm.ask("\n¿Deseas volver a autenticarte con otra cuenta?", default=False):
            return

    success = interactive_login()
    if success:
        user = verify_session()
        print_header(user)
        if user:
            name = f"{user.get('name', {}).get('given', '')} {user.get('name', {}).get('family', '')}".strip() or user.get("userName") or "Estudiante"
            console.print(f"[bold green]✔ ¡Autenticación completada y tokens almacenados de forma segura para {name}![/bold green]")
        else:
            console.print("[yellow]⚠️ Se guardaron las cookies de sesión, pero el aula virtual aún no las reporta como activas.[/yellow]")
            console.print("[dim]   (Prueba volver a iniciar sesión asegurándote de llegar hasta la lista de tus cursos).[/dim]")
    else:
        console.print("[bold red]✖ No se pudo completar el inicio de sesión.[/bold red]")

    timed_pause(3)


def cmd_status():
    """Diagnóstico detallado de sesión y conectividad."""
    user = verify_session()
    print_header(user)
    inst = get_active_institution()
    inst_color = inst.get("color", "bright_cyan")
    base_url = get_base_url()

    table = Table(box=box.ROUNDED, border_style="grey37", show_header=False, padding=(0, 2))
    table.add_column("Propiedad", style="dim bright_cyan")
    table.add_column("Valor", style="white")

    if user:
        name = f"{user.get('name', {}).get('given', '')} {user.get('name', {}).get('family', '')}".strip()
        table.add_row("Estado", "[bold green]● Conectado[/bold green]")
        table.add_row("Institución", f"[{inst_color}]{inst.get('name', 'N/A')}[/{inst_color}]")
        table.add_row("Estudiante", f"[bold white]{name}[/bold white]")
        table.add_row("Código / Usuario", f"[bright_cyan]{user.get('studentId') or user.get('userName', 'N/A')}[/bright_cyan]")
        table.add_row("ID Ultra", f"[dim]{user.get('id', 'N/A')}[/dim]")
        table.add_row("Servidor", f"[dim]{base_url}[/dim]")
        table.add_row("Cuadernos", f"[dim]{OUTPUT_DIR}[/dim]")

        update_info = check_for_updates()
        if update_info and update_info.get("has_update"):
            table.add_row("Versión CLI", f"v{VERSION} [bold bright_green](¡Nueva versión {update_info['latest_version']} disponible!)[/bold bright_green]")
        else:
            table.add_row("Versión CLI", f"v{VERSION} [dim green](Al día)[/dim green]")

        console.print(Panel(table, title="[bold white] Diagnóstico [/bold white]", title_align="left", border_style="grey37", box=box.ROUNDED))
    else:
        table.add_row("Estado", "[bold red]✖ Sesión inactiva o expirada[/bold red]")
        table.add_row("Institución activa", f"[{inst_color}]{inst.get('name', 'N/A')}[/{inst_color}]")
        table.add_row("Servidor", f"[dim]{base_url}[/dim]")
        table.add_row("Cuadernos", f"[dim]{OUTPUT_DIR}[/dim]")

        update_info = check_for_updates()
        if update_info and update_info.get("has_update"):
            table.add_row("Versión CLI", f"v{VERSION} [bold bright_green](¡Nueva versión {update_info['latest_version']} disponible!)[/bold bright_green]")
        else:
            table.add_row("Versión CLI", f"v{VERSION} [dim green](Al día)[/dim green]")

        console.print(Panel(
            table,
            title="[bold white] Diagnóstico [/bold white]",
            title_align="left",
            border_style="red",
            box=box.ROUNDED,
            subtitle="[dim]Ejecuta 'login' para acceder o 'institucion' para cambiar de universidad[/dim]"
        ))


def cmd_courses():
    """Muestra la tabla de asignaturas del ciclo."""
    user = check_auth_or_prompt()
    if not user:
        return
    print_header(user)

    with console.status("[bold cyan]Consultando asignaturas matriculadas...[/bold cyan]"):
        client = UltraClient()
        courses = client.get_courses()

    if not courses:
        console.print("[yellow]No se encontraron asignaturas activas registradas en tu perfil.[/yellow]")
        return

    table = Table(
        box=box.ROUNDED,
        border_style="grey37",
        header_style="bold bright_cyan",
        title="[bold white] Cursos Matriculados [/bold white]",
        title_justify="left",
        padding=(0, 1)
    )
    table.add_column("#", style="dim", width=4, justify="center")
    table.add_column("Código", style="bright_cyan", width=22)
    table.add_column("Nombre del Curso", style="bold white")
    table.add_column("Modalidad", width=14, justify="center")

    for i, c in enumerate(courses, 1):
        name = c.get("name", "Sin nombre")
        modality = "Virtual" if "Virtual" in name else "Presencial"
        mod_style = "[bold cyan]🖥  Virtual[/bold cyan]" if modality == "Virtual" else "[bold yellow]🏫 Presencial[/bold yellow]"
        clean_name = name.replace(" - Virtual", "").replace(" - Presencial", "").strip()
        table.add_row(str(i), c.get("course_id", "-"), clean_name, mod_style)

    console.print(table)


def cmd_agenda():
    """Vista de radar de fechas, entregas y exámenes."""
    user = check_auth_or_prompt()
    if not user:
        return
    print_header(user)

    with console.status("[bold cyan]Sincronizando calendario y evaluaciones...[/bold cyan]"):
        client = UltraClient()
        courses = client.get_courses()
        all_evals = []
        for c in courses:
            evals = client.get_course_evaluations(c["id"])
            for ev in evals:
                ev["course_name"] = c["name"].replace(" - Virtual", "").replace(" - Presencial", "").strip()
                all_evals.append(ev)

    sorted_evals = sorted(
        [ev for ev in all_evals if ev.get("due_date") and ev.get("due_date") != "Por definir"],
        key=lambda x: x["due_date"]
    )

    if not sorted_evals:
        console.print("[yellow]No hay evaluaciones con fecha límite registrada actualmente.[/yellow]")
        return

    table = Table(
        box=box.ROUNDED,
        border_style="grey37",
        header_style="bold bright_cyan",
        title="[bold white] Radar de Evaluaciones [/bold white]",
        title_justify="left",
        padding=(0, 1)
    )
    table.add_column("Fecha", style="bold bright_cyan", width=26)
    table.add_column("Curso", style="bold white", width=30)
    table.add_column("Evaluación", style="yellow")
    table.add_column("Pts", style="green", width=8, justify="center")

    for ev in sorted_evals:
        due = format_date(ev.get("due_date"))
        pts = f"{ev.get('points_possible')}" if ev.get("points_possible") is not None else "-"
        table.add_row(due, ev["course_name"][:28], ev.get("title", ""), pts)

    console.print(table)


def _run_sync_all(organizer, courses):
    """Ejecuta la sincronización completa de todos los cursos matriculados."""
    console.print("\n[bold cyan]Iniciando compilación de todos los Cuadernos de Estudio...[/bold cyan]\n")

    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=35, style="grey23", complete_style="bright_cyan"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        overall_task = progress.add_task("Progreso General", total=len(courses))
        sub_task = progress.add_task("Conectando con Blackboard Ultra...", total=None)

        def callback(event_type: str, *args):
            if event_type == "status":
                msg = args[0]
                progress.update(sub_task, description=f"[dim cyan]{msg}[/dim cyan]")
            elif event_type == "course_start":
                course_name, current_idx, total = args
                progress.update(overall_task, total=total, completed=current_idx - 1, description=f"Cursos: {current_idx}/{total}")
                progress.update(sub_task, description=f"[bold yellow]📚 {course_name[:35]}...[/bold yellow]")
                console.print(f"[bold cyan]┌── [[/bold cyan][bold white]{current_idx}/{total}[/bold white][bold cyan]] Sincronizando:[/bold cyan] [bold white]{course_name}[/bold white]")
            elif event_type == "action":
                action_text = args[0]
                progress.update(sub_task, description=f"[green]{action_text}[/green]")
            elif event_type == "log":
                log_text = args[0]
                console.print(f"[bold cyan]│[/bold cyan]  {log_text}")
            elif event_type == "course_end":
                course_name, current_idx, total = args
                progress.update(overall_task, completed=current_idx)
                console.print(f"[bold cyan]└──[/bold cyan] [bold green]✔ Cuaderno completado para {course_name[:35]}[/bold green]\n")

        summary = organizer.sync_all_courses(progress_callback=callback)
        progress.update(overall_task, completed=summary["total_courses"], description="[bold green]¡Sincronización completada![/bold green]")
        progress.update(sub_task, description="[bold green]100% al día[/bold green]")

    console.print()
    table = Table(
        box=box.ROUNDED,
        border_style="grey37",
        header_style="bold bright_cyan",
        title="[bold white] Resumen de Sincronización [/bold white]",
        title_justify="left",
        padding=(0, 1)
    )
    table.add_column("Curso", style="bold white")
    table.add_column("Evals", style="bright_cyan", width=8, justify="center")
    table.add_column("Avisos", style="yellow", width=8, justify="center")
    table.add_column("Archivos", style="green", width=10, justify="center")

    for c in summary["courses"]:
        table.add_row(
            c["name"].replace(" - Virtual", "").replace(" - Presencial", ""),
            str(len(c["evaluations"])),
            str(c["announcements_count"]),
            str(c["files_count"])
        )

    console.print(table)
    console.print(f"\n  📁 Cuadernos en: [bold bright_cyan]{OUTPUT_DIR}[/bold bright_cyan]")
    console.print("  💡 Contexto IA:  [bold bright_cyan]cuadernos/RESUMEN_SEMESTRE_IA.md[/bold bright_cyan]")

    if Confirm.ask("\n[bold cyan]✨ ¿Deseas generar la carpeta unificada para Gemini Notebook / NotebookLM para los cursos sincronizados?[/bold cyan]", default=True):
        for c in summary["courses"]:
            _export_course_to_gemini(Path(c["dir"]), c.get("downloaded_files"))


def _run_sync_single_course(organizer, selected_course, target_section=None):
    """Ejecuta la sincronización de un curso individual o una unidad/semana específica con barra de progreso."""
    c_name = selected_course["name"].replace(" - Virtual", "").replace(" - Presencial", "")
    target_label = target_section["title"] if target_section else "Todo el curso"
    
    console.print(f"\n[bold cyan]Sincronizando:[/bold cyan] [bold white]{c_name}[/bold white]")
    console.print(f"[bold cyan]Alcance:[/bold cyan] [yellow]{target_label}[/yellow]\n")

    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=35, style="grey23", complete_style="bright_cyan"),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        sync_task = progress.add_task(f"Iniciando {target_label}...", total=None)

        def callback(event_type: str, *args):
            if event_type == "action":
                progress.update(sync_task, description=f"[bold green]{args[0]}[/bold green]")
            elif event_type == "log":
                console.print(f"[bold cyan]│[/bold cyan]  {args[0]}")

        c_info = organizer.sync_course(selected_course, target_section=target_section, progress_callback=callback)
        progress.update(sync_task, description=f"[bold green]✔ ¡{target_label} completado![/bold green]")

    console.print(f"\n[bold green]✔ ¡Sincronización de {c_name} finalizada con éxito![/bold green]")
    console.print(f"📁 Cuaderno actualizado en: [bold cyan]{c_info['dir']}[/bold cyan]")
    console.print(f"📊 Materiales procesados: [bold white]{c_info['files_count']}[/bold white] | Evaluaciones: [cyan]{len(c_info['evaluations'])}[/cyan] | Anuncios: [yellow]{c_info['announcements_count']}[/yellow]")

    if Confirm.ask("\n[bold cyan]✨ ¿Deseas generar la carpeta unificada para Gemini Notebook / NotebookLM?[/bold cyan]", default=True):
        _export_course_to_gemini(Path(c_info['dir']), c_info.get("downloaded_files"))


def _export_course_to_gemini(course_dir: Path, manifest: list[dict] | None = None):
    with console.status(f"[bold cyan]Generando carpeta unificada para Gemini Notebook en {course_dir.name}...[/bold cyan]"):
        count = generate_gemini_notebook(course_dir, manifest)
    console.print(f"[bold green]✔ Carpeta gemini_notebook/ lista con {count} archivos unificados.[/bold green]")


def cmd_notebook():
    """Genera la carpeta unificada para Gemini Notebook (Exportación sin red)."""
    dirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if not dirs:
        console.print("[yellow]No se encontraron cursos descargados en la carpeta cuadernos.[/yellow]")
        return

    options = [
        {"id": "0", "key_label": "[0]", "icon": "⚡", "command": "todos", "desc": "Exportar TODOS los cursos locales", "aliases": ["0", "todos", "all"]},
        {"id": "v", "key_label": "[v]", "icon": "↩", "command": "volver", "desc": "Volver al menú principal", "aliases": ["v", "volver", "back"]},
        {"is_separator": True, "title": ""},
    ]

    for i, d in enumerate(dirs, 1):
        options.append({
            "id": str(i),
            "key_label": f"[{i}]",
            "icon": "📂",
            "command": d.name,
            "desc": "",
            "aliases": [str(i), d.name.lower()]
        })

    choice = hybrid_select(
        options=options,
        title="Exportar a Gemini Notebook",
        header_func=print_header,
        tip_text="Arrastra la carpeta 'gemini_notebook' a NotebookLM para crear podcasts de estudio.",
        default_idx=0
    )

    if choice in ["v", "volver", "back"]:
        return False
    elif choice in ["0", "todos", "all"]:
        for d in dirs:
            _export_course_to_gemini(d)
        return True
    else:
        target_dir = None
        try:
            d_idx = int(choice) - 1
            if 0 <= d_idx < len(dirs):
                target_dir = dirs[d_idx]
        except ValueError:
            for d in dirs:
                if choice.lower() in d.name.lower():
                    target_dir = d
                    break

        if target_dir:
            _export_course_to_gemini(target_dir)
            return True
        else:
            console.print("[red]Opción inválida.[/red]")
            return False


def cmd_sync():
    """Sincronización interactiva: permite elegir todos los cursos o un curso y semana específica."""
    user = check_auth_or_prompt()
    if not user:
        return
    print_header(user)

    client = UltraClient()
    organizer = CourseNotebookOrganizer(client)

    with console.status("[bold cyan]Cargando asignaturas...[/bold cyan]"):
        courses = client.get_courses()

    if not courses:
        console.print("[yellow]No se encontraron asignaturas activas.[/yellow]")
        return

    # 1. Menú de selección de curso
    course_options = [
        {"id": "0", "key_label": "[0]", "icon": "⚡", "command": "todos", "desc": "Sincronizar TODOS los cursos del semestre", "aliases": ["0", "todos", "all"]},
        {"id": "v", "key_label": "[v]", "icon": "↩", "command": "volver", "desc": "Volver al menú principal", "aliases": ["v", "volver", "back"]},
        {"is_separator": True, "title": ""},
    ]
    for i, c in enumerate(courses, 1):
        clean_name = c["name"].replace(" - Virtual", "").replace(" - Presencial", "")
        cid = c.get("course_id", "")
        course_options.append({
            "id": str(i),
            "key_label": f"[{i}]",
            "icon": "📚",
            "command": clean_name,
            "desc": f"({cid})" if cid else "",
            "aliases": [str(i), clean_name.lower(), cid.lower()]
        })

    c_choice = hybrid_select(
        options=course_options,
        title="Seleccionar Curso",
        header_func=lambda: print_header(user),
        tip_text="Escribe el número del curso o 'v' para retroceder.",
        default_idx=0
    )

    if c_choice in ["v", "volver", "back"]:
        return False

    if c_choice in ["0", "todos", "all"]:
        _run_sync_all(organizer, courses)
        return True

    try:
        c_idx = int(c_choice) - 1
        if 0 <= c_idx < len(courses):
            selected_course = courses[c_idx]
        else:
            console.print("[red]Opción de curso inválida.[/red]")
            return False
    except ValueError:
        # Check alias
        selected_course = None
        for i, c in enumerate(courses, 1):
            if c_choice == str(i) or c_choice in c["name"].lower() or c_choice == c.get("course_id", "").lower():
                selected_course = c
                break
        if not selected_course:
            console.print("[red]Opción de curso inválida.[/red]")
            return False

    # 2. El usuario seleccionó un curso específico
    course_clean_name = selected_course["name"].replace(" - Virtual", "").replace(" - Presencial", "")

    with console.status(f"[bold cyan]Explorando unidades y semanas de {course_clean_name}...[/bold cyan]"):
        sections = client.get_course_sections(selected_course["id"])

    if not sections:
        console.print("[yellow]  ⚠ No se encontraron unidades/semanas individuales. Sincronizando curso completo...[/yellow]")
        _run_sync_single_course(organizer, selected_course, target_section=None)
        return True

    # Menú de unidades / semanas
    section_options = [
        {"id": "0", "key_label": "[0]", "icon": "📁", "command": "todo", "desc": "Sincronizar TODO el curso (todas las semanas)", "aliases": ["0", "todo", "all"]},
        {"id": "v", "key_label": "[v]", "icon": "↩", "command": "volver", "desc": "Volver atrás", "aliases": ["v", "volver", "back"]},
        {"is_separator": True, "title": ""},
    ]
    for i, s in enumerate(sections, 1):
        is_sub = s.get("level", 0) > 0
        prefix = "↳" if is_sub else "📂"
        section_options.append({
            "id": str(i),
            "key_label": f"[{i}]",
            "icon": prefix,
            "command": s["title"],
            "desc": "",
            "aliases": [str(i), s["title"].lower()]
        })

    s_choice = hybrid_select(
        options=section_options,
        title=course_clean_name,
        header_func=lambda: print_header(user),
        tip_text="Escribe el número de la sección o 'v' para retroceder.",
        default_idx=0
    )

    if s_choice in ["v", "volver", "back"]:
        return cmd_sync()  # Vuelve al menú anterior recursivamente

    if s_choice in ["0", "todo", "all"]:
        _run_sync_single_course(organizer, selected_course, target_section=None)
        return True
    else:
        chosen_section = None
        try:
            sec_idx = int(s_choice) - 1
            if 0 <= sec_idx < len(sections):
                chosen_section = sections[sec_idx]
        except ValueError:
            for s in sections:
                if s_choice.lower() in s.get("title", "").lower():
                    chosen_section = s
                    break

        if chosen_section:
            _run_sync_single_course(organizer, selected_course, target_section=chosen_section)
            return True
        else:
            console.print("[red]Sección inválida.[/red]")
            return False


def cmd_logout():
    """Cierra la sesión actual y elimina credenciales locales."""
    inst = get_active_institution()
    print_header()
    if logout():
        console.print(f"[bold green]✔ Sesión de {inst.get('short_name', 'Blackboard')} cerrada exitosamente. Credenciales eliminadas.[/bold green]")
    else:
        console.print("[bold red]✖ Hubo un problema al intentar cerrar sesión.[/bold red]")


def cmd_update(update_info: dict | None = None):
    """Muestra información de la última versión y abre la página de Releases en el navegador."""
    import webbrowser
    print_header()
    if update_info is None:
        update_info = check_for_updates()

    target_url = (update_info and update_info.get("url")) or RELEASES_URL
    latest_v = (update_info and update_info.get("latest_version")) or f"v{VERSION}"
    has_update = bool(update_info and update_info.get("has_update"))

    if has_update:
        panel_title = "[bold bright_green] 🚀 Nueva Versión Disponible [/bold bright_green]"
        border_style = "bright_green"
        status_msg = f"[bold green]¡Hay una nueva versión disponible ({latest_v})![/bold green]"
    else:
        panel_title = "[bold bright_cyan] ℹ️ Información de Versión [/bold bright_cyan]"
        border_style = "grey37"
        status_msg = f"[bold green]✔ Ya cuentas con la versión más reciente (v{VERSION}).[/bold green]"

    console.print(Panel(
        f"[bold white]Versión instalada:[/bold white] [bold cyan]v{VERSION}[/bold cyan]\n"
        f"[bold white]Última versión en GitHub:[/bold white] [bold white]{latest_v}[/bold white]\n"
        f"[bold white]Estado:[/bold white] {status_msg}\n\n"
        f"[bold white]Enlace de Releases:[/bold white] [bright_cyan]{RELEASES_URL}[/bright_cyan]\n\n"
        f"[dim grey70]Abriendo el enlace oficial de descargas en tu navegador web...[/dim grey70]",
        title=panel_title,
        title_align="left",
        border_style=border_style,
        box=box.ROUNDED
    ))

    console.print("\n[dim]Abriendo navegador...[/dim]")
    try:
        webbrowser.open(target_url)
    except Exception as e:
        console.print(f"[yellow]No se pudo abrir el navegador automáticamente: {e}[/yellow]")

    console.print(f"[dim]Enlace directo:[/dim] [bold cyan]{target_url}[/bold cyan]")
    timed_pause(3)


def cmd_open_cuadernos():
    """Abre la carpeta raíz de cuadernos en el explorador de archivos nativo."""
    print_header()
    console.print(Panel(
        f"[bold white]Abriendo carpeta de cuadernos:[/bold white]\n"
        f"[bright_cyan]{OUTPUT_DIR}[/bright_cyan]\n\n"
        f"[dim grey70]Se abrirá la ventana del explorador de archivos en tu sistema operativo...[/dim grey70]",
        title="[bold bright_cyan] 📁 Explorador de Cuadernos [/bold bright_cyan]",
        title_align="left",
        border_style="bright_cyan",
        box=box.ROUNDED
    ))
    ok = open_in_file_manager(OUTPUT_DIR)
    if ok:
        console.print("[bold green]✔ Carpeta abierta en el explorador de archivos.[/bold green]")
    else:
        console.print(f"[yellow]⚠️ No se pudo abrir automáticamente. Puedes acceder manualmente en: {OUTPUT_DIR}[/yellow]")
    timed_pause(2)


def cmd_open_gemini():
    """Abre la carpeta de cuadernos con instrucciones para Gemini Notebook / NotebookLM."""
    print_header()
    console.print(Panel(
        f"[bold white]Carpeta de Cuadernos para IA:[/bold white]\n"
        f"[bright_cyan]{OUTPUT_DIR}[/bright_cyan]\n\n"
        f"[bold bright_green]💡 Tip Pro para Estudiar con NotebookLM:[/bold bright_green]\n"
        f"[white]1. Entra a la carpeta de tu curso y luego a [bold cyan]gemini_notebook/[/bold cyan].[/white]\n"
        f"[white]2. Arrastra los archivos [bold].md[/bold] o [bold].pdf[/bold] directamente a [bold cyan]NotebookLM[/bold cyan] (https://notebooklm.google.com).[/white]\n"
        f"[white]3. ¡Genera podcasts de audio, resúmenes automáticos y guías de estudio interactivas![/white]",
        title="[bold bright_magenta] 🤖 Gemini Notebook & NotebookLM [/bold bright_magenta]",
        title_align="left",
        border_style="bright_magenta",
        box=box.ROUNDED
    ))
    open_in_file_manager(OUTPUT_DIR)
    timed_pause(3)


def cmd_open_web():
    """Abre el aula virtual activa en el navegador web habitual."""
    import webbrowser
    print_header()
    base_url = get_base_url()
    inst = get_active_institution()
    inst_name = inst.get("name", "Blackboard Learn")
    console.print(Panel(
        f"[bold white]Institución:[/bold white] [bold cyan]{inst_name}[/bold cyan]\n"
        f"[bold white]Aula Virtual:[/bold white] [bright_cyan]{base_url}[/bright_cyan]\n\n"
        f"[dim grey70]Abriendo el portal web en tu navegador habitual...[/dim grey70]",
        title="[bold bright_cyan] 🌐 Blackboard Web [/bold bright_cyan]",
        title_align="left",
        border_style="bright_cyan",
        box=box.ROUNDED
    ))
    try:
        webbrowser.open(base_url)
        console.print("[bold green]✔ Navegador web abierto.[/bold green]")
    except Exception as e:
        console.print(f"[yellow]⚠️ No se pudo abrir automáticamente el navegador: {e}[/yellow]")
    timed_pause(2)


def cmd_institution(is_first_time: bool = False):
    """Selector y configurador de universidad / Blackboard."""
    options = [
        {"id": "1", "key_label": "[1]", "icon": "🏫", "command": "UPC", "desc": "Universidad Peruana de Ciencias Aplicadas (aulavirtual.upc.edu.pe)", "aliases": ["1", "upc"]},
        {"id": "2", "key_label": "[2]", "icon": "🏫", "command": "UCV", "desc": "Universidad César Vallejo (ucv.blackboard.com)", "aliases": ["2", "ucv"]},
        {"id": "3", "key_label": "[3]", "icon": "🏫", "command": "UPN", "desc": "Universidad Privada del Norte (upn.blackboard.com)", "aliases": ["3", "upn"]},
        {"id": "4", "key_label": "[4]", "icon": "🏫", "command": "SENATI", "desc": "Servicio Nacional de Adiestramiento en Trabajo Industrial (senati.blackboard.com)", "aliases": ["4", "senati"]},
        {"id": "5", "key_label": "[5]", "icon": "🌐", "command": "Personalizada", "desc": "Cualquier Blackboard Ultra (Ingresar URL manualmente)", "aliases": ["5", "personalizada", "custom"]},
    ]
    if not is_first_time:
        options.append({"is_separator": True, "title": ""})
        options.append({"id": "0", "key_label": "[0]", "icon": "↩", "command": "cancelar", "desc": "Cancelar / Mantener actual", "aliases": ["0", "cancelar", "cancel"]})

    title = "Configuración Inicial" if is_first_time else "Configuración de Universidad"
    tip = "Usa las flechas [▲/▼] o escribe el número o nombre de tu institución."

    def _inst_header():
        print_header()
        if is_first_time:
            console.print(Panel(
                "[bold white]¡Bienvenido a Blackboard CLI![/bold white]\n\n"
                "[dim white]Para comenzar, por favor selecciona la universidad o instituto al que perteneces.[/dim white]\n"
                "[dim grey70]Esta configuración se guardará automáticamente en tu equipo para tus próximas sesiones.[/dim grey70]",
                title="[bold bright_cyan] 🎓 Configuración Inicial [/bold bright_cyan]",
                title_align="left",
                border_style="bright_cyan",
                box=box.ROUNDED
            ))
        else:
            current = get_active_institution()
            console.print(Panel(
                f"[bold white]Institución activa:[/bold white] [{current.get('color', 'white')}]{current.get('name')}[/{current.get('color', 'white')}]\n"
                f"[dim white]Servidor:[/dim white] [dim]{current.get('base_url')}[/dim]\n\n"
                f"[dim grey70]Cada universidad mantiene sus propias sesiones, credenciales y caché de descargas de forma aislada.[/dim grey70]",
                title="[bold white] 🏫 Configuración de Universidad [/bold white]",
                title_align="left",
                border_style="grey37",
                box=box.ROUNDED
            ))

    default_pos = 0 if is_first_time else (len(options) - 1)
    choice = hybrid_select(
        options=options,
        title=title,
        header_func=_inst_header,
        tip_text=tip,
        default_idx=default_pos
    )

    if choice in ["0", "cancelar", "cancel"]:
        return

    new_inst = None
    if choice in ["1", "upc"]:
        new_inst = set_active_institution("upc")
    elif choice in ["2", "ucv"]:
        new_inst = set_active_institution("ucv")
    elif choice in ["3", "upn"]:
        new_inst = set_active_institution("upn")
    elif choice in ["4", "senati"]:
        new_inst = set_active_institution("senati")
    elif choice in ["5", "personalizada", "custom"]:
        console.print("\n[dim]Ingresa la URL o dominio del aula virtual de tu universidad o instituto.[/dim]")
        console.print("[dim]Ejemplos: [cyan]senati.blackboard.com[/cyan], [cyan]ucv.blackboard.com[/cyan] o [cyan]https://miinstituto.blackboard.com[/cyan][/dim]\n")
        raw_url = Prompt.ask("[bold bright_cyan]URL de Blackboard[/bold bright_cyan]")
        if not raw_url.strip():
            console.print("[yellow]Operación cancelada: URL vacía.[/yellow]")
            if is_first_time:
                return cmd_institution(is_first_time=True)
            return

        with console.status("[bold cyan]Verificando compatibilidad con Blackboard Learn / Ultra...[/bold cyan]"):
            ok, desc = validate_blackboard_url(raw_url)

        if ok:
            console.print(f"[bold green]✔ Servidor compatible detectado:[/bold green] {desc}")
            custom_name = Prompt.ask("[bold bright_cyan]Nombre o sigla de la institución[/bold bright_cyan] (ej: SENATI, UDEP, PUCP)", default="")
            new_inst = set_active_institution("custom", custom_url=raw_url, custom_name=custom_name)
        else:
            console.print(f"[bold red]✖ No se pudo verificar la compatibilidad de la URL:[/bold red] {desc}")
            proceed = Confirm.ask("¿Deseas guardarla de todas maneras?", default=False)
            if proceed:
                custom_name = Prompt.ask("[bold bright_cyan]Nombre o sigla de la institución[/bold bright_cyan]", default="")
                new_inst = set_active_institution("custom", custom_url=raw_url, custom_name=custom_name)
            else:
                console.print("[dim]Operación cancelada sin cambios.[/dim]")
                if is_first_time:
                    return cmd_institution(is_first_time=True)
                return
    else:
        console.print(f"[red]Opción no reconocida: {choice}[/red]")
        if is_first_time:
            return cmd_institution(is_first_time=True)
        return

    if new_inst:
        prefix = "✔ Configuración inicial guardada:" if is_first_time else "✔ Institución configurada:"
        console.print(f"\n[bold green]{prefix}[/bold green] [bold white]{new_inst['name']}[/bold white] [dim]({new_inst['base_url']})[/dim]")

        # Preguntar si desea iniciar sesión de inmediato si no hay cookies guardadas
        new_user = verify_session()
        if not new_user:
            start_login = Confirm.ask(f"\n¿Deseas iniciar sesión ahora en {new_inst.get('short_name', 'esta institución')}?", default=True)
            if start_login:
                cmd_login()
                return


def interactive_menu():
    """Bucle principal del menú interactivo híbrido estilo Claude Code / Antigravity."""
    if not is_institution_configured():
        cmd_institution(is_first_time=True)

    while True:
        user = verify_session()
        update_info = check_for_updates()

        options = [
            {"id": "1", "key_label": "[1]", "icon": "⚡", "command": "sync", "desc": "Sincronizar aula virtual y actualizar cuadernos", "aliases": ["1", "sync"]},
            {"id": "2", "key_label": "[2]", "icon": "📅", "command": "agenda", "desc": "Radar de exámenes, entregas y fechas clave", "aliases": ["2", "agenda", "calendar"]},
            {"id": "3", "key_label": "[3]", "icon": "📚", "command": "cursos", "desc": "Explorar asignaturas matriculadas", "aliases": ["3", "cursos", "courses"]},
            {"id": "4", "key_label": "[4]", "icon": "🔍", "command": "status", "desc": "Diagnóstico de conexión y sesión", "aliases": ["4", "status"]},
            {"id": "5", "key_label": "[5]", "icon": "🔐", "command": "login", "desc": "Autenticar cuenta o iniciar sesión", "aliases": ["5", "login"]},
            {"id": "6", "key_label": "[6]", "icon": "🚪", "command": "logout", "desc": "Cerrar sesión y borrar credenciales", "aliases": ["6", "logout"]},
            {"id": "7", "key_label": "[7]", "icon": "🤖", "command": "notebook", "desc": "Exportar a Gemini Notebook", "aliases": ["7", "notebook", "export"]},
            {"id": "8", "key_label": "[8]", "icon": "🏫", "command": "institucion", "desc": "Cambiar universidad o instituto", "aliases": ["8", "institucion", "universidad", "university", "inst"]},
            {"is_separator": True, "title": "Accesos Rápidos"},
            {"id": "o", "key_label": "[o]", "icon": "📁", "command": "abrir", "desc": "Abrir carpeta de cuadernos en el explorador", "aliases": ["o", "abrir", "open"]},
            {"id": "g", "key_label": "[g]", "icon": "📂", "command": "gemini", "desc": "Abrir carpeta de notas de Gemini Notebook", "aliases": ["g", "gemini", "notebooklm"]},
            {"id": "w", "key_label": "[w]", "icon": "🌐", "command": "web", "desc": "Abrir aula virtual en el navegador web", "aliases": ["w", "web", "aula"]},
        ]

        if update_info and update_info.get("has_update"):
            latest_v = update_info.get("latest_version")
            options.append({
                "id": "u",
                "key_label": "[u]",
                "icon": "✨",
                "command": "update",
                "desc": f"¡Nueva versión {latest_v} disponible! (Presiona 'u' para descargar)",
                "aliases": ["u", "update", "actualizar", "version"],
                "highlight": True,
            })

        options.append({"is_separator": True, "title": ""})
        options.append({
            "id": "0",
            "key_label": "[0]",
            "icon": "❌",
            "command": "exit",
            "desc": "Salir",
            "aliases": ["0", "exit", "quit", "q"],
        })

        choice = hybrid_select(
            options=options,
            title="Comandos",
            header_func=lambda: print_header(user),
            tip_text=get_random_tip(),
            default_idx=0
        )
        choice = choice.strip().lower()

        if choice in ["1", "sync"]:
            res = cmd_sync()
            if not res:
                continue
        elif choice in ["2", "agenda", "calendar"]:
            cmd_agenda()
        elif choice in ["3", "cursos", "courses"]:
            cmd_courses()
        elif choice in ["4", "status"]:
            cmd_status()
        elif choice in ["5", "login"]:
            cmd_login()
            continue
        elif choice in ["6", "logout"]:
            cmd_logout()
        elif choice in ["7", "notebook", "export"]:
            res = cmd_notebook()
            if not res:
                continue
        elif choice in ["8", "institucion", "universidad", "university", "inst"]:
            cmd_institution()
            continue
        elif choice in ["o", "abrir", "open"]:
            cmd_open_cuadernos()
            continue
        elif choice in ["g", "gemini", "notebooklm"]:
            cmd_open_gemini()
            continue
        elif choice in ["w", "web", "aula"]:
            cmd_open_web()
            continue
        elif choice in ["u", "update", "actualizar", "version"]:
            cmd_update(update_info)
            continue
        elif choice in ["0", "exit", "quit", "q"]:
            console.print()
            console.print("[dim grey50]  Cerrando Blackboard CLI...[/dim grey50]")
            console.print("[bold bright_cyan]  ¡Hasta luego! 👋[/bold bright_cyan]\n")
            sys.exit(0)
        else:
            console.print(f"[red]  ✖ Comando no reconocido: {choice}[/red]")

        if hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            console.print("\n[dim grey50]  Presiona ENTER para continuar...[/dim grey50]")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass


def main():
    try:
        if not is_institution_configured():
            if len(sys.argv) <= 1 or sys.argv[1].lower() not in ["8", "institucion", "universidad", "university", "inst"]:
                cmd_institution(is_first_time=True)

        if len(sys.argv) > 1:
            arg = sys.argv[1].lower()
            if arg in ["1", "sync"]:
                cmd_sync()
            elif arg in ["2", "agenda", "calendar", "examenes"]:
                cmd_agenda()
            elif arg in ["3", "courses", "cursos"]:
                cmd_courses()
            elif arg in ["4", "status"]:
                cmd_status()
            elif arg in ["5", "login"]:
                cmd_login()
            elif arg in ["6", "logout"]:
                cmd_logout()
            elif arg in ["7", "notebook", "export"]:
                cmd_notebook()
            elif arg in ["8", "institucion", "universidad", "university", "inst"]:
                cmd_institution()
            elif arg in ["update", "actualizar", "version"]:
                cmd_update()
            elif arg in ["o", "open", "abrir"]:
                cmd_open_cuadernos()
            elif arg in ["g", "gemini", "notebooklm"]:
                cmd_open_gemini()
            elif arg in ["w", "web", "aula"]:
                cmd_open_web()
            else:
                console.print(f"[red]Comando desconocido: {arg}[/red]")
                console.print("Comandos disponibles: login, status, courses, agenda, sync, logout, notebook, institucion, update, abrir, gemini, web")
        else:
            interactive_menu()
    except KeyboardInterrupt:
        console.print("\n\n[dim]👋 Operación cancelada por el usuario. ¡Hasta luego![/dim]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
