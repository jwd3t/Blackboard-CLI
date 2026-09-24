"""
Cliente HTTP para interactuar con la API REST de Blackboard Ultra.
Consume los endpoints internos para obtener cursos, carpetas, archivos, anuncios y calendario.
"""
from __future__ import annotations

import re
import mimetypes
import urllib.parse
from pathlib import Path
import html2text
from typing import Any
import httpx
from bs4 import BeautifulSoup

from config import BASE_URL
from auth import get_stored_cookies


def get_filename_from_cd(cd_header: str) -> str | None:
    """Extrae el nombre de archivo real del encabezado Content-Disposition."""
    if not cd_header:
        return None
    # 1. RFC 5987 / 6266 filename*
    m = re.search(r"filename\*=(?:UTF-8''|utf-8'')([^;]+)", cd_header, re.IGNORECASE)
    if m:
        return urllib.parse.unquote(m.group(1).strip("\"' \t"))
    # 2. filename entre comillas
    m = re.search(r'filename="([^"]+)"', cd_header, re.IGNORECASE)
    if m:
        return urllib.parse.unquote(m.group(1).strip())
    # 3. filename sin comillas
    m = re.search(r'filename=([^;\s]+)', cd_header, re.IGNORECASE)
    if m:
        return urllib.parse.unquote(m.group(1).strip("\"' \t"))
    return None


