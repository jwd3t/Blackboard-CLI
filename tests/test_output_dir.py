"""
Pruebas unitarias para la configuración de ubicación personalizada de cuadernos
(src/config.py, src/organizer.py y cmd_carpeta en src/cli.py).
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

import config
from ultra_client import UltraClient
from organizer import CourseNotebookOrganizer


class TestCustomOutputDir(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.orig_config_file = config.OUTPUT_DIR_CONFIG_FILE
        self.orig_output_dir = config.OUTPUT_DIR
        config.OUTPUT_DIR_CONFIG_FILE = self.temp_dir / "output_dir.json"

    def tearDown(self):
        config.OUTPUT_DIR_CONFIG_FILE = self.orig_config_file
        config.OUTPUT_DIR = self.orig_output_dir
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_and_custom_persistence(self):
        self.assertEqual(config.get_output_dir(), config.DEFAULT_OUTPUT_DIR)

        custom_dest = self.temp_dir / "EscritorioTest" / "cuadernos"
        saved = config.set_output_dir(custom_dest)
        self.assertEqual(saved, custom_dest.resolve())
        self.assertTrue(custom_dest.exists())
        self.assertEqual(config.get_output_dir(), custom_dest.resolve())
        self.assertEqual(config.OUTPUT_DIR, custom_dest.resolve())

        # CourseNotebookOrganizer debe tomar la ruta dinámica automáticamente
        client = UltraClient(base_url="https://aulavirtual.upc.edu.pe")
        org = CourseNotebookOrganizer(client)
        self.assertEqual(org.output_dir, custom_dest.resolve())

        # Restaurar por defecto (sin crear carpeta default en repo si no hace falta)
        restored = config.set_output_dir(None, create_dir=False)
        self.assertEqual(restored, config.DEFAULT_OUTPUT_DIR)
        self.assertEqual(config.get_output_dir(), config.DEFAULT_OUTPUT_DIR)

    def test_clean_user_path(self):
        self.assertEqual(config.clean_user_path('"C:\\Users\\juan\\Desktop\\cuadernos"'), "C:\\Users\\juan\\Desktop\\cuadernos")
        self.assertEqual(config.clean_user_path("'/Users/juan/Desktop/cuadernos'"), "/Users/juan/Desktop/cuadernos")
        self.assertEqual(config.clean_user_path("& 'C:\\Users\\juan\\Desktop\\cuadernos'"), "C:\\Users\\juan\\Desktop\\cuadernos")
        self.assertEqual(config.clean_user_path("   D:\\Mis Cuadernos   "), "D:\\Mis Cuadernos")

    def test_detect_course_folders(self):
        root = self.temp_dir / "mi_carpeta"
        root.mkdir()
        (root / "[CC101] Algoritmos").mkdir()
        curso2 = root / "Matematicas"
        curso2.mkdir()
        (curso2 / "CUADERNO_CURSO.md").write_text("# Cuaderno", encoding="utf-8")
        (root / ".skills").mkdir()
        (root / "CarpetaVacia").mkdir()
        (root / "RESUMEN_SEMESTRE_IA.md").write_text("# Resumen", encoding="utf-8")

        detected = config.detect_course_folders(root)
        names = [p.name for p in detected]
        self.assertEqual(names, ["[CC101] Algoritmos", "Matematicas"])

    def test_cmd_carpeta_manual_and_default(self):
        import cli

        target_folder = self.temp_dir / "Escritorio" / "MisCuadernos"
        target_folder.mkdir(parents=True)
        (target_folder / "[SI400] Taller").mkdir()

        # Simular selección [3] ruta manual con comillas de arrastrar y soltar
        with patch("cli.hybrid_select", return_value="3"), \
             patch("cli.Prompt.ask", return_value=f'"{target_folder}"'), \
             patch("cli.timed_pause"), \
             patch("cli.console.print"):
            cli.cmd_carpeta()

        self.assertEqual(config.get_output_dir(), target_folder.resolve())

        # Simular selección [4] restaurar defecto
        fake_default = self.temp_dir / "default_cuadernos"
        with patch("cli.hybrid_select", return_value="4"), \
             patch.object(config, "DEFAULT_OUTPUT_DIR", fake_default), \
             patch("cli.DEFAULT_OUTPUT_DIR", fake_default), \
             patch("cli.timed_pause"), \
             patch("cli.console.print"):
            cli.cmd_carpeta()
            self.assertEqual(config.get_output_dir(), fake_default)
            self.assertFalse(config.OUTPUT_DIR_CONFIG_FILE.exists())

    def test_cmd_carpeta_desktop_preset(self):
        import cli

        fake_desktop = self.temp_dir / "FakeDesktop"
        (fake_desktop / "cuadernos" / "[MA101] Calculo").mkdir(parents=True)

        with patch("cli.get_desktop_dir", return_value=fake_desktop), \
             patch("cli.hybrid_select", return_value="1"), \
             patch("cli.timed_pause"), \
             patch("cli.console.print"):
            cli.cmd_carpeta()

        self.assertEqual(config.get_output_dir(), (fake_desktop / "cuadernos").resolve())


if __name__ == "__main__":
    unittest.main()
