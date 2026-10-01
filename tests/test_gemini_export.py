import sys
import unittest
import tempfile
import shutil
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import organizer
from organizer import (
    parse_unit_number,
    parse_week_number,
    generate_gemini_notebook,
    convert_to_markdown_anydoc,
    convert_course_materials_to_markdown,
    generate_course_skill,
    generate_semester_skill,
)


class TestGeminiExportAndAnyDoc(unittest.TestCase):
    def test_regex(self):
        self.assertEqual(parse_unit_number("Unidad 1"), 1)
        self.assertEqual(parse_unit_number("Unidad II"), 2)
        self.assertEqual(parse_unit_number("U3"), 3)
        self.assertEqual(parse_unit_number("Unit 4"), 4)
        self.assertIsNone(parse_unit_number("Semana 5"))
        self.assertEqual(parse_unit_number("u3_semana1"), 3)
        self.assertEqual(parse_unit_number("archivo_u1.pdf"), 1)
        
        self.assertEqual(parse_week_number("Semana 03"), 3)
        self.assertEqual(parse_week_number("Sem. 4"), 4)
        self.assertEqual(parse_week_number("S05"), 5)
        self.assertEqual(parse_week_number("Week 6"), 6)
        self.assertIsNone(parse_week_number("Unidad 1"))
        self.assertEqual(parse_week_number("s1_recurso.pdf"), 1)
        self.assertEqual(parse_week_number("archivo_s12.pdf"), 12)

    def test_unified_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            course = base / "[CS101] Test Course"
            course.mkdir()
            
            info_dir = course / "00_INFORMACION_GENERAL"
            info_dir.mkdir()
            (info_dir / "silabo.pdf").write_text("dummy")
            (info_dir / "plan_calendario.pdf").write_text("dummy")
            
            mat_dir = course / "02_MATERIALES_Y_CLASES"
            mat_dir.mkdir()
            
            w1_dir = mat_dir / "Unidad 1" / "Semana 01"
            w1_dir.mkdir(parents=True)
            (w1_dir / "diapo.pdf").write_text("dummy")
            (w1_dir / "guia.docx").write_text("dummy")
            
            w2_dir = mat_dir / "Unidad 1" / "Semana 02"
            w2_dir.mkdir(parents=True)
            (w2_dir / "lectura.pdf").write_text("dummy")
            
            w3_dir = mat_dir / "Sin unidad ni semana"
            w3_dir.mkdir(parents=True)
            (w3_dir / "otros.pdf").write_text("dummy")

            # Run generator
            count = generate_gemini_notebook(course)
            
            gemini_dir = course / "gemini_notebook"
            files = [f.name for f in gemini_dir.iterdir()]
            files.sort()
            
            self.assertTrue("u0_s00_01_silabo.pdf" in files or "u0_s00_02_silabo.pdf" in files)
            self.assertTrue("u1_s01_01_diapo.pdf" in files or "u1_s01_02_diapo.pdf" in files)
            self.assertIn("u1_s02_01_lectura.pdf", files)
            self.assertIn("u0_s00_01_otros.pdf", files)
            self.assertIn("SKILL.md", files)

    def test_manifest_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            course = base / "[CS102] Manifest Course"
            course.mkdir()
            
            info_dir = course / "00_INFORMACION_GENERAL"
            info_dir.mkdir()
            f1 = info_dir / "silabo.pdf"
            f1.write_text("dummy")
            
            mat_dir = course / "02_MATERIALES_Y_CLASES"
            mat_dir.mkdir()
            f2 = mat_dir / "diapo.pdf"
            f2.write_text("dummy")
            
            manifest = [
                {"local_path": f1, "original_name": "silabo.pdf", "unit": 0, "week": 0, "is_info_general": True},
                {"local_path": f2, "original_name": "diapo.pdf", "unit": 1, "week": 1, "is_info_general": False},
            ]
            
            old_output_dir = organizer.OUTPUT_DIR
            organizer.OUTPUT_DIR = base
            try:
                count = generate_gemini_notebook(course, manifest)
            finally:
                organizer.OUTPUT_DIR = old_output_dir
            
            gemini_dir = course / "gemini_notebook"
            files = [f.name for f in gemini_dir.iterdir()]
            files.sort()
            
            self.assertIn("u0_s00_01_silabo.pdf", files)
            self.assertIn("u1_s01_01_diapo.pdf", files)
            self.assertIn("SKILL.md", files)

    def test_anydoc_conversion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Valid CSV file
            csv_file = base / "tabla_notas.csv"
            csv_file.write_text("Alumno,Nota1,Nota2\nJuan,18,20\nPedro,15,16", encoding="utf-8")
            
            md_file = convert_to_markdown_anydoc(csv_file)
            self.assertIsNotNone(md_file)
            self.assertTrue(md_file.exists())
            self.assertEqual(md_file.name, "tabla_notas.md")
            
            content = md_file.read_text(encoding="utf-8")
            self.assertIn("AnyDoc", content)
            self.assertIn("| Alumno | Nota1 | Nota2 |", content)
            self.assertIn("| Juan | 18 | 20 |", content)

            # Test corrupt fallback (does not crash)
            corrupt = base / "danado.docx"
            corrupt.write_text("not a real zip or docx")
            res = convert_to_markdown_anydoc(corrupt)
            self.assertIsNone(res)

    def test_course_skill_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            course_dir = Path(tmpdir) / "[CC101] Algoritmos y Estructuras"
            course_dir.mkdir()
            
            skill_path = generate_course_skill(
                course_dir=course_dir,
                course={"name": "Algoritmos y Estructuras", "course_id": "CC101"}
            )
            self.assertTrue(skill_path.exists())
            self.assertEqual(skill_path.name, "SKILL.md")
            
            sub_skill = course_dir / ".skills" / "estudio-curso" / "SKILL.md"
            self.assertTrue(sub_skill.exists())
            
            content = skill_path.read_text(encoding="utf-8")
            self.assertIn("name: estudio-cc101", content)
            self.assertIn("AnyDoc", content)
            self.assertIn("00_INFORMACION_GENERAL", content)
            self.assertIn("01_EVALUACIONES_Y_EXAMENES", content)

    def test_semester_skill_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            courses = [{"name": "Redes", "course_id": "RD101"}]
            evals = [{"title": "PC1", "due_date": "2026-10-15", "course_name": "Redes"}]
            
            skill_path = generate_semester_skill(out_dir, courses, evals)
            self.assertTrue(skill_path.exists())
            self.assertEqual(skill_path.name, "SKILL.md")
            
            sub_skill = out_dir / ".skills" / "estudio-semestre" / "SKILL.md"
            self.assertTrue(sub_skill.exists())
            
            content = skill_path.read_text(encoding="utf-8")
            self.assertIn("name: estudio-semestre", content)
            self.assertIn("RESUMEN_SEMESTRE_IA.md", content)

    def test_gemini_notebook_with_anydoc_companion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            course = base / "[MA101] Calculo I"
            course.mkdir()
            
            mat_dir = course / "02_MATERIALES_Y_CLASES" / "Unidad 1" / "Semana 01"
            mat_dir.mkdir(parents=True)
            
            csv_file = mat_dir / "datos_limites.csv"
            csv_file.write_text("x,f(x)\n0,1\n1,2", encoding="utf-8")
            
            # Run convert_course_materials_to_markdown
            converted = convert_course_materials_to_markdown(course)
            self.assertEqual(converted, 1)
            self.assertTrue((mat_dir / "datos_limites.md").exists())
            
            # Now run generate_gemini_notebook
            count = generate_gemini_notebook(course)
            # Should have both csv and md in gemini_notebook
            gemini_dir = course / "gemini_notebook"
            files = [f.name for f in gemini_dir.iterdir()]
            
            self.assertIn("u1_s01_01_datos_limites.csv", files)
            self.assertIn("u1_s01_01_datos_limites.md", files)
            self.assertIn("SKILL.md", files)


if __name__ == "__main__":
    unittest.main()
