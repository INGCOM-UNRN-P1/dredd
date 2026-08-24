# Dredd: Juez de Trabajos Prácticos y Orquestador Docente

Orquestador docente de evaluación masiva, autograding multicanal y gestión de entregas en C (compatible con **GitHub Classroom** y **Moodle**).

---

## 🚀 Instalación y Entorno

Dredd está desarrollado en Python 3.11+ con `typer` y `rich`.

```bash
# Instalación en modo desarrollo
cd dredd
uv sync --extra dev

# Ver catálogo de comandos
uv run dredd --help
```

---

## 🛠️ Flujos de Trabajo y Comandos

### 1. Flujo GitHub Classroom

#### Evaluación de Entregas (`dredd eval`)
Clona o actualiza el repositorio en `<actividad>-submissions/<estudiante>/`, ejecuta el análisis con el motor Ripley (o fallback nativo con reglas P1 de cátedra) y ensambla `${estudiante}.md`:

```bash
# Evaluar un estudiante puntual
dredd eval tp01 alvarez_juan

# Evaluar toda la cohorte presente en el workspace
dredd eval tp01 --all
```

#### Publicación de Feedback en GitHub (`dredd comment`)
Envía automáticamente el informe `${estudiante}.md` como comentario en el Pull Request abierto del estudiante utilizando GitHub CLI (`gh`):

```bash
dredd comment tp01 alvarez_juan --open
```

#### Creación / Reparación de Pull Requests (`dredd pr-fix`)
Reconstruye o abre el Pull Request de corrección en caso de que el estudiante no lo haya generado o haya alterado las ramas base:

```bash
dredd pr-fix tp01 alvarez_juan
```

---

### 2. Flujo Moodle

#### Ingesta Masiva y Versionado (`dredd moodle ingest`)
Descomprime el ZIP masivo de Moodle, normaliza la codificación a UTF-8 (soportando CP1252, ISO-8859-1 y UTF-8-sig), aplana las carpetas y genera versiones deterministas (`r1`, `r2`, ...) mediante hash SHA-256 en `.metadata.db`:

```bash
dredd moodle ingest entregas_tp01.zip
```

#### Mapeo Interactivo de Archivos (`dredd map`)
Vincula heurísticamente o mediante interfaz interactiva los archivos fuente `.c` de los estudiantes con los testcases correspondientes, guardando las reglas en `mappings.json`:

```bash
dredd map tp01_1228009 -e ejercicio1 -e ejercicio2 --auto
```

#### Exportación de Calificaciones y Dashboard (`dredd export` / `dredd moodle export`)
Genera el archivo CSV compatible con el Libro de Calificaciones de Moodle, el ZIP de retroalimentación masiva para subir al aula virtual y el reporte `dashboard.md` con estadísticas de la cohorte:

```bash
# Exportación completa (CSV + ZIP + Dashboard)
dredd export tp01_1228009

# Exportación puntual de planilla CSV
dredd moodle export -e tp01 -o calificaciones.csv
```

---

### 3. Herramientas de Auditoría y Reportes

#### Detección de Plagio con Winnowing (`dredd plagiarism`)
Calcula la matriz de similitud de código fuente normalizado en todas las entregas descargadas utilizando el algoritmo Winnowing:

```bash
dredd plagiarism tp01_1228009 --threshold 0.70
```

#### Conversión de Informes a HTML / PDF (`dredd export-report`)
Convierte informes Markdown a HTML enriquecido autocontenido (con CSS embebido) o PDF con formato de imprenta (generación pura en Python sin dependencias externas pesadas):

```bash
# Exportar a HTML
dredd export-report tp01_1228009/alvarez_juan/alvarez_juan.md --format html

# Exportar a PDF
dredd export-report tp01_1228009/alvarez_juan/alvarez_juan.md --format pdf
```

---

## 🧱 Arquitectura del Paquete

```
src/dredd/
├── cli.py               # Punto de entrada Typer y comandos CLI
└── core/
    ├── ast_checker.py   # Linter nativo de reglas P1 (0xXXXXh) y AST
    ├── db.py            # Capa SQLite de persistencia (.metadata.db)
    ├── exporter.py      # Generador de CSV Moodle, ZIP feedback y dashboard
    ├── git_ops.py       # Gestión de caché local de repositorios de estudiantes
    ├── github_api.py    # Integración con gh CLI (PRs y comentarios)
    ├── ingest.py        # Ingesta masiva de ZIPs Moodle, encodings y SHA-256
    ├── makefile_eval.py # Soporte para proyectos modulares con Makefiles
    ├── mapping.py       # Mapeo heurístico e interactivo (mappings.json)
    ├── moodle.py        # Adaptadores y utilitarios para Moodle
    ├── plagiarism.py    # Detector de similitud por huellas Winnowing
    ├── report_export.py # Conversor Markdown a HTML y PDF (zero-dependencies)
    ├── reporter.py      # Ensamblador de informes Markdown modulares
    └── ripley_client.py # Cliente de integración con el motor stateless Ripley
```
