"""
Módulo organizador de "Cuadernos de Curso".
Estructura automáticamente la información dispersa de Blackboard Ultra
en carpetas limpias y genera archivos Markdown optimizados para el estudiante y la IA.
"""
from __future__ import annotations

import re
import json
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
    KEYWORDS_INFO_GENERAL,
    SUPPORTED_EXTENSIONS,
)
from ultra_client import UltraClient


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


class CourseNotebookOrganizer:
    def __init__(self, client: UltraClient):
        self.client = client
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
        course_name = course.get("name", "Curso")
        course_code = course.get("course_id", "")
        folder_name = sanitize_name(f"[{course_code}] {course_name}" if course_code else course_name)
        course_dir = OUTPUT_DIR / folder_name

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
                course_name=course_name
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
                course_name=course_name
            )

        # 4. Generar o actualizar la portada y cuaderno resumen del curso
        self._generate_course_notebook(
            course_dir=course_dir,
            course=course,
            evaluations=evaluations,
            announcements=announcements,
            downloaded_files=downloaded_files
        )

        return {
            "name": course_name,
            "code": course_code,
            "dir": str(course_dir),
            "evaluations": evaluations,
            "announcements_count": len(announcements),
            "files_count": len(downloaded_files)
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
        course_name: str = ""
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
                    download_url = att.get("downloadUrl")
                    if download_url:
                        cat_label = "00_INFO_GENERAL" if dest_dir == info_dir else "02_MATERIALES"
                        if progress_callback:
                            progress_callback("action", f"[{course_name[:25]}] ⬇️ Descargando: {file_name} -> {cat_label}")

                        success = self.client.download_file(download_url, dest_file)
                        if success:
                            if progress_callback:
                                progress_callback("log", f"  💾 Guardado: {file_name} ({cat_label})")
                            downloaded.append({
                                "title": title,
                                "file_name": file_name,
                                "path": str(dest_file.relative_to(OUTPUT_DIR)),
                                "is_info_general": (dest_dir == info_dir)
                            })

            # 2. Si tiene lecturas o recursos embebidos (ej: documentos de Blackboard con links bbcswebdav)
            embedded_files = list(node.get("embedded_files", []))
            seen_emb_urls = {emb.get("url") for emb in embedded_files if emb.get("url")}

            # Asegurar que cualquier enlace bbcswebdav presente en description_md o raw_body se incluya
            desc_md = node.get("description_md", "").strip()
            raw_body = node.get("raw_body", "")
            for text_src in (desc_md, raw_body):
                if not text_src:
                    continue
                for match_url in re.findall(r'https?://[^\s"\'<>)]+bbcswebdav[^\s"\'<>)]+|/bbcswebdav/[^\s"\'<>)]+', text_src):
                    cleaned_url = match_url.rstrip(".,;)\"'")
                    if cleaned_url not in seen_emb_urls:
                        seen_emb_urls.add(cleaned_url)
                        embedded_files.append({
                            "url": cleaned_url,
                            "text": "recurso"
                        })

            downloaded_embedded_map = {}  # url -> saved_file_name
            ignored_banner_urls = set()

            for emb in embedded_files:
                emb_url = emb.get("url")
                emb_text = sanitize_name(emb.get("text", "lectura"))
                dest_dir = info_dir if is_info else target_folder
                if emb_url:
                    if progress_callback:
                        progress_callback("action", f"[{course_name[:25]}] 📖 Descargando recurso: {emb_text}...")

                    saved_name = self.client.download_embedded_file(emb_url, dest_dir, fallback_name=emb_text)
                    if saved_name:
                        downloaded_embedded_map[emb_url] = saved_name
                        if progress_callback:
                            progress_callback("log", f"  📖 Recurso guardado: {saved_name}")
                        downloaded.append({
                            "title": emb_text if emb_text not in ["recurso", "lectura"] else saved_name,
                            "file_name": saved_name,
                            "path": str((dest_dir / saved_name).relative_to(OUTPUT_DIR)),
                            "is_info_general": (dest_dir == info_dir)
                        })
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
                        downloaded.append({
                            "title": title,
                            "file_name": doc_name,
                            "path": str(doc_path.relative_to(OUTPUT_DIR)),
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
                    course_name=course_name
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
        master_file = OUTPUT_DIR / "RESUMEN_SEMESTRE_IA.md"
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
