"""
Módulo organizador de "Cuadernos de Curso".
Estructura automáticamente la información dispersa de Blackboard Ultra
en carpetas limpias y genera archivos Markdown optimizados para el estudiante y la IA.
"""
from __future__ import annotations

import re
import html
import json
import shutil
import urllib.parse
from pathlib import Path
from datetime import datetime
from dateutil import parser as date_parser

from config import (
    OUTPUT_DIR,
    DIR_INFO_GENERAL,
    DIR_EVALUACIONES,
    DIR_MATERIALES,
    DIR_ANUNCIOS,
    DIR_GEMINI_NOTEBOOK,
    KEYWORDS_INFO_GENERAL,
    SUPPORTED_EXTENSIONS,
    ANYDOC_SUPPORTED_EXTENSIONS,
)
from ultra_client import UltraClient


def parse_unit_number(text: str) -> int | None:
    """Detecta números de unidad arábigos y romanos."""
    match = re.search(r'(?i)(?<![a-zA-Z])(?:unidad|unit|u)\s*([0-9]+|[IVXLCDM]+)(?![a-zA-Z0-9])', text)
    if not match:
        return None
    val = match.group(1).upper()
    if val.isdigit():
        return int(val)
    romans = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}
    return romans.get(val)


def parse_week_number(text: str) -> int | None:
    """Detecta semanas."""
    match = re.search(r'(?i)(?<![a-zA-Z])(?:semana|sem\.?|s|week)\s*([0-9]+)(?![a-zA-Z0-9])', text)
    if match:
        return int(match.group(1))
    return None


def convert_to_markdown_anydoc(file_path: Path, force: bool = False) -> Path | None:
    """
    Convierte un documento soportado (.pdf, .docx, .pptx, etc.) a Markdown limpio usando AnyDoc.
    Guarda el archivo .md en el mismo directorio que el archivo original para que convivan juntos.
    Retorna la ruta al archivo .md generado o existente, o None si no aplica o falla.
    """
    if not file_path.is_file() or file_path.stat().st_size == 0:
        return None

    ext = file_path.suffix.lower()
    if ext not in ANYDOC_SUPPORTED_EXTENSIONS or ext == ".md":
        return None

    target_md = file_path.with_suffix(".md")
    if target_md.exists() and target_md.stat().st_size > 0 and not force:
        return target_md

    try:
        import anydoc
        md_text = anydoc.to_markdown(str(file_path))
        if not md_text or not md_text.strip():
            return None

        header = (
            f"<!-- Documento convertido automáticamente a Markdown vía AnyDoc -->\n"
            f"<!-- Archivo original: {file_path.name} -->\n\n"
        )
        target_md.write_text(header + md_text.strip() + "\n", encoding="utf-8")
        return target_md
    except Exception:
        # Fallback silencioso ante archivos corruptos, PDFs escaneados o formatos incompatibles
        return None


def convert_course_materials_to_markdown(course_dir: Path, progress_callback=None) -> int:
    """
    Recorre los materiales y documentos de información general del curso y
    convierte todos los archivos soportados a Markdown con AnyDoc.
    """
    converted = 0
    dirs_to_check = [course_dir / DIR_INFO_GENERAL, course_dir / DIR_MATERIALES]
    for d in dirs_to_check:
        if not d.exists():
            continue
        for file in sorted(d.rglob("*")):
            if file.is_file() and file.suffix.lower() in ANYDOC_SUPPORTED_EXTENSIONS and file.suffix.lower() != ".md":
                md_path = convert_to_markdown_anydoc(file)
                if md_path and md_path.exists():
                    converted += 1
                    if progress_callback:
                        progress_callback("log", f"  📄 [dim green]Convertido a Markdown:[/dim green] [dim]{md_path.name}[/dim]")
    return converted


