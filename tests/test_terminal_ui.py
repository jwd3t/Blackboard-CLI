"""
Pruebas unitarias para el módulo de interfaz interactiva de consola (src/terminal_ui.py)
y las utilidades de apertura en el explorador de archivos (src/config.py).
"""
import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Asegurar importación de src/
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from terminal_ui import (
    read_key_event,
    hybrid_select,
    get_random_tip,
    _find_match_idx,
    _find_match_id,
    TIPS,
)
from config import open_in_file_manager


class TestTerminalUI(unittest.TestCase):
    """Pruebas unitarias del motor de eventos de teclado y menús híbridos."""

    def test_random_tip(self):
        """Verifica que se retorne un tip válido de la lista predefinida."""
        tip = get_random_tip()
        self.assertIsInstance(tip, str)
        self.assertIn(tip, TIPS)

    def test_read_key_event_logic_win32(self):
        """Valida el parsing de eventos de teclado en Windows con msvcrt."""
        with patch("sys.platform", "win32"), patch("msvcrt.getwch") as mock_getwch:
            # Flecha Arriba (\xe0 + H)
            mock_getwch.side_effect = ["\xe0", "H"]
            self.assertEqual(read_key_event(), ("KEY", "UP"))

            # Flecha Abajo (\x00 + P)
            mock_getwch.side_effect = ["\x00", "P"]
            self.assertEqual(read_key_event(), ("KEY", "DOWN"))

            # Flecha Izquierda (\xe0 + K)
            mock_getwch.side_effect = ["\xe0", "K"]
            self.assertEqual(read_key_event(), ("KEY", "LEFT"))

            # Flecha Derecha (\xe0 + M)
            mock_getwch.side_effect = ["\xe0", "M"]
            self.assertEqual(read_key_event(), ("KEY", "RIGHT"))

            # ENTER (\r y \n)
            mock_getwch.side_effect = ["\r"]
            self.assertEqual(read_key_event(), ("KEY", "ENTER"))
            mock_getwch.side_effect = ["\n"]
            self.assertEqual(read_key_event(), ("KEY", "ENTER"))

            # BACKSPACE (\x08 y \x7f)
            mock_getwch.side_effect = ["\x08"]
            self.assertEqual(read_key_event(), ("KEY", "BACKSPACE"))
            mock_getwch.side_effect = ["\x7f"]
            self.assertEqual(read_key_event(), ("KEY", "BACKSPACE"))

            # ESC (\x1b)
            mock_getwch.side_effect = ["\x1b"]
            self.assertEqual(read_key_event(), ("KEY", "ESC"))

            # Carácter regular
            mock_getwch.side_effect = ["s"]
            self.assertEqual(read_key_event(), ("CHAR", "s"))

            # Caracteres de control no imprimibles (no deben contaminar el buffer)
            mock_getwch.side_effect = ["\x01"]  # Ctrl+A
            self.assertEqual(read_key_event(), ("KEY", "UNKNOWN"))
            mock_getwch.side_effect = ["\t"]
            self.assertEqual(read_key_event(), ("KEY", "UNKNOWN"))

            # Ctrl+C (\x03)
            mock_getwch.side_effect = ["\x03"]
            with self.assertRaises(KeyboardInterrupt):
                read_key_event()

    def test_read_key_event_logic_unix(self):
        """Valida el parsing de eventos de teclado en Linux/macOS."""
        mock_tty = MagicMock()
        mock_termios = MagicMock()
        mock_select = MagicMock()

        modules_patch = {
            "tty": mock_tty,
            "termios": mock_termios,
            "select": mock_select,
        }

        with patch("sys.platform", "linux"), \
             patch.dict("sys.modules", modules_patch), \
             patch("sys.stdin.fileno", return_value=0):

            # Flecha Arriba (\x1b + [ + A)
            mock_select.select.return_value = ([True], [], [])
            with patch("sys.stdin.read", side_effect=["\x1b", "[", "A"]):
                self.assertEqual(read_key_event(), ("KEY", "UP"))

            # Flecha Arriba en modo SS3 (\x1b + O + A)
            with patch("sys.stdin.read", side_effect=["\x1b", "O", "A"]):
                self.assertEqual(read_key_event(), ("KEY", "UP"))

            # Flecha Abajo (\x1b + [ + B)
            with patch("sys.stdin.read", side_effect=["\x1b", "[", "B"]):
                self.assertEqual(read_key_event(), ("KEY", "DOWN"))

            # ENTER (\n)
            with patch("sys.stdin.read", side_effect=["\n"]):
                self.assertEqual(read_key_event(), ("KEY", "ENTER"))

            # BACKSPACE (\x7f)
            with patch("sys.stdin.read", side_effect=["\x7f"]):
                self.assertEqual(read_key_event(), ("KEY", "BACKSPACE"))

            # Ctrl+C (\x03)
            with patch("sys.stdin.read", side_effect=["\x03"]):
                with self.assertRaises(KeyboardInterrupt):
                    read_key_event()

    def test_wrap_around(self):
        """Comprueba que al subir desde la primera opción salta a la última y viceversa."""
        options = [
            {"id": "1", "command": "sync", "desc": "Sync"},
            {"id": "2", "command": "agenda", "desc": "Agenda"},
            {"is_separator": True, "title": "Separador"},
            {"id": "3", "command": "cursos", "desc": "Cursos"},
        ]

        # 1. Subir desde el inicio (idx 0) debe saltar al último elemento seleccionable (id: "3")
        with patch("sys.stdin.isatty", return_value=True), \
             patch("terminal_ui.read_key_event", side_effect=[("KEY", "UP"), ("KEY", "ENTER")]), \
             patch("terminal_ui.console.clear"), \
             patch("terminal_ui.console.print"):
            choice = hybrid_select(options, default_idx=0)
            self.assertEqual(choice, "3")

        # 2. Bajar desde el último elemento (idx 2 en seleccionables, id: "3") debe saltar al primero (id: "1")
        with patch("sys.stdin.isatty", return_value=True), \
             patch("terminal_ui.read_key_event", side_effect=[("KEY", "DOWN"), ("KEY", "ENTER")]), \
             patch("terminal_ui.console.clear"), \
             patch("terminal_ui.console.print"):
            choice = hybrid_select(options, default_idx=2)
            self.assertEqual(choice, "1")

    def test_buffer_clear_on_arrow(self):
        """Comprueba que pulsar flechas limpia el buffer de texto."""
        options = [
            {"id": "1", "command": "sync", "aliases": ["1", "sync"]},
            {"id": "2", "command": "agenda", "aliases": ["2", "agenda"]},
            {"id": "3", "command": "cursos", "aliases": ["3", "cursos"]},
        ]

        # Se escribe "sy" (selecciona sync en idx 0).
        # Luego se presiona DOWN: esto debe limpiar el buffer y avanzar a agenda (idx 1).
        # Al presionar ENTER, debe retornar "2" (agenda) y no "1" (sync).
        events = [
            ("CHAR", "s"),
            ("CHAR", "y"),
            ("KEY", "DOWN"),
            ("KEY", "ENTER")
        ]
        with patch("sys.stdin.isatty", return_value=True), \
             patch("terminal_ui.read_key_event", side_effect=events), \
             patch("terminal_ui.console.clear"), \
             patch("terminal_ui.console.print"):
            choice = hybrid_select(options, default_idx=0)
            self.assertEqual(choice, "2")

    def test_non_tty_fallback(self):
        """Comprueba que en modo no interactivo recurre a Prompt.ask() sin fallar."""
        options = [
            {"id": "1", "command": "sync"},
            {"id": "2", "command": "agenda"},
        ]

        with patch("sys.stdin.isatty", return_value=False), \
             patch("terminal_ui.Prompt.ask", return_value="sync") as mock_ask:
            choice = hybrid_select(options, title="Test Menu")
            self.assertEqual(choice, "sync")
            mock_ask.assert_called_once()

    def test_text_matching_priority(self):
        """Verifica la lógica de coincidencia por ID, comando, alias, prefijo, subcadena y diacríticos."""
        options = [
            {"id": "1", "key_label": "[1]", "command": "Cálculo Diferencial", "aliases": ["s", "sync"]},
            {"id": "o", "key_label": "[o]", "command": "abrir", "aliases": ["abrir", "open"]},
            {"id": "0", "key_label": "[0]", "command": "exit", "aliases": ["salir", "q"]},
            {"id": "2", "key_label": "[2]", "command": "202402 - ALGEBRA LINEAL", "desc": "Curso matemático"},
            {"id": "3", "key_label": "[3]", "title": "Semana 1: Introducción", "desc": "Primeras clases"},
        ]
        selectable = [0, 1, 2, 3, 4]

        # Coincidencia por ID directo
        self.assertEqual(_find_match_idx("1", options, selectable), 0)
        self.assertEqual(_find_match_idx("o", options, selectable), 1)
        self.assertEqual(_find_match_idx("0", options, selectable), 2)

        # Coincidencia por comando y normalización de tildes (calculo -> Cálculo)
        self.assertEqual(_find_match_idx("calculo", options, selectable), 0)
        self.assertEqual(_find_match_idx("abrir", options, selectable), 1)
        self.assertEqual(_find_match_idx("exit", options, selectable), 2)

        # Coincidencia por prefijo
        self.assertEqual(_find_match_idx("calc", options, selectable), 0)
        self.assertEqual(_find_match_idx("ab", options, selectable), 1)

        # Coincidencia por subcadena en comando ("algebra" dentro de "202402 - ALGEBRA LINEAL")
        self.assertEqual(_find_match_idx("algebra", options, selectable), 3)

        # Coincidencia por campo 'title'
        self.assertEqual(_find_match_idx("semana", options, selectable), 4)

        # Coincidencia por alias
        self.assertEqual(_find_match_idx("salir", options, selectable), 2)
        self.assertEqual(_find_match_idx("open", options, selectable), 1)

        # Búsqueda de ID
        self.assertEqual(_find_match_id("abrir", options), "o")
        self.assertEqual(_find_match_id("calculo", options), "1")
        self.assertEqual(_find_match_id("algebra", options), "2")
        self.assertIsNone(_find_match_id("inexistente", options))

    def test_backspace_editing(self):
        """Comprueba que backspace retrocede en el buffer y reevalúa la selección."""
        options = [
            {"id": "1", "command": "sync"},
            {"id": "2", "command": "agenda"},
        ]
        # Escribe 'a' (salta a agenda idx 1), luego backspace, luego 's' (salta a sync idx 0), luego ENTER
        events = [
            ("CHAR", "a"),
            ("KEY", "BACKSPACE"),
            ("CHAR", "s"),
            ("KEY", "ENTER")
        ]
        with patch("sys.stdin.isatty", return_value=True), \
             patch("terminal_ui.read_key_event", side_effect=events), \
             patch("terminal_ui.console.clear"), \
             patch("terminal_ui.console.print"):
            choice = hybrid_select(options, default_idx=0)
            self.assertEqual(choice, "1")

    def test_open_in_file_manager(self):
        """Comprueba la función open_in_file_manager en diferentes plataformas y con carpetas y archivos."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "subcarpeta"

            # En Windows (carpeta)
            with patch("sys.platform", "win32"), patch("os.startfile") as mock_startfile:
                ok = open_in_file_manager(test_path)
                self.assertTrue(ok)
                self.assertTrue(test_path.exists())
                mock_startfile.assert_called_once_with(str(test_path.resolve()))

            # En Windows (archivo existente)
            test_file = Path(tmp_dir) / "archivo.txt"
            test_file.write_text("dummy", encoding="utf-8")
            with patch("sys.platform", "win32"), patch("os.startfile") as mock_startfile:
                ok = open_in_file_manager(test_file)
                self.assertTrue(ok)
                mock_startfile.assert_called_with(str(test_file.resolve()))

            # En macOS
            with patch("sys.platform", "darwin"), patch("subprocess.run") as mock_run:
                ok = open_in_file_manager(test_path)
                self.assertTrue(ok)
                mock_run.assert_called_once_with(["open", str(test_path.resolve())], check=True)

            # En Linux
            with patch("sys.platform", "linux"), patch("subprocess.run") as mock_run:
                ok = open_in_file_manager(test_path)
                self.assertTrue(ok)
                mock_run.assert_called_once_with(["xdg-open", str(test_path.resolve())], check=True)

            # Error o excepción del sistema
            with patch("sys.platform", "win32"), patch("os.startfile", side_effect=OSError("Access denied")):
                ok = open_in_file_manager(test_path)
                self.assertFalse(ok)

    def test_cmd_institution_resilience(self):
        """Valida que cmd_institution maneje alias para UCV, SENATI y entradas no válidas sin crashear."""
        from cli import cmd_institution

        # 1. Selección por alias 'ucv'
        with patch("sys.stdin.isatty", return_value=False), \
             patch("rich.prompt.Prompt.ask", return_value="ucv"), \
             patch("cli.verify_session", return_value={"userName": "alumno_ucv"}), \
             patch("cli.set_active_institution") as mock_set:
            mock_set.return_value = {"id": "ucv", "name": "UCV", "base_url": "https://ucv.blackboard.com"}
            cmd_institution()
            mock_set.assert_called_with("ucv")

        # 2. Selección por alias 'senati'
        with patch("sys.stdin.isatty", return_value=False), \
             patch("rich.prompt.Prompt.ask", return_value="senati"), \
             patch("cli.verify_session", return_value={"userName": "alumno_senati"}), \
             patch("cli.set_active_institution") as mock_set:
            mock_set.return_value = {"id": "senati", "name": "SENATI", "base_url": "https://senati.blackboard.com"}
            cmd_institution()
            mock_set.assert_called_with("senati")

        # 3. Opción inválida no debe crashear con AttributeError en new_inst.get()
        with patch("sys.stdin.isatty", return_value=False), \
             patch("rich.prompt.Prompt.ask", return_value="opcion_invalida"), \
             patch("cli.verify_session", return_value=None):
            # No debe lanzar excepción
            cmd_institution()


if __name__ == "__main__":
    unittest.main()
