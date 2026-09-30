"""
Módulo de interfaz de usuario de consola para Blackboard CLI.
Proporciona navegación interactiva por flechas [▲/▼], buffer de texto simultáneo,
resaltado de opciones y consejos didácticos rotativos.
"""
from __future__ import annotations

import os
import sys
import random
import unicodedata
from typing import Callable, Any

# Asegurar codificación UTF-8 en consola de Windows con tolerancia de caracteres
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def normalize_text(text: Any) -> str:
    """Normaliza texto eliminando acentos/diacríticos y espacios para comparaciones insensibles."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt

console = Console(force_terminal=True, color_system="truecolor")

TIPS = [
    "Presiona [o] para abrir tu carpeta de cuadernos en el explorador de archivos.",
    "Puedes arrastrar los archivos de 'gemini_notebook' directamente a NotebookLM para crear podcasts de estudio.",
    "Navega por las opciones usando las flechas [▲/▼] y [Enter], o escribe el comando directamente.",
    "Escribe 'v' en cualquier submenú para retroceder sin cerrar el programa.",
    "Usa [8] institucion para alternar entre UPC, UCV, UPN y SENATI sin perder tus sesiones.",
    "El comando [2] agenda te muestra exámenes y tareas ordenados por fecha de entrega.",
    "Presiona [w] para abrir directamente el aula virtual de tu universidad en tu navegador.",
    "La sincronización inteligente solo descarga archivos nuevos, ahorrando tiempo y datos en disco.",
]


def get_random_tip() -> str:
    """Retorna un tip educativo aleatorio."""
    return random.choice(TIPS)


def setup_terminal_window(min_cols: int = 120, min_lines: int = 40):
    """
    Asegura que la ventana de la consola tenga un tamaño adecuado (por defecto 120 columnas x 40 líneas)
    para visualizar el banner completo y todas las opciones sin necesidad de scroll vertical.
    """
    if not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        return
    try:
        import shutil
        cols, lines = shutil.get_terminal_size((80, 24))
        target_cols = max(cols, min_cols)
        target_lines = max(lines, min_lines)

        # Enviar secuencia de escape ANSI para emuladores modernos (Windows Terminal, iTerm2, macOS Terminal, Linux)
        sys.stdout.write(f"\x1b[8;{target_lines};{target_cols}t")
        sys.stdout.flush()

        # En Windows conhost clásico, invocar mode con
        if sys.platform == "win32":
            os.system(f"mode con: cols={target_cols} lines={target_lines} >nul 2>&1")
    except Exception:
        pass


def read_key_event() -> tuple[str, str]:
    """
    Lee un evento de teclado de forma interactiva.
    Retorna (TIPO, VALOR):
      - ("KEY", "UP")
      - ("KEY", "DOWN")
      - ("KEY", "LEFT")
      - ("KEY", "RIGHT")
      - ("KEY", "ENTER")
      - ("KEY", "BACKSPACE")
      - ("KEY", "ESC")
      - ("CHAR", caracter)
    """
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            codes = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}
            return ("KEY", codes.get(ch2, "UNKNOWN"))
        elif ch in ("\r", "\n"):
            return ("KEY", "ENTER")
        elif ch in ("\x08", "\x7f"):
            return ("KEY", "BACKSPACE")
        elif ch == "\x1b":
            return ("KEY", "ESC")
        elif ch == "\x03":
            raise KeyboardInterrupt()
        elif ch.isprintable():
            return ("CHAR", ch)
        return ("KEY", "UNKNOWN")
    else:
        import tty
        import termios
        import select
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    ch2 = sys.stdin.read(1)
                    if ch2 in ("[", "O"):
                        ch3 = sys.stdin.read(1)
                        codes = {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}
                        return ("KEY", codes.get(ch3, "UNKNOWN"))
                return ("KEY", "ESC")
            elif ch in ("\r", "\n"):
                return ("KEY", "ENTER")
            elif ch in ("\x08", "\x7f"):
                return ("KEY", "BACKSPACE")
            elif ch == "\x03":
                raise KeyboardInterrupt()
            elif ch.isprintable():
                return ("CHAR", ch)
            return ("KEY", "UNKNOWN")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _find_match_idx(buf: str, options: list[dict], selectable_indices: list[int]) -> int | None:
    """Encuentra el índice de la opción que mejor coincide con el texto escrito (tolerante a mayúsculas, espacios y tildes)."""
    if not buf:
        return None
    b = normalize_text(buf)
    if not b:
        return None

    # 1. Coincidencia exacta de ID o key_label (ej: '1', 'o', '0', '[o]')
    for idx in selectable_indices:
        opt = options[idx]
        opt_id = normalize_text(opt.get("id", ""))
        key_lbl = normalize_text(str(opt.get("key_label", "")).strip("[] "))
        if b == opt_id or b == key_lbl:
            return idx

    # 2. Coincidencia exacta de comando, nombre, título o alias (ej: 'sync', 'abrir', 'exit')
    for idx in selectable_indices:
        opt = options[idx]
        cmd = normalize_text(opt.get("command") or opt.get("name") or opt.get("title") or "")
        aliases = [normalize_text(a) for a in opt.get("aliases", [])]
        if b == cmd or b in aliases:
            return idx

    # 3. Coincidencia por prefijo de comando, nombre, título o alias (ej: 'sy' -> 'sync', 'ag' -> 'agenda')
    for idx in selectable_indices:
        opt = options[idx]
        cmd = normalize_text(opt.get("command") or opt.get("name") or opt.get("title") or "")
        aliases = [normalize_text(a) for a in opt.get("aliases", [])]
        if cmd.startswith(b) or any(a.startswith(b) for a in aliases):
            return idx

    # 4. Coincidencia por subcadena en comando, nombre, título o alias (ej: 'algebra' -> '202402 - ALGEBRA LINEAL')
    for idx in selectable_indices:
        opt = options[idx]
        cmd = normalize_text(opt.get("command") or opt.get("name") or opt.get("title") or "")
        aliases = [normalize_text(a) for a in opt.get("aliases", [])]
        if b in cmd or any(b in a for a in aliases):
            return idx

    # 5. Coincidencia por descripción
    for idx in selectable_indices:
        opt = options[idx]
        desc = normalize_text(opt.get("desc") or opt.get("description") or "")
        if b in desc:
            return idx

    return None


def _find_match_id(buf: str, options: list[dict]) -> str | None:
    """Retorna el ID de la opción que coincide con el texto ingresado, o None."""
    selectable_indices = [i for i, opt in enumerate(options) if not opt.get("is_separator", False)]
    idx = _find_match_idx(buf, options, selectable_indices)
    if idx is not None:
        return str(options[idx]["id"])
    return None


def hybrid_select(
    options: list[dict],
    title: str = "Opciones",
    header_func: Callable | None = None,
    tip_text: str | None = None,
    default_idx: int = 0,
    allow_empty_fallback: bool = True
) -> str:
    """
    Menú selector híbrido: flechas [▲/▼] con wrap-around + barra de texto en tiempo real.
    En entornos no interactivos (pipes, CI, unittest), recurre limpiamente a Prompt.ask
    mostrando previamente la tabla de opciones.
    """
    # Si no es terminal interactiva, fallback a Prompt.ask mostrando las opciones
    if not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        if header_func:
            try:
                header_func()
            except Exception:
                pass

        table = Table(
            box=box.SIMPLE,
            show_header=False,
            padding=(0, 1),
            show_edge=False,
        )
        table.add_column("Key", style="bold bright_cyan", width=5, justify="right")
        table.add_column("Icon", width=3, justify="center")
        table.add_column("Command", style="bold white")
        table.add_column("Desc", style="dim grey70")

        for opt in options:
            if opt.get("is_separator", False):
                sep_title = opt.get("title", "")
                if sep_title:
                    table.add_row("", "", f"[dim grey42]─── {sep_title}[/dim grey42]", f"[dim grey42]{'─' * 38}[/dim grey42]")
                else:
                    table.add_row("", "", "", "")
                continue

            key_label = opt.get("key_label") or f"[{opt.get('id', '')}]"
            icon = opt.get("icon", "")
            cmd = opt.get("command") or opt.get("name") or opt.get("title") or ""
            desc = opt.get("desc") or opt.get("description") or ""
            table.add_row(key_label, icon, cmd, desc)

        panel = Panel(
            table,
            title=f"[bold white] {title} [/bold white]",
            title_align="left",
            border_style="grey37",
            box=box.ROUNDED,
            padding=(0, 1)
        )
        console.print(panel)
        if tip_text:
            console.print(f"  [bold yellow]💡 Tip:[/bold yellow] [dim white]{tip_text}[/dim white]\n")

        selectable = [opt for opt in options if not opt.get("is_separator", False)]
        default_val = None
        if 0 <= default_idx < len(selectable):
            default_val = str(selectable[default_idx].get("id", ""))

        if default_val is not None:
            return Prompt.ask(f"\n{title}", default=default_val).strip().lower()
        return Prompt.ask(f"\n{title}").strip().lower()

    selectable_indices = [i for i, opt in enumerate(options) if not opt.get("is_separator", False)]
    if not selectable_indices:
        return ""

    curr_pos = max(0, min(default_idx, len(selectable_indices) - 1))
    current_idx = selectable_indices[curr_pos]
    buffer = ""

    def _render():
        if header_func is not None:
            try:
                header_func()
            except Exception:
                console.clear()
        else:
            console.clear()

        table = Table(
            box=box.SIMPLE,
            show_header=False,
            padding=(0, 1),
            show_edge=False,
        )
        table.add_column("Pointer", width=2, justify="right")
        table.add_column("Key", style="bold bright_cyan", width=5, justify="right")
        table.add_column("Icon", width=3, justify="center")
        table.add_column("Command", style="bold white")
        table.add_column("Desc", style="dim grey70")

        for i, opt in enumerate(options):
            if opt.get("is_separator", False):
                sep_title = opt.get("title", "")
                if sep_title:
                    table.add_row(
                        "",
                        "",
                        "",
                        f"[dim grey42]─── {sep_title}[/dim grey42]",
                        f"[dim grey42]{'─' * 38}[/dim grey42]"
                    )
                else:
                    table.add_row("", "", "", "", "")
                continue

            is_selected = (i == current_idx)
            pointer = ">" if is_selected else " "
            key_label = opt.get("key_label") or f"[{opt.get('id', '')}]"
            icon = opt.get("icon", "")
            cmd = opt.get("command") or opt.get("name") or opt.get("title") or ""
            desc = opt.get("desc") or opt.get("description") or ""
            is_highlight = opt.get("highlight", False)

            if is_selected:
                k_styled = f"[bold bright_cyan]{key_label}[/bold bright_cyan]"
                i_styled = f"[bold]{icon}[/bold]" if icon else ""
                if is_highlight:
                    c_styled = f"[bold bright_green]{cmd}[/bold bright_green]"
                    d_styled = f"[bold bright_green]{desc}[/bold bright_green]"
                else:
                    c_styled = f"[bold bright_white]{cmd}[/bold bright_white]"
                    d_styled = f"[bold white]{desc}[/bold white]"
            else:
                k_styled = f"[dim bright_cyan]{key_label}[/dim bright_cyan]"
                i_styled = f"[dim]{icon}[/dim]" if icon else ""
                if is_highlight:
                    c_styled = f"[bright_green]{cmd}[/bright_green]"
                    d_styled = f"[dim green]{desc}[/dim green]"
                else:
                    c_styled = f"[white]{cmd}[/white]"
                    d_styled = f"[dim grey70]{desc}[/dim grey70]"

            table.add_row(pointer, k_styled, i_styled, c_styled, d_styled)

        panel = Panel(
            table,
            title=f"[bold white] {title} [/bold white]",
            title_align="left",
            border_style="grey37",
            box=box.ROUNDED,
            padding=(0, 1)
        )
        console.print(panel)

        if tip_text:
            console.print(f"  [bold yellow]💡 Tip:[/bold yellow] [dim white]{tip_text}[/dim white]")
            console.print()

        cursor_sym = "█"
        prompt_str = (
            f"  [dim cyan][▲/▼ Moverte | Enter Elegir][/dim cyan] "
            f"[dim grey50]O escribe aquí:[/dim grey50] "
            f"[bold bright_cyan]{buffer}[/bold bright_cyan]{cursor_sym}"
        )
        console.print(prompt_str, end="")

    try:
        try:
            console.show_cursor(False)
        except Exception:
            pass

        while True:
            _render()
            try:
                ev_type, ev_val = read_key_event()
            except KeyboardInterrupt:
                console.print("\n\n[dim]👋 Operación cancelada por el usuario. ¡Hasta luego![/dim]\n")
                sys.exit(0)

            if ev_type == "KEY":
                if ev_val == "UP":
                    buffer = ""
                    curr_pos = selectable_indices.index(current_idx)
                    curr_pos = (curr_pos - 1) % len(selectable_indices)
                    current_idx = selectable_indices[curr_pos]
                elif ev_val == "DOWN":
                    buffer = ""
                    curr_pos = selectable_indices.index(current_idx)
                    curr_pos = (curr_pos + 1) % len(selectable_indices)
                    current_idx = selectable_indices[curr_pos]
                elif ev_val == "ENTER":
                    if buffer.strip():
                        matched_id = _find_match_id(buffer.strip(), options)
                        if matched_id is not None:
                            return matched_id
                        return buffer.strip().lower()
                    else:
                        return str(options[current_idx]["id"])
                elif ev_val == "BACKSPACE":
                    if buffer:
                        buffer = buffer[:-1]
                        if buffer.strip():
                            m_idx = _find_match_idx(buffer.strip(), options, selectable_indices)
                            if m_idx is not None:
                                current_idx = m_idx
                elif ev_val == "ESC":
                    if buffer:
                        buffer = ""
            elif ev_type == "CHAR":
                buffer += ev_val
                m_idx = _find_match_idx(buffer.strip(), options, selectable_indices)
                if m_idx is not None:
                    current_idx = m_idx
    finally:
        try:
            console.show_cursor(True)
        except Exception:
            pass
        console.print()
