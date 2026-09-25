# Registro de Cambios (Changelog)

Todas las modificaciones notables de este proyecto serán documentadas en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/)
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [2.2.0] - 2026-09-25

### ✨ Añadido
- **Exportación unificada para Gemini Notebook / NotebookLM:** Nuevo comando `notebook` que genera una carpeta plana (`gemini_notebook/`) con todos los archivos de estudio ordenados cronológicamente (`uX_sXX_YY_archivo.ext`) listos para ser arrastrados a Gemini.

## [2.1.1] - 2026-09-24

### ✨ Añadido
- **Verificación previa en disco:** Antes de emitir cualquier petición de red o mostrar el spinner de descarga, se comprueba si el archivo ya existe físicamente en disco y tiene un tamaño válido (`> 0 bytes`).
- **Caché persistente de descargas:** Nuevo archivo de caché local (`.session_data/downloads_cache.json`) que mapea URLs de Blackboard Ultra a sus nombres de archivo reales, evitando consultas HTTP innecesarias.
- **Diferenciación visual en consola:**
  - `⚡` *(color atenuado)* para recursos que ya estaban descargados previamente y al día (`ya descargado`).
  - `💾` *(color brillante)* para nuevos archivos descargados.
- **Rutas de origen en consola (Breadcrumbs):** Los logs ahora muestran la jerarquía de carpetas/semanas de origen (`format_display_path`), ej: `Semana 5 _ Storage › Recursos de aprendizaje ➔ archivo.pdf`.
- **Barra de progreso interactiva:** Integración de `Rich.Progress` con spinner animado, barra de progreso gráfica y contador de tiempo transcurrido en sincronizaciones por curso y sección.
- **Lanzadores descriptivos por plataforma:** Se renombraron los scripts de inicio genéricos a `BlackboardCLI-v{VERSION}-{Plataforma}`:
  - `BlackboardCLI-v2.1.1-Windows.bat` *(Windows)*
  - `BlackboardCLI-v2.1.1-macOS.command` *(macOS)*
  - `BlackboardCLI-v2.1.1-Linux.sh` *(Linux)*
- **Soporte multiplataforma completo:** Detección automática de Python 3.10+, creación de entorno virtual `.venv` aislado e instalación desatendida de dependencias y Playwright Chromium tanto en macOS/Linux como en Windows.
- **Salida elegante con `Ctrl+C`:** La interrupción por teclado (`KeyboardInterrupt`) en `cli.py` ahora muestra una despedida amigable y sale limpiamente sin mostrar trazas de error de Python.
- **Empaquetado inteligente:** `package.py` ahora empaqueta dinámicamente según la versión actual, incluyendo automáticamente el `CHANGELOG.md` y los lanzadores de cada plataforma.
- **Limpieza de sistema en Git:** Se agregaron `.DS_Store` y `Thumbs.db` al `.gitignore` para evitar archivos temporales generados por Finder (macOS) y el explorador de Windows.

### ⚡ Rendimiento
- **0 peticiones redundantes:** La resincronización de un curso con materiales ya descargados pasa de tomar ~30 segundos a menos de 1 segundo, eliminando tráfico innecesario hacia los servidores de Blackboard.
- **Normalización canónica de URLs:** Unificación y limpieza de entidades HTML (`&amp;` a `&`) y parámetros de consulta para evitar duplicidad de solicitudes en enlaces embebidos de `bbcswebdav`.

### 🐛 Corregido
- **Duplicidad de logs y descargas por documento:** Solucionado el problema donde archivos como PDFs y Word se imprimían hasta 3 veces consecutivas debido a los bloques hijos internos de documentos Ultra (`ultradocumentbody`).
- **Descargas incompletas:** Detección de archivos corruptos o de 0 bytes para forzar su re-descarga limpia si fueron interrumpidos previamente.

---

## [2.0.0] - 2026-09-22

> 💡 **Nota del desarrollador: El mito de la v1.0.0 y por qué arrancamos en la 2.0.0**  
> La versión 1.0.0 existió... pero era fea con ganas: una terminal en blanco y negro sin piedad que descargaba absolutamente todo el semestre a la fuerza sin darte a elegir nada.  
> En un ataque de inspiración (y cafeína), se rehizo todo el mismo día: interfaz visual pro con su logo, radar de evaluaciones, menús interactivos y la opción de elegir qué curso o semana descargar.  
> ¿El resultado? La v1.0.0 se convirtió oficialmente en *lost media* el mismísimo día de su creación, porque el proyecto saltó de 1.0 a 2.0 en cuestión de horas. No quedó de otra que inaugurar el primer commit directamente como `v2.0.0`. 🚀

### ✨ Lanzamiento Inicial v2.0
- **Cuadernos de Estudio para IA:** Estructuración automática de todo el contenido académico en carpetas organizadas y archivos Markdown listos para ser consumidos por modelos de IA (Claude, ChatGPT, Antigravity, Gemini).
- **Inicio de sesión interactivo:** Autenticación segura mediante navegador automatizado con Playwright Chromium y guardado de cookies locales en `.session_data/`.
- **Radar de evaluaciones:** Extracción y compilación automática de fechas de entrega, exámenes parciales/finales y rúbricas en `01_EVALUACIONES_Y_EXAMENES/agenda_evaluaciones.md`.
- **Resumen general del ciclo:** Generación del archivo maestro `RESUMEN_SEMESTRE_IA.md` con el índice integral de asignaturas, evaluaciones pendientes y rutas de materiales.
- **Empaquetado seguro (`package`):** Generador de archivos ZIP para compartir el proyecto sin incluir credenciales privadas, cookies ni materiales descargados.
- **Lanzador automático en Windows:** Script `run.bat` con resolución de alias de Microsoft Store, creación automática de `.venv` e instalación de dependencias.

---

[2.1.1]: https://github.com/jwd3t/Blackboard-CLI/compare/2.0.0...2.1.1
[2.0.0]: https://github.com/jwd3t/Blackboard-CLI/releases/tag/2.0.0