class UltraClient:
    def __init__(self, cookies: dict[str, str] | None = None):
        if cookies is None:
            cookies = get_stored_cookies() or {}
        self.cookies = cookies
        xsrf = self.cookies.get("XSRF-TOKEN", "")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "X-Blackboard-XSRF": xsrf,
            "X-XSRF-TOKEN": xsrf,
        }
        self.client = httpx.Client(
            base_url=BASE_URL,
            cookies=self.cookies,
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True
        )
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.body_width = 0

    def clean_html(self, html_content: str | None) -> str:
        """Convierte contenido HTML a Markdown limpio para la IA."""
        if not html_content:
            return ""
        try:
            return self.html_converter.handle(html_content).strip()
        except Exception:
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text("\n").strip()

    def get_me(self) -> dict:
        """Obtiene la información del usuario autenticado."""
        resp = self.client.get("/learn/api/public/v1/users/me")
        resp.raise_for_status()
        return resp.json()

    def get_courses(self) -> list[dict]:
        """
        Obtiene únicamente los cursos activos en los que el estudiante está matriculado.
        Usa el endpoint específico del usuario (/learn/api/public/v1/users/me/courses)
        evitando el catálogo general de la universidad.
        """
        user = self.get_me()
        user_id = user["id"]

        # Consultar cursos donde el usuario está matriculado
        resp = self.client.get(f"/learn/api/public/v1/users/{user_id}/courses")
        if resp.status_code != 200:
            resp = self.client.get("/learn/api/public/v1/users/me/courses")

        if resp.status_code != 200:
            return []

        user_courses_raw = resp.json().get("results", [])
        cleaned = []
        seen = set()

        for item in user_courses_raw:
            cid = item.get("courseId")
            if not cid or cid in seen:
                continue

            seen.add(cid)
            # Consultar los metadatos completos de este curso específico
            c_resp = self.client.get(f"/learn/api/public/v3/courses/{cid}")
            if c_resp.status_code == 200:
                c_data = c_resp.json()
                course_name = c_data.get("name")
                # Descartar cursos sin nombre o de prueba
                if course_name:
                    cleaned.append({
                        "id": cid,
                        "course_id": c_data.get("courseId", ""),
                        "name": course_name,
                        "description": self.clean_html(c_data.get("description", "")),
                        "created": c_data.get("created", ""),
                        "ultra_status": c_data.get("ultraStatus", "Ultra")
                    })

        return cleaned

    def get_course_announcements(self, course_id: str) -> list[dict]:
        """Obtiene todos los anuncios de un curso en formato estructurado."""
        url = f"/learn/api/public/v1/courses/{course_id}/announcements"
        resp = self.client.get(url)
        if resp.status_code != 200:
            return []

        results = resp.json().get("results", [])
        announcements = []
        for ann in results:
            announcements.append({
                "id": ann.get("id"),
                "title": ann.get("title", "Sin título"),
                "body_md": self.clean_html(ann.get("body", "")),
                "created": ann.get("created", ""),
                "modified": ann.get("modified", "")
            })
        # Ordenar de más reciente a más antiguo
        announcements.sort(key=lambda x: x["created"], reverse=True)
        return announcements

    def get_course_evaluations(self, course_id: str) -> list[dict]:
        """
        Obtiene las evaluaciones, tareas, exámenes y fechas de entrega
        usando tanto el calendario como las columnas del libro de calificaciones.
        """
        evaluations = []
        seen_titles = set()

        # 1. Consultar el calendario del curso
        cal_url = f"/learn/api/public/v1/calendars/items?courseId={course_id}"
        cal_resp = self.client.get(cal_url)
        if cal_resp.status_code == 200:
            for item in cal_resp.json().get("results", []):
                title = item.get("title", "").strip()
                if not title:
                    continue
                seen_titles.add(title.lower())
                evaluations.append({
                    "id": item.get("id"),
                    "title": title,
                    "type": item.get("type", "Evaluación"),
                    "due_date": item.get("end") or item.get("start") or "Por definir",
                    "description_md": self.clean_html(item.get("description", "")),
                    "source": "calendar"
                })

        # 2. Consultar el Gradebook (Libro de calificaciones) para descripciones y rúbricas adicionales
        gb_url = f"/learn/api/public/v1/courses/{course_id}/gradebook/columns"
        gb_resp = self.client.get(gb_url)
        if gb_resp.status_code == 200:
            for col in gb_resp.json().get("results", []):
                name = col.get("name", "").strip()
                if not name or name.lower() in seen_titles:
                    continue
                evaluations.append({
                    "id": col.get("id"),
                    "title": name,
                    "type": "Calificación / Entrega",
                    "due_date": col.get("grading", {}).get("due") or "Por definir",
                    "points_possible": col.get("score", {}).get("possible", None),
                    "description_md": self.clean_html(col.get("description", "")),
                    "source": "gradebook"
                })

        # Ordenar por fecha de entrega
        evaluations.sort(key=lambda x: x.get("due_date") or "9999", reverse=False)
        return evaluations

    def get_course_sections(self, course_id: str) -> list[dict]:
        """
        Explora las unidades, semanas y carpetas de un curso
        para permitir al usuario seleccionar una unidad o semana específica a sincronizar.
        """
        cnt_resp = self.client.get(f"/learn/api/public/v1/courses/{course_id}/contents")
        if cnt_resp.status_code != 200:
            return []

        sections = []
        for it in cnt_resp.json().get("results", []):
            title = it.get("title", "").strip()
            cid = it.get("id")
            handler = it.get("contentHandler", {}).get("id", "")
            has_ch = it.get("hasChildren", False)
            if has_ch or any(k in handler for k in ["folder", "module", "lesson"]):
                sections.append({
                    "id": cid,
                    "title": title,
                    "display_title": title,
                    "parent_title": "",
                    "level": 0
                })
                # Explorar nivel secundario para encontrar semanas
                sub_resp = self.client.get(f"/learn/api/public/v1/courses/{course_id}/contents/{cid}/children")
                if sub_resp.status_code == 200:
                    for sub in sub_resp.json().get("results", []):
                        s_title = sub.get("title", "").strip()
                        s_cid = sub.get("id")
                        s_handler = sub.get("contentHandler", {}).get("id", "")
                        s_has_ch = sub.get("hasChildren", False)
                        if s_has_ch or any(k in s_handler for k in ["folder", "module", "lesson"]) or any(k in s_title for k in ["Semana", "Unidad", "Tema", "Laboratorio", "Guía", "Guia"]):
                            sections.append({
                                "id": s_cid,
                                "title": s_title,
                                "display_title": f"  ↳ {s_title}",
                                "parent_title": title,
                                "level": 1
                            })
        return sections

    def get_course_contents_tree(self, course_id: str, parent_id: str | None = None) -> list[dict]:
        """
        Recorre recursivamente los contenidos del curso (carpetas, archivos, módulos).
        """
        if parent_id:
            url = f"/learn/api/public/v1/courses/{course_id}/contents/{parent_id}/children"
        else:
            url = f"/learn/api/public/v1/courses/{course_id}/contents"

        resp = self.client.get(url)
        if resp.status_code != 200:
            return []

        items = resp.json().get("results", [])
        tree = []

        for item in items:
            item_id = item.get("id")
            title = item.get("title", "Sin título").strip()
            handler = item.get("contentHandler", {}).get("id", "")
            has_children = item.get("hasChildren", False)
            raw_body = item.get("body", "")
            body = self.clean_html(raw_body)

            # Extraer enlaces embebidos de lecturas y archivos dentro del HTML del documento
            embedded_files = []
            seen_urls = set()
            if raw_body:
                soup = BeautifulSoup(raw_body, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if not href or href in seen_urls:
                        continue
                    if "bbcswebdav" in href or "/xid-" in href:
                        seen_urls.add(href)
                        # Buscar el mejor nombre o texto descriptivo disponible
                        text = (
                            a.get_text().strip() or
                            a.get("title", "").strip() or
                            a.get("aria-label", "").strip() or
                            a.get("download", "").strip() or
                            ""
                        )
                        if not text and a.find("img"):
                            text = a.find("img").get("alt", "").strip()
                        embedded_files.append({
                            "url": href,
                            "text": text or "recurso"
                        })

                # Extraer cualquier otra URL de bbcswebdav encontrada en el HTML (incluyendo fuentes de bloques Ultra)
                for match_url in re.findall(r'https?://[^\s"\'<>)]+bbcswebdav[^\s"\'<>)]+|/bbcswebdav/[^\s"\'<>)]+', raw_body):
                    cleaned_url = match_url.rstrip(".,;)\"'")
                    if cleaned_url not in seen_urls:
                        seen_urls.add(cleaned_url)
                        embedded_files.append({
                            "url": cleaned_url,
                            "text": "recurso"
                        })

            external_url = item.get("contentHandler", {}).get("url")

            node = {
                "id": item_id,
                "title": title,
                "handler": handler,
                "has_children": has_children,
                "description_md": body,
                "raw_body": raw_body,
                "attachments": [],
                "embedded_files": embedded_files,
                "external_url": external_url,
                "children": []
            }

            # Consultar adjuntos si es un archivo o documento
            att_url = f"/learn/api/public/v1/courses/{course_id}/contents/{item_id}/attachments"
            att_resp = self.client.get(att_url)
            if att_resp.status_code == 200:
                for att in att_resp.json().get("results", []):
                    att_id = att.get("id")
                    node["attachments"].append({
                        "id": att_id,
                        "fileName": att.get("fileName", f"archivo_{att_id}"),
                        "mimeType": att.get("mimeType", ""),
                        "downloadUrl": f"/learn/api/public/v1/courses/{course_id}/contents/{item_id}/attachments/{att_id}/download"
                    })

            # Si es carpeta o módulo con hijos, recorrer recursivamente
            if has_children or "folder" in handler or "module" in handler or "lesson" in handler:
                node["children"] = self.get_course_contents_tree(course_id, parent_id=item_id)

            tree.append(node)

        return tree

    def download_file(self, download_url: str, dest_path) -> bool:
        """Descarga un archivo si no existe ya localmente."""
        if dest_path.exists() and dest_path.stat().st_size > 0:
            return True  # Ya descargado

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.client.stream("GET", download_url) as resp:
                if resp.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                    return True
        except Exception as e:
            print(f"Error al descargar {dest_path.name}: {e}")
        return False

    def download_embedded_file(self, url: str, dest_dir, fallback_name: str = "documento") -> str | None:
        """
        Descarga una lectura o recurso embebido (ej: bbcswebdav) detectando
        su nombre de archivo real desde los encabezados HTTP.
        Retorna el nombre del archivo descargado o None si falló o si es un recurso ignorado (ej. imagen/banner).
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            with self.client.stream("GET", url, follow_redirects=True) as resp:
                if resp.status_code != 200:
                    return None

                ct = resp.headers.get("content-type", "").lower()
                clean_ct = ct.split(";")[0].strip()

                # Si es una página web / redirect de login o error HTML, omitir
                if clean_ct == "text/html":
                    return None

                # Si es una imagen o video decorativo (como el banner de la cabecera), omitir
                if clean_ct.startswith("image/") or clean_ct.startswith("video/"):
                    return None

                cd = resp.headers.get("content-disposition", "")
                real_name = get_filename_from_cd(cd)

                if not real_name:
                    # Mapeo de tipos MIME comunes de documentos
                    mimes = {
                        "application/pdf": ".pdf",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
                        "application/vnd.ms-powerpoint": ".ppt",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                        "application/msword": ".doc",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                        "application/vnd.ms-excel": ".xls",
                        "application/zip": ".zip",
                        "application/x-zip-compressed": ".zip",
                        "application/x-rar-compressed": ".rar",
                        "text/plain": ".txt",
                        "text/csv": ".csv",
                    }
                    ext = mimes.get(clean_ct) or mimetypes.guess_extension(clean_ct) or ""

                    if Path(fallback_name).suffix:
                        real_name = fallback_name
                    else:
                        real_name = (fallback_name or "documento") + ext

                # Sanitizar caracteres ilegales en archivos
                real_name = re.sub(r'[\\/*?:"<>|]', "_", real_name).strip()
                if not real_name:
                    return None

                # Omitir imágenes y videos por extensión
                ignored_exts = {".mp4", ".mov", ".avi", ".mkv", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"}
                ext_check = Path(real_name).suffix.lower()
                if ext_check in ignored_exts or not ext_check:
                    return None

                final_path = dest_dir / real_name
                # Si ya existe con tamaño mayor a 0, no re-descargar
                if final_path.exists() and final_path.stat().st_size > 0:
                    return real_name

                with open(final_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                return real_name
        except Exception as e:
            print(f"Error al descargar recurso embebido {fallback_name}: {e}")
            return None
