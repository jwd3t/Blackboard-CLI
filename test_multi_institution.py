"""
Pruebas unitarias y de integración para la arquitectura Multi-Institución (v3.0.0).
Valida:
1. Normalización de URLs.
2. Cambio de institución (UPC, UCV, UPN y personalizada).
3. Aislamiento de sesiones, cookies y caché de descargas por institución.
4. Retrocompatibilidad de sesiones v2.x.
5. Inyección de dependencias en UltraClient y CourseNotebookOrganizer.
6. Validación de URLs de Blackboard Learn / Ultra.
"""
import os
import json
import shutil
import tempfile
from pathlib import Path
import unittest

from config import (
    normalize_url,
    get_active_institution,
    set_active_institution,
    get_base_url,
    get_cookies_file,
    get_downloads_cache_file,
    get_browser_session_dir,
    validate_blackboard_url,
    DEFAULT_INSTITUTIONS,
    ACTIVE_INSTITUTION_FILE,
    SESSION_DIR,
)
from ultra_client import UltraClient
from organizer import CourseNotebookOrganizer


class TestMultiInstitution(unittest.TestCase):
    def setUp(self):
        # Guardar estado previo de active_institution si existía
        self.temp_dir = tempfile.mkdtemp()
        self.original_active_content = None
        if ACTIVE_INSTITUTION_FILE.exists():
            self.original_active_content = ACTIVE_INSTITUTION_FILE.read_text(encoding="utf-8")

    def tearDown(self):
        # Restaurar estado previo
        if self.original_active_content is not None:
            ACTIVE_INSTITUTION_FILE.write_text(self.original_active_content, encoding="utf-8")
        elif ACTIVE_INSTITUTION_FILE.exists():
            ACTIVE_INSTITUTION_FILE.unlink()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_normalize_url(self):
        """Prueba la limpieza y estandarización de URLs de Blackboard."""
        self.assertEqual(normalize_url("ucv.blackboard.com"), "https://ucv.blackboard.com")
        self.assertEqual(normalize_url("https://ucv.blackboard.com/"), "https://ucv.blackboard.com")
        self.assertEqual(normalize_url("http://bb.ejemplo.edu.pe/"), "http://bb.ejemplo.edu.pe")
        self.assertEqual(normalize_url("  aulavirtual.upc.edu.pe  "), "https://aulavirtual.upc.edu.pe")
        self.assertEqual(normalize_url(""), "")

        # Atajos de SENATI
        self.assertEqual(normalize_url("senati"), "https://senati.blackboard.com")
        self.assertEqual(normalize_url("senati.pe"), "https://senati.blackboard.com")
        self.assertEqual(normalize_url("senati.edu.pe"), "https://senati.blackboard.com")
        self.assertEqual(normalize_url("aulavirtual.senati.edu.pe"), "https://senati.blackboard.com")

    def test_set_active_institution_predefined(self):
        """Verifica el cambio a instituciones predefinidas (UPC, UCV, UPN, SENATI)."""
        # SENATI
        inst_senati = set_active_institution("senati")
        self.assertEqual(inst_senati["id"], "senati")
        self.assertEqual(inst_senati["base_url"], "https://senati.blackboard.com")
        self.assertEqual(get_base_url(), "https://senati.blackboard.com")
        self.assertTrue(get_cookies_file().name.endswith("cookies_senati.json"))
        self.assertTrue(get_downloads_cache_file().name.endswith("downloads_cache_senati.json"))
        self.assertTrue(get_browser_session_dir().name.endswith("browser_senati"))

        # UCV
        inst_ucv = set_active_institution("ucv")
        self.assertEqual(inst_ucv["id"], "ucv")
        self.assertEqual(inst_ucv["base_url"], "https://ucv.blackboard.com")
        self.assertEqual(get_base_url(), "https://ucv.blackboard.com")
        self.assertTrue(get_cookies_file().name.endswith("cookies_ucv.json"))
        self.assertTrue(get_downloads_cache_file().name.endswith("downloads_cache_ucv.json"))
        self.assertTrue(get_browser_session_dir().name.endswith("browser_ucv"))

        # UPN
        inst_upn = set_active_institution("upn")
        self.assertEqual(inst_upn["id"], "upn")
        self.assertEqual(inst_upn["base_url"], "https://upn.blackboard.com")
        self.assertEqual(get_base_url(), "https://upn.blackboard.com")
        self.assertTrue(get_cookies_file().name.endswith("cookies_upn.json"))

        # UPC
        inst_upc = set_active_institution("upc")
        self.assertEqual(inst_upc["id"], "upc")
        self.assertEqual(inst_upc["base_url"], "https://aulavirtual.upc.edu.pe")
        self.assertEqual(get_base_url(), "https://aulavirtual.upc.edu.pe")

    def test_set_active_institution_custom(self):
        """Verifica la configuración de una institución personalizada genérica."""
        custom_url = "https://blackboard.udep.edu.pe"
        inst_custom = set_active_institution("custom", custom_url=custom_url, custom_name="UDEP")
        self.assertEqual(inst_custom["id"], "custom")
        self.assertEqual(inst_custom["name"], "UDEP")
        self.assertEqual(inst_custom["short_name"], "UDEP")
        self.assertEqual(inst_custom["base_url"], "https://blackboard.udep.edu.pe")
        self.assertEqual(get_base_url(), "https://blackboard.udep.edu.pe")
        self.assertTrue(get_cookies_file().name.endswith("cookies_custom.json"))
        self.assertTrue(get_downloads_cache_file().name.endswith("downloads_cache_custom.json"))

    def test_legacy_retrocompatibility(self):
        """Verifica que las cookies y caché v2.x (cookies.json) sigan reconociéndose para UPC."""
        legacy_cookies = SESSION_DIR / "cookies.json"
        inst_cookies = SESSION_DIR / "cookies_upc.json"

        # Simular sesión v2 previa
        set_active_institution("upc")
        try:
            legacy_cookies.write_text('[{"name": "test_cookie", "value": "123"}]', encoding="utf-8")
            if inst_cookies.exists():
                inst_cookies.unlink()

            resolved_file = get_cookies_file()
            self.assertEqual(resolved_file.name, "cookies.json")
        finally:
            if legacy_cookies.exists():
                legacy_cookies.unlink()

    def test_session_isolation(self):
        """Verifica que cada universidad use archivos de sesión separados sin colisiones."""
        # UPC
        set_active_institution("upc")
        cookies_upc = get_cookies_file()

        # UCV
        set_active_institution("ucv")
        cookies_ucv = get_cookies_file()

        # SENATI
        set_active_institution("senati")
        cookies_senati = get_cookies_file()

        # UPN
        set_active_institution("upn")
        cookies_upn = get_cookies_file()

        self.assertNotEqual(cookies_upc, cookies_ucv)
        self.assertNotEqual(cookies_ucv, cookies_senati)
        self.assertNotEqual(cookies_senati, cookies_upn)
        self.assertNotEqual(cookies_upc, cookies_senati)

    def test_ultra_client_dependency_injection(self):
        """Verifica que UltraClient acepte base_url y cache_file inyectados."""
        custom_base = "https://senati.blackboard.com"
        temp_cache = Path(self.temp_dir) / "test_cache.json"

        client = UltraClient(base_url=custom_base, cache_file=temp_cache)
        self.assertEqual(client.base_url, custom_base)
        self.assertEqual(client.cache_file, temp_cache)

        # Probar guardado y lectura de caché
        client.downloads_cache["https://ejemplo.com/recurso"] = "recurso.pdf"
        client._save_cache()
        self.assertTrue(temp_cache.exists())

        new_client = UltraClient(base_url=custom_base, cache_file=temp_cache)
        self.assertEqual(new_client.downloads_cache.get("https://ejemplo.com/recurso"), "recurso.pdf")

    def test_organizer_output_dir_injection(self):
        """Verifica que CourseNotebookOrganizer permita un output_dir personalizado."""
        temp_output = Path(self.temp_dir) / "mis_cuadernos"
        client = UltraClient(base_url="https://senati.blackboard.com")
        organizer = CourseNotebookOrganizer(client, output_dir=temp_output)

        self.assertEqual(organizer.output_dir, temp_output)
        self.assertTrue(temp_output.exists())

    def test_validate_blackboard_url(self):
        """Verifica el validador de endpoints de Blackboard Learn Ultra."""
        # 1. SENATI (servidor oficial verificado)
        is_valid_senati, msg_senati = validate_blackboard_url("https://senati.blackboard.com")
        self.assertTrue(is_valid_senati, f"SENATI debería ser válida: {msg_senati}")
        self.assertIn("Blackboard", msg_senati)

        # 2. UCV (servidor real verificado)
        is_valid, msg = validate_blackboard_url("https://ucv.blackboard.com")
        self.assertTrue(is_valid, f"UCV debería ser válida: {msg}")
        self.assertIn("Blackboard", msg)

        # 3. Servidor inexistente / inválido
        is_invalid, err_msg = validate_blackboard_url("https://esta-url-no-existe-12345.com", timeout=2.0)
        self.assertFalse(is_invalid)


if __name__ == "__main__":
    unittest.main()
