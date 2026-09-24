# Registro de Cambios (Changelog)

Todas las modificaciones notables de este proyecto serán documentadas en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/)
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [2.1.0] - 2026-09-24

### ✨ Añadido
- **Verificación previa de archivos locales:** Antes de iniciar cualquier llamada de red o mostrar el spinner de descarga, se comprueba si el archivo ya existe físicamente en disco y tiene un tamaño válido (`> 0 bytes`).
- **Caché persistente de descargas:** Nuevo archivo de caché local (`.session_data/downloads_cache.json`) que mapea URLs de Blackboard Ultra a sus nombres de archivo reales sin requerir peticiones HTTP intermedias.
- **Rutas de origen en consola (Breadcrumbs):** Los logs ahora muestran la jerarquía de carpetas/semanas de origen (`format_display_path`), ej: `Semana 5 _ Storage › Recursos de aprendizaje ➔ archivo.pdf`.
- **Diferenciación visual en consola:**
  - `⚡` *(color atenuado)* para recursos que ya estaban descargados y al día.
  - `💾` *(color brillante)* para nuevos archivos descargados.
- **Barra de progreso interactiva:** Integración de `Rich.Progress` con spinner animado, barra de progreso gráfica y contador de tiempo transcurrido en sincronizaciones por curso y sección.
- **Soporte multiplataforma completo:** Scripts `run.sh` y `run.command` para ejecución nativa en macOS y Linux con detección de Python 3.10+, creación de `.venv` e instalación automática de dependencias.

### ⚡ Rendimiento
- **0 peticiones redundantes:** La resincronización de un curso con materiales ya descargados pasa de tomar ~30 segundos a menos de 1 segundo, eliminando tráfico innecesario hacia los servidores de Blackboard.
- **Normalización canónica de URLs:** Unificación y limpieza de entidades HTML (`&amp;` a `&`) y parámetros de consulta para evitar duplicidad de solicitudes en enlaces embebidos de `bbcswebdav`.

### 🐛 Corregido
- **Duplicidad de logs y descargas por documento:** Eliminado el problema donde archivos como PDFs y Word se imprimían hasta 3 veces consecutivas debido a los bloques hijos internos de documentos Ultra (`ultradocumentbody`).
- **Descargas incompletas:** Detección de archivos corruptos o de 0 bytes para forzar su re-descarga limpia si fueron interrumpidos previamente.

---

## [2.0.0] - 2026-09-22

> 💡 **Nota del desarrollador: ¿Por qué el primer release es directamente la 2.0.0?**  
> Porque en el desarrollo se avanzó tanto a puro instinto, café y cero control de versiones, que para cuando alguien por fin se acordó de hacer `git init`, el proyecto ya estaba en su prime, graduado con honores y con arquitectura digna de una versión 2.0.  
> La legendaria versión 1.0 vive únicamente en nuestros corazones (y en carpetas olvidadas llamadas `proyecto_final_ahora_si_este_es_v2_final_final.zip`). 🚀

### ✨ Lanzamiento Inicial v2.0
- **Cuadernos de Estudio para IA:** Estructuración automática de todo el contenido académico en carpetas organizadas y archivos Markdown listos para ser consumidos por modelos de IA (Claude, ChatGPT, Antigravity, Gemini).
- **Inicio de sesión interactivo:** Autenticación segura mediante navegador automatizado con Playwright Chromium y guardado de cookies locales en `.session_data/`.
- **Radar de evaluaciones:** Extracción y compilación automática de fechas de entrega, exámenes parciales/finales y rúbricas en `01_EVALUACIONES_Y_EXAMENES/agenda_evaluaciones.md`.
- **Resumen general del ciclo:** Generación del archivo maestro `RESUMEN_SEMESTRE_IA.md` con el índice integral de asignaturas, evaluaciones pendientes y rutas de materiales.
- **Empaquetado seguro (`package`):** Generador de archivos ZIP para compartir el proyecto sin incluir credenciales privadas, cookies ni materiales descargados.
- **Lanzador automático en Windows:** Script `run.bat` con resolución de alias de Microsoft Store, creación automática de `.venv` e instalación de dependencias.
