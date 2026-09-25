# Dredd: Juez de Trabajos Prácticos y Orquestador Docente

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

Orquestador docente de evaluación masiva, autograding multicanal y gestión de entregas en C (compatible con **GitHub Classroom** y **Moodle**).

---

## 🎯 Alcance

### Qué cubre
- Orquestación central de corrección masiva de trabajos prácticos y exámenes de programación en C.
- Ingesta y normalización de entregas provenientes de Moodle (ZIPs) y GitHub Classroom (repositorios Git).
- Calificación ponderada y gestión de base de datos relacional SQLite (`dredd.db`).
- Detección de plagio y copias entre estudiantes mediante algoritmo de huellas digitales de Winnowing.
- Re-evaluación incremental rápida (`dredd rerun --failed-only` y `--dry-run`).
- Generación de reportes de devolución individual en Markdown y actas consolidadas.

### Qué no cubre (Límites y Delegación)
- Compilación directa y traducción pedagógica de errores (delega prioritariamente en `daedalus` y `esper`, con fallback a GCC).
- Ejecución aislada de binarios (delega en `nostromo` y Bubblewrap, con fallback por cuotas `setrlimit`).
- Linter de reglas de cátedra y estilo (delega en `gaff` y `ripley`, con fallback a linter nativo Tree-Sitter AST).
- Creación y multiplexación de guías de ejercicios (delega en `deckard`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Linux (nativo o WSL). Python >= 3.10.

### Dependencias Externas y Binarios
- `sqlite3`, `git`, y herramientas del ecosistema en PATH (`daedalus`, `nostromo`, `ripley`).

### Integración en el Ecosistema
- CLI `dredd`. Hub central de calificación docente del ecosistema.

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

# Limpiar evaluaciones previas (carpetas rNi e informes generados)
dredd evaluate clean tp01
dredd evaluate clean tp01 alvarez_juan
dredd evaluate clean tp01 --dry-run   # Simulación sin borrar
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

#### Diagnóstico del Entorno y Ecosistema (`dredd doctor`)
Verifica la disponibilidad y estado de todas las dependencias nativas y herramientas hermanas del ecosistema Cátedra P1:

```bash
dredd doctor
```

#### Re-evaluación Rápida y Filtrada (`dredd rerun`)
Re-ejecuta evaluaciones sobre entregas previas sin repetir descargas o clones innecesarios, filtrando únicamente entregas que hayan fallado:

```bash
dredd rerun tp01 --failed-only --dry-run
```

#### Exportación de Actas SIU Guaraní (`dredd export-guarani`)
Genera planillas tabulares compatibles con SIU Guaraní bajo codificación UTF-8-SIG y separadores punto y coma:

```bash
dredd export-guarani tp01 -o actas_tp01.csv
```

#### Multiplexación Docente de Prácticos (`dredd multiplex`)
Alias de conveniencia que delega en Deckard la generación de variantes combinatorias y asignación determinista por estudiante:

```bash
dredd multiplex --spec matriz.yaml -o dist/multiplex/
```

#### Auditoría de Repositorios y Makefiles
Comandos especializados para auditoría de commits de estudiantes y Makefiles:

```bash
dredd audit-git tp01 --json
dredd audit-makefile tp01 --json
dredd late-penalty tp01 --deadline 2026-09-20 --json
dredd typology tp01 --json
dredd eval-stability tp01 --runs 3 --json
```

---

## 🧱 Arquitectura del Paquete

```
src/dredd/
├── __init__.py          # Metadatos del paquete (__version__)
├── cli.py               # Punto de entrada Typer y catálogo de comandos CLI
└── core/
    ├── ast_checker.py   # Linter nativo Tree-Sitter AST de reglas P1 (0xXXXXh)
    ├── baseline.py      # Detección de plantillas de base y omisión de ejercicios sin tocar
    ├── binary_check.py  # Detección y purga preventiva de binarios prohibidos
    ├── boiler_strip.py  # Limpieza de código boilerplate para comparaciones
    ├── cache.py         # Gestión de caché local
    ├── cohort_bench.py  # Métricas comparativas y benchmarking de la cohorte
    ├── compiler.py      # Orquestador de compilación C (Daedalus / Esper / GCC / Make)
    ├── config.py        # Configuración declarativa (dredd.yaml) y políticas de chequeo
    ├── dashboard.py     # Generación de tablero estadístico de rendimiento
    ├── db.py            # Persistencia relacional SQLite (.metadata.db)
    ├── diff_submission.py # Comparador diferencial entre entregas y revisiones
    ├── doctor.py        # Diagnóstico del entorno, dependencias y kernel namespaces
    ├── ecosystem.py     # Resolución unificada de herramientas y binarios hermanos
    ├── eval_clean.py    # Limpieza estructurada de carpetas de evaluación
    ├── exporter.py      # Exportación a planillas Moodle, ZIPs y métricas
    ├── feedback_pack.py # Ensamblador de paquetes de retroalimentación
    ├── feedback_template.py # Plantillas de feedback enriquecido
    ├── fuzz_gen.py      # Generador de inputs aleatorios deterministas y fuzzing
    ├── git_anomaly.py   # Auditoría de anomalías en commits de estudiantes
    ├── git_ops.py       # Gestión local de repositorios Git de entregas
    ├── github_api.py    # Integración con GitHub Classroom vía gh CLI
    ├── guarani.py       # Exportación de actas compatibles con SIU Guaraní
    ├── guide_integration.py # Adaptadores para guías docentes de Deckard
    ├── ingest.py        # Ingesta masiva de entregas multi-encoding (Moodle)
    ├── late_penalty.py  # Cálculo de penalizaciones por entregas fuera de término
    ├── makefile_audit.py # Auditoría estática de sintaxis y reglas de Makefiles
    ├── makefile_eval.py # Evaluación de proyectos con Makefiles por ejercicio
    ├── mapping.py       # Mapeo heurístico e interactivo entre entregas y guías
    ├── moodle.py        # Adaptadores y utilidades de ingesta/exportación Moodle
    ├── oral_guide.py    # Generador de preguntas conceptuales para defensas orales
    ├── output_sanitizer.py # Sanitizador de secuencias ANSI y volcados extensos
    ├── plagiarism.py    # Detector de plagio por algoritmo Winnowing
    ├── plagiarism_history.py # Comparación contra cohortes y cursadas previas
    ├── reformat.py      # Normalización a esquema canónico de revisiones rN/
    ├── report_export.py # Conversor de Markdown a HTML autocontenido y PDF
    ├── reporter.py      # Ensamblador modular de informes de devolución pedagógica
    ├── ripley_client.py # Cliente de integración con Ripley / Linter AST nativo
    ├── sandbox.py       # Aislamiento por namespaces (bwrap), setrlimit y evasión
    ├── smith_adversary.py # Evaluador adversarial de robustez
    ├── stability_eval.py # Auditoría de no-determinismo y estabilidad de pruebas
    ├── submission_typology.py # Clasificación tipológica de estilos de entrega
    └── valgrind.py      # Runner y parser de reportes XML de Valgrind
```
