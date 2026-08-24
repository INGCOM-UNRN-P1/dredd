# Dredd: El Juez de los Trabajos Prácticos

Orquestador docente de evaluación masiva, autograding multicanal y gestión de entregas en C (compatible con GitHub Classroom y Moodle).

---

## 🚀 Instalación y Uso Rápido

Dredd está desarrollado en Python 3.11+ con `typer` y `rich`.

```bash
# Instalación en modo desarrollo
uv sync --extra dev

# Ver catálogo de comandos
uv run dredd --help
```

---

## 🛠️ Comandos Principales

### 1. Evaluación de Entregas (`dredd eval`)
Clona o actualiza el repositorio en `<ejercicio>-submissions/<estudiante>/`, ejecuta el análisis con Ripley (o fallback nativo con reglas P1 de cátedra) y ensambla `${estudiante}.md`:

```bash
# Evaluar un estudiante puntual
dredd eval tp01 alvarez_juan

# Evaluar toda la cohorte presente en el workspace
dredd eval tp01 --all
```

### 2. Publicación de Feedback en GitHub (`dredd comment`)
Envía automáticamente el informe `${estudiante}.md` como comentario en el Pull Request abierto del estudiante utilizando la GitHub CLI (`gh`):

```bash
dredd comment tp01 alvarez_juan --open
```

### 3. Creación / Reparación de Pull Requests (`dredd pr-fix`)
Reconstruye o abre el Pull Request de corrección en caso de que el estudiante no lo haya generado o haya roto la rama:

```bash
dredd pr-fix tp01 alvarez_juan
```

### 4. Detección de Plagio con Winnowing (`dredd plagiarism`)
Calcula la matriz de similitud de código fuente normalizado en todas las entregas descargadas:

```bash
dredd plagiarism tp01 --threshold 0.60
```

### 5. Integración con Moodle (`dredd moodle`)
```bash
# Ingesta masiva de archivo ZIP descargado de Moodle
dredd moodle ingest entregas_tp01.zip -e tp01

# Exportación de planilla CSV compatible con el calificador de Moodle
dredd moodle export -e tp01 -o notas_tp01.csv
```

---

## 🧱 Arquitectura del Proyecto

```
src/dredd/
├── cli.py               # Punto de entrada Typer y comandos CLI
├── core/
│   ├── ast_checker.py   # Linter nativo de reglas P1 (0xXXXXh) y convenciones C
│   ├── git_ops.py       # Gestión de caché local de repositorios de estudiantes
│   ├── github_api.py    # Integración con gh CLI (PRs y comentarios)
│   ├── makefile_eval.py # Soporte para proyectos modulares con Makefiles (modo conan)
│   ├── moodle.py        # Ingesta de ZIPs y exportación CSV para Moodle
│   ├── plagiarism.py    # Detector de similitud por huellas Winnowing
│   ├── reporter.py      # Ensamblador de informes Markdown modulares
│   └── ripley_client.py # Cliente de integración con el motor stateless Ripley
```
