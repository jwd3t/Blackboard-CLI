from pathlib import Path
from organizer import parse_unit_number, parse_week_number, generate_gemini_notebook

def test_regex():
    assert parse_unit_number("Unidad 1") == 1
    assert parse_unit_number("Unidad II") == 2
    assert parse_unit_number("U3") == 3
    assert parse_unit_number("Unit 4") == 4
    assert parse_unit_number("Semana 5") == None
    assert parse_unit_number("u3_semana1") == 3
    assert parse_unit_number("archivo_u1.pdf") == 1
    
    assert parse_week_number("Semana 03") == 3
    assert parse_week_number("Sem. 4") == 4
    assert parse_week_number("S05") == 5
    assert parse_week_number("Week 6") == 6
    assert parse_week_number("Unidad 1") == None
    assert parse_week_number("s1_recurso.pdf") == 1
    assert parse_week_number("archivo_s12.pdf") == 12
    print("✅ Regex tests passed")

def test_unified_copy():
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        # Create course structure
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
        
        assert "u0_s00_01_silabo.pdf" in files or "u0_s00_02_silabo.pdf" in files
        assert "u1_s01_01_diapo.pdf" in files or "u1_s01_02_diapo.pdf" in files
        assert "u1_s02_01_lectura.pdf" in files
        assert "u0_s00_01_otros.pdf" in files
        
        print("✅ Unified copy tests passed")

def test_manifest_copy():
    import tempfile
    
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
        
        import organizer
        old_output_dir = organizer.OUTPUT_DIR
        organizer.OUTPUT_DIR = base
        try:
            count = generate_gemini_notebook(course, manifest)
        finally:
            organizer.OUTPUT_DIR = old_output_dir
        
        gemini_dir = course / "gemini_notebook"
        files = [f.name for f in gemini_dir.iterdir()]
        files.sort()
        
        assert "u0_s00_01_silabo.pdf" in files
        assert "u1_s01_01_diapo.pdf" in files
        print("✅ Manifest copy tests passed")

if __name__ == "__main__":
    test_regex()
    test_unified_copy()
    test_manifest_copy()
