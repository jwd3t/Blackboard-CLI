"""
Pruebas unitarias y de integración para la arquitectura Multi-Institución (v3.0.0).
Valida:
1. Normalización de URLs.
2. Cambio de institución (UPC, UCV, UPN y personalizada).
3. Aislamiento de sesiones, cookies y caché de descargas por institución.
4. Retrocompatibilidad de sesiones v2.x.
5. Inyección de dependencias en UltraClient y CourseNotebookOrganizer.
6. Validación de URLs de Blackboard Learn / Ultra.
7. Verificador de versiones y releases GitHub (v3.0.0).
8. Confirmaciones unificadas en español (SpanishConfirm [s/n]).
"""
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
import unittest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    normalize_url,
    get_active_institution,
    set_active_institution,
    is_institution_configured,
    get_base_url,
    get_cookies_file,
    get_downloads_cache_file,
    get_browser_session_dir,
    validate_blackboard_url,
    parse_version_tuple,
    check_for_updates,
    VERSION,
    RELEASES_URL,
    UPDATE_CACHE_FILE,
    DEFAULT_INSTITUTIONS,
    ACTIVE_INSTITUTION_FILE,
    SESSION_DIR,
)
from ultra_client import UltraClient
from organizer import CourseNotebookOrganizer
from auth import extract_cookies_for_domain
from cli import SpanishConfirm, InvalidResponse


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

    def test_extract_cookies_for_domain(self):
        """Verifica que las cookies del dominio exacto prevalezcan sobre dominios secundarios y se excluyan servicios externos."""
        sample_cookies = [
            {"name": "JSESSIONID", "value": "WRONG_JSESSION", "domain": "alt-5eed7aa3f3eed.blackboard.com"},
            {"name": "JSESSIONID", "value": "CORRECT_JSESSION", "domain": "senati.blackboard.com"},
            {"name": "BbRouter", "value": "ALT_ROUTER", "domain": "alt-5eed7aa3f3eed.blackboard.com"},
            {"name": "BbRouter", "value": "MAIN_ROUTER", "domain": "senati.blackboard.com"},
            {"name": "XSRF-TOKEN", "value": "TOKEN_123", "domain": "senati.blackboard.com"},
            {"name": "_ga", "value": "GA_PARENT", "domain": ".blackboard.com"},
            {"name": "ESTSAUTH", "value": "MS_SECRET", "domain": "login.microsoftonline.com"},
            {"name": "SAML_COOKIE", "value": "SAML_SECRET", "domain": "senati.edu.pe"},
        ]

        extracted = extract_cookies_for_domain(sample_cookies, "https://senati.blackboard.com")

        # Dominio exacto prevalece
        self.assertEqual(extracted["BbRouter"], "MAIN_ROUTER")
        self.assertEqual(extracted["JSESSIONID"], "CORRECT_JSESSION")
        self.assertEqual(extracted["XSRF-TOKEN"], "TOKEN_123")

        # Dominio comodín / padre permitido
        self.assertEqual(extracted["_ga"], "GA_PARENT")

        # Dominios externos ignorados para Blackboard
        self.assertNotIn("ESTSAUTH", extracted)
        self.assertNotIn("SAML_COOKIE", extracted)

    def test_is_institution_configured(self):
        """Verifica que el estado de configuración inicial se detecte correctamente."""
        # Al borrar active_institution.json, no debe estar configurado
        if ACTIVE_INSTITUTION_FILE.exists():
            ACTIVE_INSTITUTION_FILE.unlink()
        self.assertFalse(is_institution_configured())

        # Al guardar una institución, debe marcarse como configurado
        set_active_institution("senati")
        self.assertTrue(is_institution_configured())
        self.assertEqual(get_active_institution()["id"], "senati")

    def test_parse_version_tuple(self):
        """Valida la conversión de strings de versión semver a tuplas numéricas."""
        self.assertEqual(parse_version_tuple("2.3.0"), (2, 3, 0))
        self.assertEqual(parse_version_tuple("v2.3.0"), (2, 3, 0))
        self.assertEqual(parse_version_tuple("v2.10.4-beta"), (2, 10, 4))
        self.assertTrue(parse_version_tuple("v2.3.1") > parse_version_tuple("v2.3.0"))
        self.assertTrue(parse_version_tuple("v2.3.0") > parse_version_tuple("v2.2.0"))
        self.assertTrue(parse_version_tuple("v3.0.0") > parse_version_tuple("v2.9.9"))

    def test_check_for_updates(self):
        """Valida la detección de nuevas versiones y el funcionamiento del archivo de caché."""
        backup_cache = None
        if UPDATE_CACHE_FILE.exists():
            backup_cache = UPDATE_CACHE_FILE.read_text(encoding="utf-8")

        try:
            # 1. Simular caché reciente con versión superior
            import time
            UPDATE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            fake_cache = {
                "checked_at": time.time(),
                "tag_name": "v2.4.0",
                "html_url": "https://github.com/jwd3t/Blackboard-CLI/releases/tag/v2.4.0"
            }
            UPDATE_CACHE_FILE.write_text(json.dumps(fake_cache), encoding="utf-8")

            res = check_for_updates("2.3.0", cache_ttl=3600)
            self.assertIsNotNone(res)
            self.assertTrue(res["has_update"])
            self.assertEqual(res["latest_version"], "v2.4.0")
            self.assertEqual(res["url"], "https://github.com/jwd3t/Blackboard-CLI/releases/tag/v2.4.0")

            # 2. Si la versión actual ya es superior a la caché
            res_up_to_date = check_for_updates("2.5.0", cache_ttl=3600)
            self.assertIsNone(res_up_to_date)
        finally:
            if backup_cache is not None:
                UPDATE_CACHE_FILE.write_text(backup_cache, encoding="utf-8")
            elif UPDATE_CACHE_FILE.exists():
                UPDATE_CACHE_FILE.unlink()

    def test_spanish_confirm(self):
        """Valida que SpanishConfirm procese entradas en español y renderice [s/n]."""
        confirm = SpanishConfirm()
        self.assertEqual(confirm.choices, ["s", "n"])

        # Entradas afirmativas
        self.assertTrue(confirm.process_response("s"))
        self.assertTrue(confirm.process_response("si"))
        self.assertTrue(confirm.process_response("sí"))
        self.assertTrue(confirm.process_response("S"))
        self.assertTrue(confirm.process_response("y"))
        self.assertTrue(confirm.process_response("yes"))

        # Entradas negativas
        self.assertFalse(confirm.process_response("n"))
        self.assertFalse(confirm.process_response("no"))
        self.assertFalse(confirm.process_response("N"))

        # Entrada inválida lanza InvalidResponse
        with self.assertRaises(InvalidResponse):
            confirm.process_response("tal vez")

        # Render de defaults
        self.assertEqual(confirm.render_default(True).plain, "(s)")
        self.assertEqual(confirm.render_default(False).plain, "(n)")


if __name__ == "__main__":
    unittest.main()
