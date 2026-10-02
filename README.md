# 🎓 Blackboard CLI — AI Study Notebook Sync

Herramienta de consola moderna y profesional para **Blackboard Ultra Multi-Institución** (UPC, UCV, UPN, SENATI y cualquier aula virtual Blackboard Learn / Ultra). Sincroniza tus cursos, materiales semanales, evaluaciones y anuncios oficiales, organizándolos en **Cuadernos de Estudio en Markdown** listos para ser leídos por ti o por cualquier Inteligencia Artificial (Antigravity, Claude, ChatGPT, Gemini, etc.).

---

## ⚡ Inicio Rápido (Sin complicaciones)

No necesitas configurar entornos manualmente. El programa incluye gestores automáticos para Windows y macOS/Linux.

1. **Descarga y descomprime:**
   - Descarga el archivo [Blackboard-CLI.zip](https://github.com/jwd3t/Blackboard-CLI/releases) desde la sección de **Releases** de este repositorio y descomprímelo en cualquier carpeta de tu equipo.
2. **Ejecutar:**
   - **En Windows:** Haz doble clic en **`BlackboardCLI-v*.bat`** (ej. `BlackboardCLI-v3.1.1-Windows.bat`).
   - **En Mac:** Haz doble clic en **`BlackboardCLI-v*.command`** (o en la terminal: `./BlackboardCLI-v*.command`).
   - **En Linux:** Abre la terminal en la carpeta y ejecuta **`./BlackboardCLI-v*.sh`**.
   - *Nota de la primera vez:* En su primer arranque, el programa creará automáticamente un entorno virtual aislado (`.venv`) e instalará las librerías necesarias. **No dejará ningún residuo en tu sistema.**
3. **Elegir Institución e Iniciar Sesión:**
   - Por defecto está configurado para la **UPC**, pero puedes cambiar a **SENATI**, **UCV**, **UPN** o **cualquier enlace personalizado de Blackboard** usando la opción `[8] institucion`.
   - Selecciona `[5] login`. Se abrirá una ventana de navegador donde podrás ingresar con tu cuenta institucional, contraseña y confirmar tu verificación en dos pasos (2FA).
   - *Resiliencia de navegador:* Si tu antivirus bloquea Chromium, el sistema detecta y utiliza automáticamente Microsoft Edge o Google Chrome instalados en tu equipo.
   - ¡Listo! Las credenciales y sesiones se guardan de forma aislada e independiente para cada institución.

---

## 🖥️ Control Híbrido y Menú Interactivo

La CLI cuenta con una experiencia de control híbrido moderna:
* **Navegación instantánea:** Puedes desplazarte con las flechas `[▲/▼]` (con rotación cíclica suave) y presionar `Enter` para elegir.
* **Barra de texto en tiempo real:** Simultáneamente, puedes escribir números o nombres de comando (`sync`, `o`, `2`, `exit`) con borrado `Backspace`, viendo en vivo cómo el selector salta a tu opción.
* **Consejos didácticos:** Barra de tips en español al pie del menú para aprender atajos y flujos de estudio con IA.

| Opción | Comando | Descripción |
| :---: | :--- | :--- |
| `[1]` | `sync` | **Sincronizador:** Permite descargar todo el semestre o elegir un curso y semana específica. |
| `[2]` | `agenda` | **Radar de Evaluaciones:** Lista exámenes, tareas y fechas de entrega ordenadas cronológicamente. |
| `[3]` | `cursos` | **Asignaturas:** Tabla con tus cursos activos del ciclo y sus códigos. |
| `[4]` | `status` | **Diagnóstico:** Revisa el estado de la conexión con el servidor Ultra, institución activa y perfil. |
| `[5]` | `login` | **Iniciar Sesión:** Abre el navegador para autenticarte vía SSO / 2FA en la institución activa. |
| `[6]` | `logout` | **Cerrar Sesión:** Borra de inmediato las credenciales y cookies de la institución activa. |
| `[7]` | `notebook`| **Exportar a Gemini Notebook:** Genera una carpeta plana (`gemini_notebook/`) optimizada para NotebookLM. |
| `[8]` | `institucion`| **Cambiar Institución:** Alterna entre UPC, UCV, UPN, SENATI o agrega cualquier URL de Blackboard Learn. |
| **Accesos Rápidos** | | |
| `[o]` | `abrir` | **Explorador:** Abre la carpeta raíz de `cuadernos/` en el explorador de archivos nativo. |
| `[g]` | `gemini` | **Notas IA:** Abre la carpeta de cuadernos con tips para arrastrar a Google NotebookLM. |
| `[w]` | `web` | **Aula Virtual Web:** Abre el Blackboard institucional activo directamente en tu navegador web. |
| `[0]` | `exit` | Cierra la aplicación. |

> 💡 **Tip de Navegación:** Dentro de los menús de sincronización puedes escribir **`v`** en cualquier momento para volver a la pantalla anterior sin cerrar el programa.

---

## 📁 Estructura de los "Cuadernos de Estudio" Generados

Al sincronizar, se creará una carpeta llamada `cuadernos/` con una estructura limpia y estandarizada:

```text
cuadernos/
├── SKILL.md                      <-- 🧠 Guía maestra del semestre para Agentes IA
├── RESUMEN_SEMESTRE_IA.md        <-- 📊 Índice general del ciclo con radar de exámenes
└── [CODIGO] Nombre del Curso/
    ├── SKILL.md                  <-- 🎓 Skill de IA del curso (prioriza AnyDoc .md)
    ├── CUADERNO_CURSO.md         <-- 📓 Cuaderno maestro del curso con fórmulas y enlaces
    ├── 00_INFORMACION_GENERAL/   <-- 📄 Sílabos, normas del curso y plan calendario (.md y original)
    ├── 01_EVALUACIONES_Y_EXAMENES/
    │   └── agenda_evaluaciones.md <-- 📅 Fechas, temas de evaluaciones y ponderaciones
    ├── 02_MATERIALES_Y_CLASES/   <-- 📚 Contenido organizado por Semanas o Unidades
    │   ├── Semana 01/
    │   │   ├── diapositivas.pptx <-- 📦 Archivo original
    │   │   └── diapositivas.md   <-- ⚡ Versión Markdown limpia vía AnyDoc
    │   └── Semana 02/
    ├── 03_ANUNCIOS/
    │   └── historial_anuncios.md <-- 📢 Comunicados oficiales del profesor
    └── gemini_notebook/          <-- 🤖 Carpeta plana con prefijos uX_sXX (solo materiales originales y lecturas nativas) lista para NotebookLM
```

---

## 🤖 ¿Cómo estudiar con IA usando estos cuadernos?

* **Detección automática de Skills (`SKILL.md`):**
  Al abrir la carpeta en herramientas como **Antigravity**, **Cursor** o **Claude Code**, el agente leerá automáticamente el archivo `SKILL.md` del curso, aprendiendo a priorizar los archivos `.md` de AnyDoc, respetando los temarios y resolviendo dudas con respuestas precisas.
* **Velocidad y Ahorro de Tokens con AnyDoc:**
  Gracias a la conversión automática a `.md`, los modelos no necesitan procesar pesados binarios PPTX o PDFs, ahorrando hasta un 90% de ventana de contexto y respondiendo en segundos.
* **Preguntar por evaluaciones:**
  > *"¿Qué evaluaciones tengo en las próximas dos semanas y cuál tiene mayor peso porcentual?"*  
  *(La IA leerá `cuadernos/RESUMEN_SEMESTRE_IA.md` y las agendas).*
* **Estudiar temas semanales:**
  > *"Explícame de forma sencilla el contenido teórico de la Semana 03 de este curso."*  
  *(La IA consultará los archivos Markdown convertidos de la semana seleccionada).*
* **Consultar fórmulas de calificación:**
  > *"¿Cuánto necesito sacar en el examen final para aprobar el curso según la fórmula del sílabo?"*

---

## 🔒 Privacidad y Seguridad

* **Tus credenciales nunca se comparten:** Ni tus contraseñas, ni tus cookies de sesión se suben a ningún servidor externo. Todo se ejecuta 100% de forma local en tu máquina.
* **El comando `package` es seguro:** Si deseas compartir la herramienta con un amigo, la opción `[7] package` genera un ZIP que automáticamente excluye tus archivos personales, notas y sesiones.

---

## 🛠️ Requisitos del Sistema

* **Windows:** Windows 10 o Windows 11 (64 bits).
* **macOS:** macOS Catalina (10.15) o superior.
* Tener Python 3.9 o superior instalado (Python 3.10+ recomendado; en Windows marcar *"Add python.exe to PATH"*; en Mac instalar vía `brew install python` o python.org). Los scripts de inicio se encargarán de todo lo demás.

### 💻 Ejecución directa con Python (Desarrolladores)
Si clonas el repositorio y deseas ejecutar el código directamente sin los lanzadores `.bat`/`.sh`:
```bash
pip install -r src/requirements.txt
python src/cli.py
```

Para correr las pruebas unitarias:
```bash
python tests/test_multi_institution.py
python tests/test_gemini_export.py
```

---

## 📄 Licencia

Este proyecto está protegido bajo la licencia **GNU General Public License v3.0 (GPLv3)**.  
Consulta el archivo [LICENSE](LICENSE) para más detalles.

*Está permitido el uso libre, estudio y mejora del código, pero cualquier derivado debe permanecer bajo la misma licencia abierta, garantizando siempre el crédito al autor original y prohibiendo la apropiación o cierre del software.*
