# 🎓 Blackboard CLI (UPC) — AI Study Notebook Sync

Herramienta de consola moderna y profesional para **Blackboard Ultra (UPC)**. Sincroniza tus cursos, materiales semanales, evaluaciones y anuncios oficiales, organizándolos en **Cuadernos de Estudio en Markdown** listos para ser leídos por ti o por cualquier Inteligencia Artificial (Antigravity, Claude, ChatGPT, Gemini, etc.).

---

## ⚡ Inicio Rápido (Sin complicaciones)

No necesitas configurar entornos manualmente. El programa incluye gestores automáticos para Windows y macOS/Linux.

1. **Descarga y descomprime:**
   - Descarga el archivo `Blackboard-CLI.zip` desde la sección de **Releases** de este repositorio y descomprímelo en cualquier carpeta de tu equipo.
2. **Ejecutar:**
   - **En Windows:** Haz doble clic en **`BlackboardCLI-v2.1.1-Windows.bat`**.
   - **En Mac:** Haz doble clic en **`BlackboardCLI-v2.1.1-macOS.command`** (o en la terminal: `./BlackboardCLI-v2.1.1-macOS.command`).
   - **En Linux:** Abre la terminal en la carpeta y ejecuta **`./BlackboardCLI-v2.1.1-Linux.sh`**.
   - *Nota de la primera vez:* En su primer arranque, el programa creará automáticamente un entorno virtual aislado (`.venv`) e instalará las librerías necesarias. **No dejará ningún residuo en tu sistema.**
3. **Iniciar Sesión:**
   - En el menú principal, selecciona la opción `[5] login`.
   - Se abrirá una ventana de navegador donde podrás ingresar con tu correo UPC (`@upc.edu.pe`), contraseña institucional y confirmar tu verificación en dos pasos (2FA).
   - ¡Listo! Tu sesión quedará guardada de forma segura localmente.

---

## 🖥️ Menú Interactivo

Al iniciar la aplicación, verás la consola interactiva con las siguientes opciones:

| Opción | Comando | Descripción |
| :---: | :--- | :--- |
| `[1]` | `sync` | **Sincronizador:** Permite descargar todo el semestre o elegir un curso y semana específica. |
| `[2]` | `agenda` | **Radar de Evaluaciones:** Lista exámenes, tareas y fechas de entrega ordenadas cronológicamente. |
| `[3]` | `cursos` | **Asignaturas:** Tabla con tus cursos activos del ciclo y sus códigos. |
| `[4]` | `status` | **Diagnóstico:** Revisa el estado de la conexión con el servidor Ultra y tu perfil de estudiante. |
| `[5]` | `login` | **Iniciar Sesión:** Abre el navegador para autenticarte vía Microsoft 365 / SSO. |
| `[6]` | `logout` | **Cerrar Sesión:** Borra de inmediato las credenciales y cookies locales de tu PC. |
| `[7]` | `package`| **Empaquetar:** Genera un archivo ZIP limpio y seguro para compartir con tus compañeros. |
| `[0]` | `exit` | Cierra la aplicación. |

> 💡 **Tip de Navegación:** Dentro de los menús de sincronización puedes escribir **`v`** en cualquier momento para volver a la pantalla anterior sin cerrar el programa.

---

## 📁 Estructura de los "Cuadernos de Estudio" Generados

Al sincronizar, se creará una carpeta llamada `cuadernos/` con una estructura limpia y estandarizada:

```text
cuadernos/
├── RESUMEN_SEMESTRE_IA.md        <-- 🧠 Índice general del ciclo con radar de exámenes
└── [CODIGO] Nombre del Curso/
    ├── CUADERNO_CURSO.md         <-- 📓 Cuaderno maestro del curso con fórmulas y enlaces
    ├── 00_INFORMACION_GENERAL/   <-- 📄 Sílabos, normas del curso y plan calendario
    ├── 01_EVALUACIONES_Y_EXAMENES/
    │   └── agenda_evaluaciones.md <-- 📅 Fechas, temas de evaluaciones y ponderaciones
    ├── 02_MATERIALES_Y_CLASES/   <-- 📚 Contenido organizado por Semanas o Unidades
    │   ├── Semana 01/
    │   └── Semana 02/
    └── 03_ANUNCIOS/
        └── historial_anuncios.md <-- 📢 Comunicados oficiales del profesor
```

---

## 🤖 ¿Cómo estudiar con IA usando estos cuadernos?

Una vez descargados tus cuadernos, puedes abrir la carpeta en tu editor favorito (Cursor, VS Code, Obsidian) o arrastrar los archivos a cualquier IA:

* **Preguntar por evaluaciones:**
  > *"¿Qué evaluaciones tengo en las próximas dos semanas y cuál tiene mayor peso porcentual?"*  
  *(La IA leerá `cuadernos/RESUMEN_SEMESTRE_IA.md` y las agendas).*
* **Estudiar temas semanales:**
  > *"Explícame de forma sencilla el contenido teórico de la Semana 03 de este curso."*  
  *(La IA consultará los archivos Markdown de la semana seleccionada).*
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

---

## 📄 Licencia

Este proyecto está protegido bajo la licencia **GNU General Public License v3.0 (GPLv3)**.  
Consulta el archivo [LICENSE](LICENSE) para más detalles.

*Está permitido el uso libre, estudio y mejora del código, pero cualquier derivado debe permanecer bajo la misma licencia abierta, garantizando siempre el crédito al autor original y prohibiendo la apropiación o cierre del software.*
