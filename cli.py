"""
Blackboard CLI (UPC) - Asistente de Aula Virtual y Cuadernos de Estudio para IA.
Diseñado con una interfaz moderna inspirada en CLI de agentes de IA (Claude Code, Antigravity).
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

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
        req_file = Path(__file__).parent / "requirements.txt"
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
from rich.prompt import Prompt
from rich import box
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn
)

console = Console(force_terminal=True, color_system="truecolor")

from config import BASE_URL, OUTPUT_DIR, VERSION
from auth import verify_session, interactive_login, logout
from ultra_client import UltraClient
from organizer import CourseNotebookOrganizer, format_date
try:
    import package
    HAS_PACKAGE = True
except ImportError:
    HAS_PACKAGE = False

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

    # Tagline + version pill
    tagline = Text(justify="center")
    tagline.append("  Aula Virtual UPC", style="dim white")
    tagline.append("  •  ", style="dim grey50")
    tagline.append("Sincronizador de Cuadernos para IA", style="dim italic grey70")
    tagline.append(f"  v{VERSION} ", style="bold black on bright_cyan")
    console.print(tagline)

    # Línea separadora
    console.print(f"[dim grey30]  {'─' * min(width - 4, 78)}[/dim grey30]")

    # Status bar
    status_bar = Text()
    if user:
        name = f"{user.get('name', {}).get('given', '')} {user.get('name', {}).get('family', '')}".strip()
        student_id = user.get("studentId") or user.get("userName") or "ID N/A"
        status_bar.append("  ● ", style="bold green")
        status_bar.append(f"{name} ", style="bold white")
        status_bar.append(f"({student_id})", style="dim cyan")
        status_bar.append("  │  ", style="dim grey42")
        status_bar.append("Ultra ", style="bold green")
        status_bar.append("Conectado", style="green")
        status_bar.append("  │  ", style="dim grey42")
        status_bar.append(f"{BASE_URL.replace('https://', '')}", style="dim grey50")
    else:
        status_bar.append("  ○ ", style="bold yellow")
        status_bar.append("Sesión no iniciada", style="yellow")
        status_bar.append("  │  ", style="dim grey42")
        status_bar.append("Ejecuta ", style="dim")
        status_bar.append("login", style="bold cyan")
        status_bar.append(" para conectar tu cuenta UPC", style="dim")

    console.print(status_bar)
    console.print()


def check_auth_or_prompt():
    """Verifica si hay una sesión activa con fallback interactivo."""
    user = verify_session()
    if user:
        return user
    console.print("[yellow]⚠️  No se detectó una sesión activa en Blackboard Ultra.[/yellow]")
    opt = Prompt.ask("   ¿Deseas iniciar sesión en UPC ahora mismo?", choices=["s", "n"], default="s")
    if opt.lower() == "s":
        success = interactive_login()
        if success:
            return verify_session()
    return None


def cmd_login():
    """Flujo de autenticación con navegador persistente."""
    user = verify_session()
    print_header(user)
    if user:
        name = f"{user.get('name', {}).get('given', '')} {user.get('name', {}).get('family', '')}".strip()
        console.print(f"[bold green]✔ Sesión actualmente válida para:[/bold green] [bold white]{name}[/bold white]")
        re_login = Prompt.ask("\n¿Deseas volver a autenticarte con otra cuenta?", choices=["s", "n"], default="n")
        if re_login.lower() != "s":
            return

    success = interactive_login()
    if success:
        user = verify_session()
        print_header(user)
        console.print("[bold green]✔ ¡Autenticación completada y tokens almacenados de forma segura![/bold green]")
    else:
        console.print("[bold red]✖ No se pudo completar el inicio de sesión.[/bold red]")


def cmd_status():
    """Diagnóstico detallado de sesión y conectividad."""
    user = verify_session()
    print_header(user)
    if user:
        name = f"{user.get('name', {}).get('given', '')} {user.get('name', {}).get('family', '')}".strip()
        table = Table(box=box.ROUNDED, border_style="grey37", show_header=False, padding=(0, 2))
        table.add_column("Propiedad", style="dim bright_cyan")
        table.add_column("Valor", style="white")

        table.add_row("Estado", "[bold green]● Conectado[/bold green]")
        table.add_row("Estudiante", f"[bold white]{name}[/bold white]")
        table.add_row("Código UPC", f"[bright_cyan]{user.get('studentId', 'N/A')}[/bright_cyan]")
        table.add_row("ID Ultra", f"[dim]{user.get('id', 'N/A')}[/dim]")
        table.add_row("Servidor", f"[dim]{BASE_URL}[/dim]")
        table.add_row("Cuadernos", f"[dim]{OUTPUT_DIR}[/dim]")

        console.print(Panel(table, title="[bold white] Diagnóstico [/bold white]", title_align="left", border_style="grey37", box=box.ROUNDED))
    else:
        console.print(Panel(
            "[bold red]✖ Sesión inactiva o expirada[/bold red]\n\n"
            "  Ejecuta [bold cyan]login[/bold cyan] para acceder con tu correo institucional.",
            title="[bold white] Diagnóstico [/bold white]",
            title_align="left",
            border_style="red",
            box=box.ROUNDED
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
    course_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), show_edge=False)
    course_table.add_column("Key", style="bold bright_cyan", width=5, justify="right")
    course_table.add_column("Curso", style="bold white")

    course_table.add_row("[0]", "⚡ Sincronizar [bold]TODOS[/bold] los cursos del semestre")
    course_table.add_row("[v]", "↩ Volver al menú principal")
    course_table.add_row("", "")
    for i, c in enumerate(courses, 1):
        clean_name = c["name"].replace(" - Virtual", "").replace(" - Presencial", "")
        course_table.add_row(f"[{i}]", f"📚 {clean_name} [dim grey50]({c.get('course_id')})[/dim grey50]")

    console.print(Panel(
        course_table,
        title="[bold white] Seleccionar Curso [/bold white]",
        title_align="left",
        subtitle="[dim grey42] Escribe el número del curso o 'v' para retroceder [/dim grey42]",
        subtitle_align="left",
        border_style="grey37",
        box=box.ROUNDED
    ))

    valid_choices = [str(i) for i in range(len(courses) + 1)] + ["v"]
    c_choice = Prompt.ask("\n[bold bright_cyan]sync[/bold bright_cyan] [dim grey50]❯[/dim grey50]", choices=valid_choices)

    if c_choice == "v":
        return

    if c_choice == "0":
        _run_sync_all(organizer, courses)
        return

    # 2. El usuario seleccionó un curso específico
    selected_course = courses[int(c_choice) - 1]
    course_clean_name = selected_course["name"].replace(" - Virtual", "").replace(" - Presencial", "")

    with console.status(f"[bold cyan]Explorando unidades y semanas de {course_clean_name}...[/bold cyan]"):
        sections = client.get_course_sections(selected_course["id"])

    if not sections:
        console.print("[yellow]  ⚠ No se encontraron unidades/semanas individuales. Sincronizando curso completo...[/yellow]")
        _run_sync_single_course(organizer, selected_course, target_section=None)
        return

    # Menú de unidades / semanas
    section_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), show_edge=False)
    section_table.add_column("Key", style="bold bright_cyan", width=5, justify="right")
    section_table.add_column("Unidad / Semana", style="bold white")

    section_table.add_row("[0]", "📁 Sincronizar [bold]TODO[/bold] el curso (todas las semanas)")
    section_table.add_row("[v]", "↩ Volver atrás")
    section_table.add_row("", "")
    for i, s in enumerate(sections, 1):
        is_sub = s.get("level", 0) > 0
        style = "dim white" if is_sub else "bold white"
        prefix = "   ↳ " if is_sub else "📂 "
        section_table.add_row(f"[{i}]", f"{prefix}{s['title']}", style=style)

    console.print()
    console.print(Panel(
        section_table,
        title=f"[bold white] {course_clean_name} [/bold white]",
        title_align="left",
        subtitle="[dim grey42] Escribe el número de la sección o 'v' para retroceder [/dim grey42]",
        subtitle_align="left",
        border_style="grey37",
        box=box.ROUNDED
    ))

    sec_choices = [str(i) for i in range(len(sections) + 1)] + ["v"]
    s_choice = Prompt.ask("\n[bold bright_cyan]sección[/bold bright_cyan] [dim grey50]❯[/dim grey50]", choices=sec_choices)

    if s_choice == "v":
        return cmd_sync()  # Vuelve al menú anterior recursivamente

    if s_choice == "0":
        _run_sync_single_course(organizer, selected_course, target_section=None)
    else:
        chosen_section = sections[int(s_choice) - 1]
        _run_sync_single_course(organizer, selected_course, target_section=chosen_section)


def cmd_package():
    """Empaqueta una versión limpia y segura para compartir."""
    print_header(verify_session())
    if not HAS_PACKAGE:
        console.print("[bold yellow]El script de empaquetado (package.py) no está presente.[/bold yellow]")
        console.print("Ya estás usando una versión extraída o portable.")
        return
    console.print("[bold cyan]Generando paquete portable seguro (ZIP)...[/bold cyan]\n")
    package.create_package()


def cmd_logout():
    """Cierra la sesión actual y elimina credenciales locales."""
    print_header()
    if logout():
        console.print("[bold green]✔ Sesión cerrada exitosamente. Credenciales eliminadas.[/bold green]")
    else:
        console.print("[bold red]✖ Hubo un problema al intentar cerrar sesión.[/bold red]")

def interactive_menu():
    """Bucle principal del menú interactivo estilo Claude Code / Antigravity."""
    while True:
        user = verify_session()
        print_header(user)

        width = _get_terminal_width()

        menu_table = Table(
            box=box.SIMPLE,
            show_header=False,
            padding=(0, 1),
            show_edge=False,
        )
        menu_table.add_column("Key", style="bold bright_cyan", width=5, justify="right")
        menu_table.add_column("Icon", width=3)
        menu_table.add_column("Comando", style="bold white", width=12)
        menu_table.add_column("Descripción", style="dim grey70")

        menu_table.add_row("[1]", "⚡", "sync", "Sincronizar aula virtual y actualizar cuadernos")
        menu_table.add_row("[2]", "📅", "agenda", "Radar de exámenes, entregas y fechas clave")
        menu_table.add_row("[3]", "📚", "cursos", "Explorar asignaturas matriculadas")
        menu_table.add_row("[4]", "🔍", "status", "Diagnóstico de conexión y sesión")
        menu_table.add_row("[5]", "🔐", "login", "Autenticar cuenta o iniciar sesión")
        menu_table.add_row("[6]", "🚪", "logout", "Cerrar sesión y borrar credenciales")
        menu_table.add_row("[7]", "📦", "package", "Generar ZIP seguro para compartir")
        menu_table.add_row("", "", "", "")
        menu_table.add_row("[0]", "❌", "exit", "Salir")

        console.print(Panel(
            menu_table,
            title="[bold white] Comandos [/bold white]",
            title_align="left",
            subtitle=f"[dim grey42] Escribe un número o el nombre del comando [/dim grey42]",
            subtitle_align="left",
            border_style="grey37",
            box=box.ROUNDED,
            padding=(0, 1)
        ))
        console.print()

        choice = Prompt.ask("[bold bright_cyan]bb-cli[/bold bright_cyan] [dim grey50]❯[/dim grey50]", default="1")
        choice = choice.strip().lower()

        if choice in ["1", "sync"]:
            cmd_sync()
        elif choice in ["2", "agenda", "calendar"]:
            cmd_agenda()
        elif choice in ["3", "cursos", "courses"]:
            cmd_courses()
        elif choice in ["4", "status"]:
            cmd_status()
        elif choice in ["5", "login"]:
            cmd_login()
        elif choice in ["6", "logout"]:
            cmd_logout()
        elif choice in ["7", "package", "empaquetar"]:
            cmd_package()
        elif choice in ["0", "exit", "quit", "q"]:
            console.print()
            console.print("[dim grey50]  Cerrando Blackboard CLI...[/dim grey50]")
            console.print("[bold bright_cyan]  ¡Hasta luego! 👋[/bold bright_cyan]\n")
            sys.exit(0)
        else:
            console.print(f"[red]  ✖ Comando no reconocido: {choice}[/red]")

        console.print("\n[dim grey50]  Presiona ENTER para continuar...[/dim grey50]")
        input()


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "login":
            cmd_login()
        elif arg == "status":
            cmd_status()
        elif arg in ["courses", "cursos"]:
            cmd_courses()
        elif arg in ["agenda", "calendar", "examenes"]:
            cmd_agenda()
        elif arg == "sync":
            cmd_sync()
        elif arg == "logout":
            cmd_logout()
        elif arg in ["package", "empaquetar"]:
            cmd_package()
        else:
            console.print(f"[red]Comando desconocido: {arg}[/red]")
            console.print("Comandos disponibles: login, status, courses, agenda, sync, logout, package")
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
