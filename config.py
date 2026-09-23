"""
Configuraciones globales para el sincronizador de Blackboard Ultra UPC.
"""
from pathlib import Path

# Versión del software
VERSION = "2.0.0"

# URL base del aula virtual
BASE_URL = "https://aulavirtual.upc.edu.pe"

# Rutas de almacenamiento local
BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = BASE_DIR / ".session_data"
COOKIES_FILE = SESSION_DIR / "cookies.json"
OUTPUT_DIR = BASE_DIR / "cuadernos"

# Estructura del cuaderno por curso
DIR_INFO_GENERAL = "00_INFORMACION_GENERAL"
DIR_EVALUACIONES = "01_EVALUACIONES_Y_EXAMENES"
DIR_MATERIALES = "02_MATERIALES_Y_CLASES"
DIR_ANUNCIOS = "03_ANUNCIOS"

# Palabras clave para clasificar automáticamente archivos en 00_INFORMACION_GENERAL
KEYWORDS_INFO_GENERAL = [
    "silabo", "sílabo", "syllabus",
    "plan calendario", "calendario", "cronograma",
    "guia del estudiante", "guía del estudiante", "guia", "guía",
    "reglamento", "presentacion del curso", "presentación del curso",
    "formula", "fórmula de evaluacion", "evaluaciones del curso"
]

# Extensiones de archivos de interés para descarga
SUPPORTED_EXTENSIONS = {
    ".pdf", ".pptx", ".ppt", ".docx", ".doc",
    ".xlsx", ".xls", ".zip", ".rar", ".txt", ".csv"
}
