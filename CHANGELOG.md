# Registro de Cambios (Changelog)

Todas las modificaciones notables de este proyecto serán documentadas en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/)
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [3.0.0] - 2026-09-30

### ✨ Añadido
- **Motor AnyDoc de Conversión a Markdown Integrado (`firecrawl-anydoc`):**
  - Conversión automática y ultrarrápida de documentos (`.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, etc.) a formato Markdown limpio (`.md`).
  - Coexistencia *side-by-side*: cada documento original conserva su gemelo `.md` adyacente en el mismo directorio del curso y en `gemini_notebook/`.
  - Motor Rust 100% local sin costos ni dependencias de APIs en la nube. Fallback silencioso y resiliente ante archivos no estándar o corruptos.
- **Generación Automática de Skills para Agentes IA (`SKILL.md`):**
  - Creación de `SKILL.md` y `.skills/estudio-curso/SKILL.md` con frontmatter YAML dentro de cada cuaderno de curso.
  - Instrucciones especializadas para Antigravity, Claude, ChatGPT, Gemini y Cursor que obligan al modelo a priorizar los archivos `.md` de AnyDoc, ahorrando más del 90% de ventana de contexto en consultas.
  - Mapeo de reglas para exámenes (`agenda_evaluaciones.md`), sílabo oficial y temarios por semana.
  - Generación de `SKILL.md` maestro en la raíz de `cuadernos/` (`.skills/estudio-semestre/SKILL.md`) coordinado con `RESUMEN_SEMESTRE_IA.md`.
- **Control Híbrido y Motor de UI Desacoplado (`src/terminal_ui.py`):**
  - Navegación instantánea por teclado con flechas `[▲/▼]` con rotación cíclica suave (*wrap-around*) y selección con `Enter`.
  - Buffer de texto simultáneo en tiempo real: teclea números o comandos (`sync`, `o`, `status`, etc.) con borrado `Backspace`, viendo cómo el cursor salta a la opción en vivo.
  - Mecanismo de resiliencia con fallback automático en entornos no interactivos o pipes (`sys.stdin.isatty() == False`) recurriendo a `Prompt.ask()`.
  - Barra de tips didácticos rotativos en español al pie de los menús para enseñar trucos del programa y flujos de estudio con IA.
  - Experiencia unificada de `hybrid_select` en el Menú Principal, Selector de Cursos, Selector de Semanas, Selector de Universidad y Exportador a Gemini Notebook.
- **Tamaño de Ventana Óptimo por Defecto (120x40):**
  - Auto-ajuste de consola a 120 columnas por 40 líneas para mostrar el banner ASCII en paralelo sin scroll vertical.
- **Accesos Rápidos de Sistema (`[o]`, `[g]`, `[w]`):**
  - `[o]` / `abrir`: Abre la carpeta de cuadernos en el Explorador de Windows o Finder de Mac mediante la nueva utilidad `open_in_file_manager` en `src/config.py`.
  - `[g]` / `gemini`: Acceso rápido a las notas optimizadas para arrastrar a Google NotebookLM con tips interactivos.
  - `[w]` / `web`: Abre directamente el aula virtual de la universidad activa en el navegador web habitual.
- **Suite de Pruebas Unitarias de UI (`tests/test_terminal_ui.py`):**
  - Cobertura completa de lectura de eventos de teclado, wrap-around de flechas, limpieza de buffer, edición por backspace, fallback TTY y apertura en gestor de archivos.
- **Notificación y actualizador de versión integrado:**
  - Consulta automática no bloqueante de lanzamientos en GitHub (`https://github.com/jwd3t/Blackboard-CLI/releases/`).
  - Si existe una versión más reciente, se muestra un aviso destacado `[u] ✨ update` ubicado inmediatamente debajo de `[0] exit` en el menú interactivo y en la barra de subtítulo.
  - El comando `update` (o presionar `u`) muestra los detalles de la nueva versión y abre automáticamente la página oficial de releases en el navegador predeterminado.
  - Diagnóstico (`cmd_status`) enriquecido con el estado de la versión (`(Al día)` o `(¡Nueva versión disponible!)`).
  - Caché local con TTL (`.session_data/update_check.json`) y timeout seguro (2s) para garantizar velocidad instantánea en la interfaz.
- **Estandarización de confirmaciones en español (`s/n`):**
  - Nueva clase `SpanishConfirm` para Rich que estandariza todas las preguntas de confirmación del programa en `[s/n] (s):` o `[s/n] (n):`.
  - Acepta de forma natural y tolerante respuestas como `s`, `si`, `sí`, `y`, `yes`, `n`, `no`.
  - Soluciona inconsistencias donde algunos menús o prompts solicitaban confirmar con `Y` y otros con `S`.
- **Soporte Multi-Institución y Genérico:**
  - Soporte nativo preconfigurado para múltiples universidades e institutos: **UPC** (`aulavirtual.upc.edu.pe`), **UCV** (`ucv.blackboard.com`), **UPN** (`upn.blackboard.com`) y **SENATI** (`senati.blackboard.com`).
  - Detección de atajos y dominios de SENATI (`senati`, `senati.pe`, `aulavirtual.senati.edu.pe`).
  - Soporte genérico para **cualquier servidor Blackboard Learn / Ultra**: permite ingresar la URL de cualquier institución y valida automáticamente la compatibilidad con los endpoints de Blackboard Learn REST API (`/learn/api/public/v1/system/version`).
- **Resiliencia de navegador con fallback automático (Fix `spawn UNKNOWN`):**
  - Nuevo lanzador de navegador en cascada: si Chromium es bloqueado por antivirus o falla con `spawn UNKNOWN`, detecta y utiliza de inmediato **Microsoft Edge** (`channel="msedge"`) o **Google Chrome** (`channel="chrome"`) preinstalados en Windows.
  - Protección ante cierres inesperados de la ventana del navegador sin interrumpir ni crashear el programa.
- **Aislamiento completo de sesiones por universidad:**
  - Cookies persistentes separadas por institución (`cookies_upc.json`, `cookies_senati.json`, etc.) y perfiles de navegador independientes (`browser_upc/`, `browser_senati/`).
  - Cambiar de universidad no cierra la sesión ni invalida las credenciales de las otras.
  - Caché de descargas independiente por institución (`downloads_cache_<inst>.json`).
- **Selector interactivo de institución:**
  - Nueva opción en el menú interactivo `[8] institucion` y argumento CLI `institucion` para alternar de manera fluida entre instituciones o configurar una URL personalizada.
- **Headers y diagnóstico dinámicos:**
  - El banner, barra de estado y tabla de diagnóstico reflejan el nombre de la institución activa, URL base y color temático.
- **Reorganización modular limpia (`src/` y `tests/`):**
  - Todo el código fuente (`cli.py`, `auth.py`, `config.py`, `organizer.py`, `ultra_client.py`, `requirements.txt`) se agrupó dentro de la carpeta `src/`.
  - Las pruebas unitarias se estructuraron dentro del directorio `tests/`.
  - La raíz del proyecto y el paquete descargable ZIP quedan despejados visualmente con los ejecutables y documentación destacados (`BlackboardCLI-Windows.bat`, etc.), sin archivos de código dispersos.
- **Inyección de dependencias y desacoplamiento (SOLID):**
  - `UltraClient` y `CourseNotebookOrganizer` ahora permiten inyectar URLs base, rutas de caché y directorios de salida arbitrarios.
- **Retrocompatibilidad transparente:**
  - Detección automática y migración de sesiones existentes de la versión 2.x (`cookies.json` y `downloads_cache.json`).

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
