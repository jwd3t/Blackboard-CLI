# 📚 Blackboard Ultra Sync (UPC) - Cuadernos de Estudio para IA

Herramienta en consola para **Blackboard Ultra (UPC)** que extrae automáticamente tus cursos, materiales, anuncios y evaluaciones, organizándolos en una estructura estandarizada de **"Cuadernos de Estudio"** optimizada tanto para ti como para cualquier modelo de Inteligencia Artificial.

---

## 🚀 Inicio Rápido

### Opción 1: Ejecutar con el archivo por lotes (Recomendado en Windows)
Haz doble clic en `run.bat` o ejecútalo desde tu terminal:
```powershell
.\run.bat
```

### Opción 2: Usar el entorno virtual directamente
```powershell
.\.venv\Scripts\activate
python cli.py
```

---

## 🧭 Comandos Disponibles

| Comando | Descripción |
| :--- | :--- |
| `python cli.py` | Abre el **Menú Interactivo** con opciones numéricas. |
| `python cli.py login` | Abre una ventana de Chromium para ingresar con tu cuenta UPC (`@upc.edu.pe`) y confirmar 2FA. |
| `python cli.py status` | Muestra el estado de la conexión y los datos del estudiante autenticado. |
| `python cli.py courses` | Muestra la tabla de cursos en los que estás matriculado actualmente. |
| `python cli.py agenda` | Muestra el calendario unificado de exámenes, entregas y tareas pendientes. |
| `python cli.py sync` | **Descarga y genera automáticamente los cuadernos** (archivos, sílabos, rúbricas). |

---

## 🗂️ Estructura de los "Cuadernos de Estudio" Generados

Cuando ejecutas `sync`, se genera la carpeta `cuadernos/` con esta organización:

```text
cuadernos/
├── RESUMEN_SEMESTRE_IA.md        <-- 🧠 Portada general para la IA (fechas de exámenes consolidadas)
└── [CODIGO] Nombre del Curso/
    ├── CUADERNO_CURSO.md         <-- 📓 Cuaderno central del curso con resumen y enlaces
    ├── 00_INFORMACION_GENERAL/   <-- 📄 Sílabos, planes calendario y fórmulas de evaluación
    │   ├── silabo.pdf
    │   └── plan_calendario.pdf
    ├── 01_EVALUACIONES_Y_EXAMENES/
    │   └── agenda_evaluaciones.md <-- 📅 Fechas, temas que vienen en los exámenes y rúbricas
    ├── 02_MATERIALES_Y_CLASES/   <-- 📚 Diapositivas PPTX, lecturas y prácticas por semana
    │   ├── Semana 01/
    │   └── Semana 02/
    └── 03_ANUNCIOS/
        └── historial_anuncios.md <-- 📢 Todos los comunicados oficiales del profesor
```

---

## 🤖 ¿Cómo interactúa la IA con esto?

1. Una vez ejecutado `python cli.py sync`, los archivos quedan en texto limpio (Markdown) y documentos reales en tu disco.
2. Puedes pedirle a **Antigravity** o a cualquier IA preguntas como:
   - *"¿Qué exámenes tengo esta semana y qué entra en cada uno?"* (La IA leerá `cuadernos/RESUMEN_SEMESTRE_IA.md` y `agenda_evaluaciones.md`).
   - *"Explícame el tema de la Semana 3 de Física"* (La IA leerá las diapositivas o documentos en `02_MATERIALES_Y_CLASES/Semana 03`).
   - *"¿Cuál es la fórmula para aprobar tal materia?"* (La IA leerá el sílabo en `00_INFORMACION_GENERAL/`).