def generate_course_skill(
    course_dir: Path,
    course: dict | None = None,
    evaluations: list[dict] | None = None,
    announcements: list[dict] | None = None,
) -> Path:
    """
    Genera el archivo de skill para agentes de IA (SKILL.md y .skills/estudio-curso/SKILL.md)
    dentro del cuaderno del curso, instruyendo a modelos de IA sobre cómo navegar los materiales,
    priorizar archivos Markdown (.md generados con AnyDoc) y resolver consultas académicas.
    """
    if course:
        name = course.get("name", course_dir.name)
        code = course.get("course_id", "")
    else:
        m = re.match(r"^\[(.*?)\]\s*(.*)$", course_dir.name)
        if m:
            code = m.group(1).strip()
            name = m.group(2).strip()
        else:
            code = ""
            name = course_dir.name

    slug_raw = (code or name).lower()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug_raw).strip("-")
    skill_name = f"estudio-{slug}" if slug else "estudio-curso"

    lines = [
        "---",
        f"name: {skill_name}",
        f"description: \"Guía de estudio inteligente y navegación para el curso {name} ({code}). Instrucciones para priorizar documentos Markdown convertidos con AnyDoc, consultar temarios de exámenes y navegar clases.\"",
        "---",
        "",
        f"# 🎓 Skill de Asistente de Estudio: {name}" + (f" ({code})" if code else ""),
        "",
        "Esta skill proporciona las directivas y pautas de navegación para cualquier agente de inteligencia artificial (Antigravity, Claude, ChatGPT, Gemini, Cursor) que asista al estudiante en este curso.",
        "",
        "---",
        "",
        "## ⚡ Regla de Oro: Prioridad de Archivos Markdown (AnyDoc)",
        "",
        "Todos los documentos del curso (`.docx`, `.pptx`, `.pdf`, `.xlsx`, etc.) han sido procesados y convertidos automáticamente a **Markdown (.md)** mediante el motor AnyDoc, conviviendo lado a lado con sus archivos originales.",
        "",
        "1. **Lectura Inteligente y Ahorro de Tokens**:",
        "   - **SIEMPRE lee prioritariamente los archivos `.md` complementarios** antes de abrir un archivo binario o PDF.",
        "   - Los archivos `.md` contienen texto limpio, tablas CommonMark y la estructura jerárquica del contenido consumiendo hasta un **90% menos de tokens** de ventana de contexto.",
        "2. **Coexistencia con Archivos Originales**:",
        "   - Cada archivo fuente (por ejemplo `Semana 02/diapositivas.pptx`) cuenta con su gemelo `Semana 02/diapositivas.md` en la misma ruta.",
        "   - Si el usuario te pide un enlace directo, descargar el archivo original o inspeccionar diagramas visuales muy complejos, referencia la ruta del archivo original (`.pptx`, `.pdf`, etc.). Para explicaciones, resúmenes, fórmulas y resolución de dudas, usa el archivo `.md`.",
        "",
        "---",
        "",
        "## 📂 Arquitectura del Cuaderno de Estudio",
        "",
        "El curso está organizado de forma estandarizada y predecible:",
        "",
        f"- 📁 `{DIR_INFO_GENERAL}/`: Sílabo oficial, plan calendario y sistema de evaluación (fórmulas de notas, pesos de PCs, parcial y final).",
        f"- 📅 `{DIR_EVALUACIONES}/agenda_evaluaciones.md`: Calendario cronológico de todas las entregas, tareas, prácticas y exámenes parciales/finales con las rúbricas y temarios de qué entra en cada prueba.",
        f"- 📚 `{DIR_MATERIALES}/`: Organización jerárquica (`Unidad X › Semana YY`). Diapositivas de clase, guías de laboratorio y lecturas complementarias con sus archivos `.md` correspondientes.",
        f"- 📢 `{DIR_ANUNCIOS}/historial_anuncios.md`: Comunicados oficiales del profesor, cambios de fecha y recordatorios emitidos en el aula virtual.",
        f"- 🤖 `{DIR_GEMINI_NOTEBOOK}/`: Carpeta plana unificada con nomenclatura `u{{unidad}}_s{{semana}}_{{idx}}_{{nombre}}` tanto para archivos originales como para sus equivalentes `.md`, lista para ser cargada en Google NotebookLM o entornos Gemini.",
        "",
        "---",
        "",
        "## 🛠️ Flujos de Trabajo para el Asistente IA",
        "",
        "### 1. ¿Qué entra en el próximo examen / evaluación?",
        f"1. Consulta primero `{DIR_EVALUACIONES}/agenda_evaluaciones.md` para identificar la fecha límite, tipo de evaluación y las instrucciones registradas por el profesor.",
        f"2. Identifica las semanas correspondientes en `{DIR_MATERIALES}/` que comprende dicha evaluación.",
        "3. Lee los archivos `.md` de esas semanas para extraer los temas centrales y preparar simulacros de preguntas, resúmenes de conceptos y fórmulas clave.",
        "",
        "### 2. Dudas sobre una clase o semana en específico",
        f"1. Dirígete directamente a la carpeta de la semana en `{DIR_MATERIALES}/` (o al prefijo `uX_sXX_...` en `{DIR_GEMINI_NOTEBOOK}/`).",
        "2. Abre y analiza los archivos `.md` asociados a las diapositivas o guías.",
        "3. Responde al estudiante con explicaciones paso a paso basadas en la teoría oficial del curso.",
        "",
        "### 3. Fórmulas de calificación y promedios",
        f"1. Revisa `{DIR_INFO_GENERAL}/` (especialmente el sílabo en `.md`).",
        "2. Explica la fórmula de nota final y qué nota mínima necesita el estudiante según su rendimiento.",
        "",
        "### 4. Generación de Flashcards y Cuestionarios",
        f"Utiliza la información consolidada en los archivos `.md` de `{DIR_MATERIALES}/` para generar flashcards en formato Q&A o preguntas de opción múltiple con justificación detallada de cada alternativa.",
        "",
        "### 5. Conversión de Nuevos Archivos con AnyDoc en Tiempo Real",
        "Si el estudiante añade un archivo nuevo (`.docx`, `.pptx`, `.pdf`, `.xlsx`, `.csv`) que aún no tenga su gemelo `.md`, puedes convertirlo directamente en el entorno con AnyDoc:",
        "```python",
        "import anydoc",
        "from pathlib import Path",
        "doc = Path('ruta/al/documento.docx')",
        "doc.with_suffix('.md').write_text(anydoc.to_markdown(str(doc)), encoding='utf-8')",
        "```",
        ""
    ]

    skill_content = "\n".join(lines)

    # 1. En la raíz del curso
    skill_path = course_dir / "SKILL.md"
    try:
        skill_path.write_text(skill_content, encoding="utf-8")
    except Exception:
        pass

    # 2. En .skills/estudio-curso/SKILL.md (estándar para herramientas que buscan en .skills/)
    sub_skill_dir = course_dir / ".skills" / "estudio-curso"
    try:
        sub_skill_dir.mkdir(parents=True, exist_ok=True)
        (sub_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")
    except Exception:
        pass

    # 3. Limpiar SKILL.md de gemini_notebook si existía de versiones previas
    gemini_dir = course_dir / DIR_GEMINI_NOTEBOOK
    if gemini_dir.exists():
        skill_in_gemini = gemini_dir / "SKILL.md"
        if skill_in_gemini.exists():
            try:
                skill_in_gemini.unlink()
            except Exception:
                pass

    return skill_path


def generate_semester_skill(
    output_dir: Path,
    courses: list[dict],
    all_evaluations: list[dict],
) -> Path:
    """
    Genera el archivo SKILL.md y .skills/estudio-semestre/SKILL.md a nivel de la carpeta general
    de cuadernos, permitiendo que la IA comprenda el panorama global del ciclo académico.
    """
    lines = [
        "---",
        "name: estudio-semestre",
        "description: \"Guía de estudio transversal para el semestre universitario. Monitorea fechas de exámenes entre todos los cursos y coordina la navegación de cuadernos convertidos con AnyDoc.\"",
        "---",
        "",
        "# 🎓 Skill Maestra de Semestre: Panorama Global e Inteligencia de Estudio",
        "",
        "Esta skill instruye a cualquier agente de inteligencia artificial sobre cómo asistir al estudiante en la totalidad de sus asignaturas matriculadas durante el semestre académico actual.",
        "",
        "---",
        "",
        "## 🧭 Navegación Global",
        "- **Resumen Semestral**: Consulta `RESUMEN_SEMESTRE_IA.md` para ver el consolidado de cursos matriculados y el calendario unificado de exámenes.",
        "- **Cuadernos Individuales**: Cada curso cuenta con su propia carpeta estructurada (`[CODIGO] Nombre del Curso`), conteniendo:",
        "  - Su propio `SKILL.md` con las instrucciones específicas de la asignatura.",
        "  - `CUADERNO_CURSO.md` con los enlaces directos y portada.",
        f"  - `{DIR_INFO_GENERAL}/` (Sílabos y fórmulas).",
        f"  - `{DIR_EVALUACIONES}/agenda_evaluaciones.md` (Fechas y temarios).",
        f"  - `{DIR_MATERIALES}/` (Clases semanales con archivos originales y sus versiones `.md` por AnyDoc).",
        f"  - `{DIR_ANUNCIOS}/historial_anuncios.md` (Avisos del profesor).",
        f"  - `{DIR_GEMINI_NOTEBOOK}/` (Carpeta plana unificada para Google NotebookLM).",
        "",
        "## ⚡ Prioridad AnyDoc en Todos los Cursos",
        "- En cada curso, los documentos (`.docx`, `.pptx`, `.pdf`, etc.) coexisten con sus versiones `.md` generadas con AnyDoc.",
        "- **Lee prioritariamente los archivos `.md`** para ahorrar ventana de contexto y procesar la información de forma inmediata.",
        "- Si el estudiante agrega nuevos documentos no convertidos, puedes usar AnyDoc en Python: `import anydoc; anydoc.to_markdown('archivo')`.",
        ""
    ]

    skill_content = "\n".join(lines)
    skill_path = output_dir / "SKILL.md"
    try:
        skill_path.write_text(skill_content, encoding="utf-8")
    except Exception:
        pass

    sub_skill_dir = output_dir / ".skills" / "estudio-semestre"
    try:
        sub_skill_dir.mkdir(parents=True, exist_ok=True)
        (sub_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")
    except Exception:
        pass

    return skill_path


def is_anydoc_companion_markdown(path: Path) -> bool:
    """
    Determina si un archivo .md es una versión complementaria generada por AnyDoc
    a partir de un archivo binario existente, o si es un archivo de sistema/skill/agenda.
    Retorna False únicamente si es un documento de texto/lectura nativo de Blackboard.
    """
    if path.suffix.lower() != ".md":
        return False

    name_upper = path.name.upper()
    if name_upper in [
        "SKILL.MD",
        "AGENDA_EVALUACIONES.MD",
        "HISTORIAL_ANUNCIOS.MD",
        "CUADERNO_CURSO.MD",
        "RESUMEN_SEMESTRE_IA.MD",
    ]:
        return True

    # 1. Si existe un archivo original con el mismo nombre y extensión binaria en el mismo directorio
    for ext in ANYDOC_SUPPORTED_EXTENSIONS:
        if ext != ".md" and path.with_suffix(ext).exists():
            return True

    # 2. Si contiene el encabezado característico de conversión AnyDoc
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            first_lines = "".join(f.readline() for _ in range(3))
            if "AnyDoc" in first_lines or "Documento convertido" in first_lines:
                return True
    except Exception:
        pass

    return False


def generate_gemini_notebook(course_dir: Path, manifest: list[dict] | None = None) -> int:
    """
    Genera la carpeta plana unificada para Gemini Notebook.
    Usa el manifiesto si se provee, o escanea el disco si no.
    Solo incluye los materiales originales (PDF, PPTX, DOCX, etc.) y documentos
    de lectura nativos de Blackboard, excluyendo versiones .md de AnyDoc y SKILL.md.
    """
    gemini_dir = course_dir / DIR_GEMINI_NOTEBOOK
    gemini_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    # Limpiar posibles archivos .md de AnyDoc o SKILL.md que hayan quedado previamente en gemini_notebook
    for f in gemini_dir.iterdir():
        if f.is_file() and is_anydoc_companion_markdown(f):
            try:
                f.unlink()
            except Exception:
                pass

    if manifest is not None:
        is_legacy = any("local_path" not in item or "unit" not in item or "week" not in item for item in manifest)
        if is_legacy:
            manifest = None

    if manifest is not None:
        week_counters = {}
        idx_info = 1
        for item in manifest:
            local_path = item["local_path"]
            if isinstance(local_path, str):
                local_path = Path(local_path)

            if not local_path.exists() or local_path.stat().st_size == 0:
                continue

            # Excluir archivos .md de AnyDoc y skills
            if is_anydoc_companion_markdown(local_path):
                continue

            # Solo copiamos archivos soportados (PDF, PPTX, etc) o sin extensión válida
            if local_path.suffix.lower() not in SUPPORTED_EXTENSIONS and local_path.suffix:
                continue

            orig_name = item.get("original_name", local_path.name)
            is_info = item.get("is_info_general", False)

            if is_info:
                new_name = f"u0_s00_{idx_info:02d}_{orig_name}"
                idx_info += 1
            else:
                u_num = item.get("unit", 0)
                w_num = item.get("week", 0)
                key = (u_num, w_num)
                week_counters[key] = week_counters.get(key, 0) + 1
                idx = week_counters[key]
                new_name = f"u{u_num}_s{w_num:02d}_{idx:02d}_{orig_name}"

            shutil.copy2(local_path, gemini_dir / new_name)
            count += 1

        generate_course_skill(course_dir)
        return count

    # Escaneo en disco
    info_dir = course_dir / DIR_INFO_GENERAL
    if info_dir.exists():
        idx = 1
        for file in sorted(info_dir.rglob("*")):
            if file.is_file() and (file.suffix.lower() in SUPPORTED_EXTENSIONS or not file.suffix):
                # Omitir .md que sean complementarios de AnyDoc o skills
                if is_anydoc_companion_markdown(file):
                    continue
                new_name = f"u0_s00_{idx:02d}_{file.name}"
                shutil.copy2(file, gemini_dir / new_name)
                idx += 1
                count += 1

    mat_dir = course_dir / DIR_MATERIALES
    if mat_dir.exists():
        week_counters = {}
        # Ordenamos para asegurar que el correlativo se asigne de forma determinista
        for file in sorted(mat_dir.rglob("*")):
            if file.is_file() and (file.suffix.lower() in SUPPORTED_EXTENSIONS or not file.suffix):
                if is_anydoc_companion_markdown(file):
                    continue
                rel_parts = file.relative_to(mat_dir).parts
                path_str = " ".join(rel_parts)
                u_num = parse_unit_number(path_str) or 0
                w_num = parse_week_number(path_str) or 0
                
                key = (u_num, w_num)
                week_counters[key] = week_counters.get(key, 0) + 1
                idx = week_counters[key]
                
                new_name = f"u{u_num}_s{w_num:02d}_{idx:02d}_{file.name}"
                shutil.copy2(file, gemini_dir / new_name)
                count += 1

    generate_course_skill(course_dir)
    return count


def sanitize_name(name: str) -> str:
    """Elimina caracteres no permitidos en nombres de carpetas de Windows."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return re.sub(r"\s+", " ", clean)


def format_date(date_str: str | None) -> str:
    """Convierte fechas ISO a formato legible en español."""
    if not date_str or date_str == "Por definir":
        return "Por definir"
    try:
        dt = date_parser.parse(date_str)
        # Formato: 2026-10-15 19:00 (Jueves)
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_sem = dias[dt.weekday()]
        return dt.strftime(f"%Y-%m-%d %H:%M ({dia_sem})")
    except Exception:
        return date_str


def is_info_general(title: str, filename: str = "") -> bool:
    """Determina si un contenido pertenece a la Información General / Sílabo."""
    text = f"{title.lower()} {filename.lower()}"
    return any(kw in text for kw in KEYWORDS_INFO_GENERAL)


def format_display_path(dest_dir: Path, course_dir: Path | None, current_relative_path: str) -> str:
    """Genera una ruta amigable y concisa (ej: Semana 5 › Recursos) para mostrar en consola."""
    if course_dir:
        try:
            rel = dest_dir.relative_to(course_dir)
            parts = [p for p in rel.parts if p not in ["02_MATERIALES_Y_CLASES", "00_INFORMACION_GENERAL"]]
            if not parts:
                return "00_INFO_GENERAL" if "00_INFORMACION_GENERAL" in str(rel) else "Materiales"
            return " › ".join(parts)
        except Exception:
            pass
    return current_relative_path.replace("/", " › ") or "Materiales"


class CourseNotebookOrganizer:
    def __init__(self, client: UltraClient, output_dir: Path | None = None):
        self.client = client
        self.output_dir = output_dir or OUTPUT_DIR
        self._processed_course_files: set[str] = set()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def sync_all_courses(self, progress_callback=None) -> dict:
        """Sincroniza todos los cursos activos y genera sus cuadernos."""
        if progress_callback:
            progress_callback("status", "Obteniendo lista de cursos matriculados...")
        courses = self.client.get_courses()
        total_courses = len(courses)
        summary = {"total_courses": total_courses, "courses": []}

        all_upcoming_evals = []

        for i, course in enumerate(courses, 1):
            if progress_callback:
                progress_callback("course_start", course["name"], i, total_courses)

            c_info = self.sync_course(course, progress_callback=progress_callback)
            summary["courses"].append(c_info)
            for ev in c_info.get("evaluations", []):
                ev["course_name"] = course["name"]
                all_upcoming_evals.append(ev)

            if progress_callback:
                progress_callback("course_end", course["name"], i, total_courses)

        # Generar el cuaderno maestro de todo el ciclo para la IA
        if progress_callback:
            progress_callback("status", "Generando resumen general del semestre para la IA...")
        self._generate_master_summary(courses, all_upcoming_evals)

        return summary

    def sync_course(self, course: dict, target_section: dict | None = None, progress_callback=None) -> dict:
        """
        Sincroniza y organiza un curso en formato cuaderno.
        Si se especifica target_section, sincroniza únicamente esa unidad o semana.
        """
        self._processed_course_files = set()
        course_name = course.get("name", "Curso")
        course_code = course.get("course_id", "")
        folder_name = sanitize_name(f"[{course_code}] {course_name}" if course_code else course_name)
        course_dir = self.output_dir / folder_name

        # Crear subdirectorios del cuaderno
        dir_info = course_dir / DIR_INFO_GENERAL
        dir_evals = course_dir / DIR_EVALUACIONES
        dir_materials = course_dir / DIR_MATERIALES
        dir_announcements = course_dir / DIR_ANUNCIOS

        for d in [dir_info, dir_evals, dir_materials, dir_announcements]:
            d.mkdir(parents=True, exist_ok=True)

        course_id = course["id"]

        # 1. Obtener y guardar evaluaciones y exámenes
        if progress_callback:
            progress_callback("action", f"[{course_name[:30]}] Consultando evaluaciones y fechas de examen...")
        evaluations = self.client.get_course_evaluations(course_id)
        self._save_evaluations(dir_evals, course_name, evaluations)
        if progress_callback:
            progress_callback("log", f"📅 {len(evaluations)} evaluaciones/rúbricas registradas")

        # 2. Obtener y guardar historial de anuncios
        if progress_callback:
            progress_callback("action", f"[{course_name[:30]}] Extrayendo comunicados del profesor...")
        announcements = self.client.get_course_announcements(course_id)
        self._save_announcements(dir_announcements, course_name, announcements)
        if progress_callback:
            progress_callback("log", f"📢 {len(announcements)} anuncios obtenidos")

        # 3. Recorrer contenidos (completo o filtrado por sección/semana)
        if target_section:
            sec_id = target_section["id"]
            sec_title = target_section.get("title", "")
            parent_title = target_section.get("parent_title", "")
            init_rel = f"{sanitize_name(parent_title)}/{sanitize_name(sec_title)}" if parent_title else sanitize_name(sec_title)

            if progress_callback:
                progress_callback("action", f"[{course_name[:25]}] Sincronizando sección: {sec_title}...")

            # Obtenemos los contenidos dentro de esta unidad/semana
            section_tree = self.client.get_course_contents_tree(course_id, parent_id=sec_id)
            downloaded_files = self._download_and_organize_contents(
                section_tree,
                materials_dir=dir_materials,
                info_dir=dir_info,
                current_relative_path=init_rel,
                progress_callback=progress_callback,
                course_name=course_name,
                course_dir=course_dir
            )
        else:
            if progress_callback:
                progress_callback("action", f"[{course_name[:30]}] Explorando árbol completo de materiales...")
            contents_tree = self.client.get_course_contents_tree(course_id)
            downloaded_files = self._download_and_organize_contents(
                contents_tree,
                materials_dir=dir_materials,
                info_dir=dir_info,
                progress_callback=progress_callback,
                course_name=course_name,
                course_dir=course_dir
            )

        # 4. Generar o actualizar la portada y cuaderno resumen del curso
        self._generate_course_notebook(
            course_dir=course_dir,
            course=course,
            evaluations=evaluations,
            announcements=announcements,
            downloaded_files=downloaded_files
        )

        # 5. Convertir materiales a Markdown vía AnyDoc (side-by-side) y generar Skill de IA
        if progress_callback:
            progress_callback("action", f"[{course_name[:25]}] Convirtiendo materiales a Markdown con AnyDoc...")
        converted_count = convert_course_materials_to_markdown(course_dir, progress_callback=progress_callback)
        if converted_count > 0 and progress_callback:
            progress_callback("log", f"✨ {converted_count} documentos convertidos a Markdown para IA")

        generate_course_skill(
            course_dir=course_dir,
            course=course,
            evaluations=evaluations,
            announcements=announcements
        )
        if progress_callback:
            progress_callback("log", f"🧠 Skill de IA configurada para el curso (SKILL.md)")

        return {
            "name": course_name,
            "code": course_code,
            "dir": str(course_dir),
            "evaluations": evaluations,
            "announcements_count": len(announcements),
            "files_count": len(downloaded_files),
            "downloaded_files": downloaded_files
        }

    def _save_evaluations(self, dest_dir: Path, course_name: str, evaluations: list[dict]):
        """Genera un archivo markdown detallado con exámenes, tareas y qué entra en cada uno."""
        md_file = dest_dir / "agenda_evaluaciones.md"
        lines = [
            f"# 📅 Evaluaciones y Exámenes: {course_name}\n",
            "> Este documento recopila todas las fechas de entrega, exámenes parciales, finales,",
            "> evaluaciones continuas y rúbricas registradas en Blackboard Ultra.\n",
            "## Resumen de Fechas\n",
            "| Evaluación / Examen | Fecha y Hora | Tipo | Puntos |",
            "| :--- | :--- | :--- | :--- |"
        ]

        for ev in evaluations:
            title = ev.get("title", "Sin título")
            due = format_date(ev.get("due_date"))
            ev_type = ev.get("type", "Tarea")
            points = ev.get("points_possible")
            points_str = f"{points} pts" if points is not None else "-"
            lines.append(f"| **{title}** | `{due}` | {ev_type} | {points_str} |")

        lines.append("\n---\n")
        lines.append("## Detalle de Exámenes y Rúbricas (Qué entra / Instrucciones)\n")

        for ev in evaluations:
            title = ev.get("title", "Sin título")
            due = format_date(ev.get("due_date"))
            desc = ev.get("description_md", "").strip() or "_No se proporcionó descripción o temario en el aula virtual._"
            lines.append(f"### 📝 {title}")
            lines.append(f"- **Fecha límite / Examen:** {due}")
            lines.append(f"- **Tipo:** {ev.get('type')}")
            if ev.get("points_possible") is not None:
                lines.append(f"- **Puntaje total:** {ev.get('points_possible')} puntos")
            lines.append(f"\n**Instrucciones y Temario:**\n\n{desc}\n")
            lines.append("---\n")

        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _save_announcements(self, dest_dir: Path, course_name: str, announcements: list[dict]):
        """Genera un archivo markdown con los comunicados del profesor."""
        md_file = dest_dir / "historial_anuncios.md"
        lines = [
            f"# 📢 Anuncios Oficiales: {course_name}\n",
            "> Comunicados publicados por los profesores en el aula virtual ordenados cronológicamente.\n"
        ]

        if not announcements:
            lines.append("_No hay anuncios publicados en este curso._\n")
        else:
            for ann in announcements:
                title = ann.get("title", "Aviso")
                created = format_date(ann.get("created"))
                body = ann.get("body_md", "").strip() or "_Sin contenido adicional._"
                lines.append(f"## 📌 {title}")
                lines.append(f"*Publicado el: {created}*\n")
                lines.append(f"{body}\n")
                lines.append("---\n")

        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _download_and_organize_contents(
        self,
        nodes: list[dict],
        materials_dir: Path,
        info_dir: Path,
        current_relative_path: str = "",
        progress_callback=None,
        course_name: str = "",
        course_dir: Path | None = None
    ) -> list[dict]:
        """
        Recorre los contenidos. Coloca los archivos directamente en la carpeta actual
        sin crear una subcarpeta innecesaria por cada archivo.
        Si detecta que es Sílabo / Plan Calendario, lo coloca en 00_INFORMACION_GENERAL.
        """
        downloaded = []

        for node in nodes:
            title = node.get("title", "Contenido")
            sanitized_title = sanitize_name(title)
            is_info = is_info_general(title)
            children = node.get("children", [])
            attachments = node.get("attachments", [])
            handler = node.get("handler", "")

            is_folder = bool(children) or ("folder" in handler.lower()) or ("module" in handler.lower())

            # Directorio destino directo (sin subcarpeta redundante para archivos individuales)
            if is_info:
                target_folder = info_dir
            else:
                target_folder = materials_dir / current_relative_path

            # 1. Si tiene archivos adjuntos directos, descargarlos en target_folder
            for att in attachments:
                file_name = sanitize_name(att.get("fileName", "archivo"))
                ext = Path(file_name).suffix.lower()

                # Verificar si es una extensión soportada
                if ext in SUPPORTED_EXTENSIONS or not ext:
                    dest_dir = info_dir if (is_info or is_info_general("", file_name)) else target_folder
                    dest_file = dest_dir / file_name
                    dest_file_key = str(dest_file.resolve())

                    # Evitar procesar o loguear el mismo archivo múltiples veces
                    if dest_file_key in self._processed_course_files:
                        continue

                    display_path = format_display_path(dest_dir, course_dir, current_relative_path)

                    # Si el archivo ya existe en disco con contenido, evitar la petición de red
                    if dest_file.exists() and dest_file.stat().st_size > 0:
                        self._processed_course_files.add(dest_file_key)
                        if progress_callback:
                            progress_callback("log", f"⚡ [dim cyan]{display_path}[/dim cyan] ➔ [dim]{file_name}[/dim] [dim green](ya descargado)[/dim green]")
                        u_num = parse_unit_number(f"{current_relative_path} {file_name}") or 0
                        w_num = parse_week_number(f"{current_relative_path} {file_name}") or 0
                        downloaded.append({
                            "title": title,
                            "file_name": file_name,
                            "local_path": dest_file,
                            "original_name": file_name,
                            "unit": u_num,
                            "week": w_num,
                            "path": str(dest_file.relative_to(self.output_dir)),
                            "is_info_general": (dest_dir == info_dir)
                        })
                        if dest_file.suffix.lower() in ANYDOC_SUPPORTED_EXTENSIONS and dest_file.suffix.lower() != ".md":
                            convert_to_markdown_anydoc(dest_file)
                        continue

                    download_url = att.get("downloadUrl")
                    if download_url:
                        if progress_callback:
                            progress_callback("action", f"[{course_name[:25]}] ⬇️ {file_name}")

                        success = self.client.download_file(download_url, dest_file)
                        if success:
                            self._processed_course_files.add(dest_file_key)
                            if progress_callback:
                                progress_callback("log", f"💾 [dim cyan]{display_path}[/dim cyan] ➔ [bold white]{file_name}[/bold white]")
                            u_num = parse_unit_number(f"{current_relative_path} {file_name}") or 0
                            w_num = parse_week_number(f"{current_relative_path} {file_name}") or 0
                            downloaded.append({
                                "title": title,
                                "file_name": file_name,
                                "local_path": dest_file,
                                "original_name": file_name,
                                "unit": u_num,
                                "week": w_num,
                                "path": str(dest_file.relative_to(self.output_dir)),
                                "is_info_general": (dest_dir == info_dir)
                            })
                            if dest_file.suffix.lower() in ANYDOC_SUPPORTED_EXTENSIONS and dest_file.suffix.lower() != ".md":
                                convert_to_markdown_anydoc(dest_file)

            # 2. Si tiene lecturas o recursos embebidos (ej: documentos de Blackboard con links bbcswebdav)
            embedded_files = list(node.get("embedded_files", []))
            seen_canonical = {html.unescape(emb.get("url", "")).split("?")[0].rstrip("/") for emb in embedded_files if emb.get("url")}

            # Asegurar que cualquier enlace bbcswebdav presente en description_md o raw_body se incluya sin duplicados
            desc_md = node.get("description_md", "").strip()
            raw_body = node.get("raw_body", "")
            for text_src in (desc_md, raw_body):
                if not text_src:
                    continue
                for match_url in re.findall(r'https?://[^\s"\'<>)]+bbcswebdav[^\s"\'<>)]+|/bbcswebdav/[^\s"\'<>)]+', text_src):
                    raw_match = html.unescape(match_url.rstrip(".,;)\"'"))
                    canon = raw_match.split("?")[0].rstrip("/")
                    if canon not in seen_canonical:
                        seen_canonical.add(canon)
                        embedded_files.append({
                            "url": raw_match,
                            "text": "recurso"
                        })

            downloaded_embedded_map = {}  # url -> saved_file_name
            ignored_banner_urls = set()

            for emb in embedded_files:
                emb_url = emb.get("url")
                emb_text = sanitize_name(emb.get("text", "lectura"))
                dest_dir = info_dir if is_info else target_folder
                if not emb_url:
                    continue

                display_path = format_display_path(dest_dir, course_dir, current_relative_path)

                # 1. Verificar si ya fue descargado previamente (0 peticiones de red)
                existing_name = self.client.check_existing_file(emb_url, dest_dir, fallback_name=emb_text)
                if existing_name:
                    dest_file_key = str((dest_dir / existing_name).resolve())
                    downloaded_embedded_map[emb_url] = existing_name

                    if dest_file_key not in self._processed_course_files:
                        self._processed_course_files.add(dest_file_key)
                        if progress_callback:
                            progress_callback("log", f"⚡ [dim cyan]{display_path}[/dim cyan] ➔ [dim]{existing_name}[/dim] [dim green](ya descargado)[/dim green]")
                        u_num = parse_unit_number(f"{current_relative_path} {existing_name}") or 0
                        w_num = parse_week_number(f"{current_relative_path} {existing_name}") or 0
                        downloaded.append({
                            "title": emb_text if emb_text not in ["recurso", "lectura"] else existing_name,
                            "file_name": existing_name,
                            "local_path": dest_dir / existing_name,
                            "original_name": existing_name,
                            "unit": u_num,
                            "week": w_num,
                            "path": str((dest_dir / existing_name).relative_to(self.output_dir)),
                            "is_info_general": (dest_dir == info_dir)
                        })
                        emb_file = dest_dir / existing_name
                        if emb_file.suffix.lower() in ANYDOC_SUPPORTED_EXTENSIONS and emb_file.suffix.lower() != ".md":
                            convert_to_markdown_anydoc(emb_file)
                    continue

                # 2. Si no está en disco, realizar la petición y descarga
                if progress_callback:
                    progress_callback("action", f"[{course_name[:25]}] 📖 Descargando: {emb_text}...")

                saved_name = self.client.download_embedded_file(emb_url, dest_dir, fallback_name=emb_text)
                if saved_name:
                    downloaded_embedded_map[emb_url] = saved_name
                    dest_file_key = str((dest_dir / saved_name).resolve())

                    # Evitar procesar o loguear el mismo archivo múltiples veces en el mismo destino
                    if dest_file_key in self._processed_course_files:
                        continue
                    self._processed_course_files.add(dest_file_key)

                    if progress_callback:
                        progress_callback("log", f"💾 [dim cyan]{display_path}[/dim cyan] ➔ [bold white]{saved_name}[/bold white]")
                    u_num = parse_unit_number(f"{current_relative_path} {saved_name}") or 0
                    w_num = parse_week_number(f"{current_relative_path} {saved_name}") or 0
                    downloaded.append({
                        "title": emb_text if emb_text not in ["recurso", "lectura"] else saved_name,
                        "file_name": saved_name,
                        "local_path": dest_dir / saved_name,
                        "original_name": saved_name,
                        "unit": u_num,
                        "week": w_num,
                        "path": str((dest_dir / saved_name).relative_to(self.output_dir)),
                        "is_info_general": (dest_dir == info_dir)
                    })
                    saved_file = dest_dir / saved_name
                    if saved_file.suffix.lower() in ANYDOC_SUPPORTED_EXTENSIONS and saved_file.suffix.lower() != ".md":
                        convert_to_markdown_anydoc(saved_file)
                else:
                    # Fue ignorado (imagen/banner decorativo o no descargable)
                    ignored_banner_urls.add(emb_url)

            # 3. Si es un enlace externo (ej: repositorio de GitHub o herramienta)
            ext_url = node.get("external_url")
            if ext_url:
                dest_dir = info_dir if is_info else target_folder
                dest_dir.mkdir(parents=True, exist_ok=True)
                links_file = dest_dir / "ENLACES_Y_REPOSITORIOS.md"
                entry = f"- [{title}]({ext_url})\n"
                try:
                    current_text = links_file.read_text(encoding="utf-8") if links_file.exists() else "# 🔗 Enlaces y Repositorios Externos\n\n"
                    if ext_url not in current_text:
                        with open(links_file, "a", encoding="utf-8") as f:
                            f.write(entry)
                        if progress_callback:
                            progress_callback("log", f"  🔗 Enlace registrado: {title}")
                except Exception:
                    pass

            # 4. Si el documento contiene explicaciones o rutas de aprendizaje en texto
            if desc_md and ("document" in handler.lower() or "recurso" in title.lower() or "guia" in title.lower() or "ruta" in title.lower() or downloaded_embedded_map):
                dest_dir = info_dir if is_info else target_folder
                dest_dir.mkdir(parents=True, exist_ok=True)
                doc_name = "Recursos_de_aprendizaje.md" if sanitized_title.lower() == "ultradocumentbody" else f"{sanitized_title}.md"
                doc_path = dest_dir / doc_name

                # Limpiar desc_md reemplazando URLs de archivos descargados por enlaces relativos locales
                clean_md = desc_md
                for emb_url, saved_name in downloaded_embedded_map.items():
                    quoted_name = urllib.parse.quote(saved_name)
                    # Reemplazar enlaces en markdown [](url) o [texto](url) por el nombre del archivo local
                    pattern = re.compile(r'\[([^\]]*)\]\(' + re.escape(emb_url) + r'\)')
                    clean_md = pattern.sub(f'📄 [{saved_name}](./{quoted_name})', clean_md)
                    clean_md = clean_md.replace(emb_url, f'./{quoted_name}')

                # Limpiar enlaces a banners de imágenes ignorados que hayan quedado como [](url)
                for banner_url in ignored_banner_urls:
                    clean_md = re.sub(r'\[([^\]]*)\]\(' + re.escape(banner_url) + r'\)\s*', '', clean_md)
                    clean_md = clean_md.replace(banner_url, '')

                # Verificar si tras limpiar queda texto explicativo real o solo enlaces
                text_only = re.sub(r'\[([^\]]*)\]\([^)]+\)', '', clean_md)
                text_only = re.sub(r'https?://\S+', '', text_only)
                text_only = re.sub(r'[📄#\*\-\s\n\r]', '', text_only)

                # Si solo había enlaces y ningún texto explicativo, estructurarlo limpiamente
                if len(text_only) < 15 and downloaded_embedded_map:
                    file_links = "\n".join([f"- 📄 [{name}](./{urllib.parse.quote(name)})" for name in downloaded_embedded_map.values()])
                    content_to_write = f"# 📄 {title if sanitized_title.lower() != 'ultradocumentbody' else 'Recursos de Aprendizaje'}\n\n### 📚 Materiales de estudio:\n{file_links}\n"
                elif clean_md.strip():
                    content_to_write = f"# 📄 {title if sanitized_title.lower() != 'ultradocumentbody' else 'Documento de Lectura'}\n\n{clean_md.strip()}\n"
                else:
                    content_to_write = ""

                if content_to_write:
                    try:
                        with open(doc_path, "w", encoding="utf-8") as f:
                            f.write(content_to_write)
                        u_num = parse_unit_number(f"{current_relative_path} {doc_name}") or 0
                        w_num = parse_week_number(f"{current_relative_path} {doc_name}") or 0
                        downloaded.append({
                            "title": title,
                            "file_name": doc_name,
                            "local_path": doc_path,
                            "original_name": doc_name,
                            "unit": u_num,
                            "week": w_num,
                            "path": str(doc_path.relative_to(self.output_dir)),
                            "is_info_general": (dest_dir == info_dir)
                        })
                    except Exception:
                        pass

            # 5. Si es carpeta o módulo con hijos, recorrer recursivamente creando la subcarpeta
            if is_folder and children:
                next_rel = "" if is_info else (f"{current_relative_path}/{sanitized_title}".strip("/"))
                sub_downloaded = self._download_and_organize_contents(
                    children,
                    materials_dir=materials_dir,
                    info_dir=info_dir,
                    current_relative_path=next_rel,
                    progress_callback=progress_callback,
                    course_name=course_name,
                    course_dir=course_dir
                )
                downloaded.extend(sub_downloaded)

        return downloaded

    def _generate_course_notebook(
        self,
        course_dir: Path,
        course: dict,
        evaluations: list[dict],
        announcements: list[dict],
        downloaded_files: list[dict]
    ):
        """Genera el cuaderno central en Markdown para el curso."""
        notebook_file = course_dir / "CUADERNO_CURSO.md"
        name = course.get("name", "Curso")
        code = course.get("course_id", "")

        lines = [
            f"# 📓 Cuaderno de Estudio: {name}",
            f"**Código de Asignatura:** `{code}`  ",
            f"**Última actualización:** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`\n",
            "---\n",
            "## 📌 Acceso Rápido del Cuaderno",
            f"- [📁 00_INFORMACION_GENERAL](./{DIR_INFO_GENERAL}/): Sílabo, plan calendario y fórmulas de evaluación.",
            f"- [📅 01_EVALUACIONES_Y_EXAMENES](./{DIR_EVALUACIONES}/agenda_evaluaciones.md): Fechas y qué viene en cada examen.",
            f"- [📚 02_MATERIALES_Y_CLASES](./{DIR_MATERIALES}/): Diapositivas, lecturas y prácticas organizadas por semana.",
            f"- [📢 03_ANUNCIOS](./{DIR_ANUNCIOS}/historial_anuncios.md): Avisos y mensajes del docente.\n",
            "---\n",
            "## 🎯 Próximas Evaluaciones y Exámenes Importantes\n"
        ]

        if not evaluations:
            lines.append("_No hay evaluaciones programadas registradas en el calendario._\n")
        else:
            for ev in evaluations[:5]:  # Mostrar los primeros 5
                title = ev.get("title")
                due = format_date(ev.get("due_date"))
                lines.append(f"- **{title}**: `{due}` ({ev.get('type')})")
            lines.append(f"\n*(Ver detalle completo con instrucciones y temario en [agenda_evaluaciones.md](./{DIR_EVALUACIONES}/agenda_evaluaciones.md))*\n")

        lines.append("---\n## 📢 Últimos Avisos del Profesor\n")
        if not announcements:
            lines.append("_No hay anuncios recientes._\n")
        else:
            for ann in announcements[:3]:
                lines.append(f"### {ann.get('title')} (`{format_date(ann.get('created'))}`)")
                lines.append(f"{ann.get('body_md')[:300]}...\n")
            lines.append(f"*(Ver todos los avisos en [historial_anuncios.md](./{DIR_ANUNCIOS}/historial_anuncios.md))*\n")

        lines.append("---\n## 📂 Resumen de Archivos Descargados\n")
        info_files = [f for f in downloaded_files if f["is_info_general"]]
        if info_files:
            lines.append("### 📄 Documentos de Información General / Sílabo:")
            for f in info_files:
                lines.append(f"- [{f['file_name']}](./{DIR_INFO_GENERAL}/{f['file_name']})")

        lines.append(f"\nTotal de archivos y materiales sincronizados: **{len(downloaded_files)}**\n")

        with open(notebook_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _generate_master_summary(self, courses: list[dict], all_evaluations: list[dict]):
        """Genera el cuaderno maestro de todo el semestre para consulta de la IA."""
        master_file = self.output_dir / "RESUMEN_SEMESTRE_IA.md"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Filtrar y ordenar evaluaciones globales por fecha
        sorted_evals = sorted(
            [ev for ev in all_evaluations if ev.get("due_date") and ev.get("due_date") != "Por definir"],
            key=lambda x: x["due_date"]
        )

        lines = [
            "# 🧠 Panorama Semestral y Calendario para Asistente IA\n",
            "> Archivo central de contexto para la IA. Contiene la lista de cursos matriculados,",
            "> el cronograma unificado de exámenes/entregas y enlaces a los cuadernos de estudio.\n",
            f"**Generado el:** `{now_str}`\n",
            "---\n",
            "## 📚 Cursos Matriculados en el Semestre\n",
            "| Curso | Código | Enlace al Cuaderno |",
            "| :--- | :--- | :--- |"
        ]

        for c in courses:
            name = c.get("name", "Curso")
            code = c.get("course_id", "")
            folder_name = sanitize_name(f"[{code}] {name}" if code else name)
            lines.append(f"| **{name}** | `{code}` | [Abrir Cuaderno](./{folder_name}/CUADERNO_CURSO.md) |")

        lines.append("\n---\n")
        lines.append("## ⏰ Calendario Unificado de Exámenes y Entregas (Todas las Asignaturas)\n")
        lines.append("| Fecha y Hora | Curso | Evaluación / Examen | Tipo |")
        lines.append("| :--- | :--- | :--- | :--- |")

        if not sorted_evals:
            lines.append("| - | - | _No hay fechas programadas aún_ | - |")
        else:
            for ev in sorted_evals:
                due = format_date(ev.get("due_date"))
                c_name = ev.get("course_name", "")
                title = ev.get("title", "")
                ev_type = ev.get("type", "")
                lines.append(f"| `{due}` | **{c_name}** | {title} | {ev_type} |")

        lines.append("\n---\n")
        lines.append("## 💡 Instrucciones para la IA:")
        lines.append("1. Cuando el usuario pregunte por sus cursos, consulta la tabla superior.")
        lines.append("2. Cuando pregunte qué exámenes tiene próximamente o qué entra en cada uno, consulta la tabla de fechas y los archivos `agenda_evaluaciones.md` de cada cuaderno.")
        lines.append("3. Si busca el sílabo, plan calendario o fórmulas de evaluación, están en la carpeta `00_INFORMACION_GENERAL` de la asignatura respectiva.")

        with open(master_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # Generar skill maestro del semestre para asistentes IA
        generate_semester_skill(self.output_dir, courses, all_evaluations)
