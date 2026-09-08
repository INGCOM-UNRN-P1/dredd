# Diseño: Subcomando `dredd github` y versionado de informes por shorthash

## 1. Contexto y Objetivos

Actualmente, `dredd` ofrece comandos aislados para interactuar con GitHub (`comment` y `pr-fix`), mientras que la clonación de repositorios de estudiantes se realiza de forma automática pero implícita en `eval`, o requiriendo estructuración en revisiones `r1/r1i`.

Este diseño establece:
1. Unificar las operaciones de GitHub bajo el subcomando `dredd github` (`clone`, `comment`, `pr-fix`), manteniendo retrocompatibilidad en los comandos raíz existentes.
2. Implementar `dredd github clone <practica> <directorio_destino> <repo_url>` para clonar entregas directamente en la ruta `<practica>/<directorio_destino>/repo`.
3. Adoptar una arquitectura de almacenamiento limpia para repositorios clonados:
   - `<practica>/<estudiante>/repo/`: Repositorio Git puro con `.git` intacto para permitir `git pull` y `pr-fix`.
   - `<practica>/<estudiante>/i_<shorthash>/`: Informes intermedios de herramientas para el commit evaluado (`compilacion.log`, `gaff.md`, `ripley.md`, etc.).
   - `<practica>/<estudiante>/<estudiante>_<shorthash>.md`: Informe consolidado de evaluación para el commit evaluado.
4. Registrar en el informe los metadatos completos del commit analizado (hash corto, hash completo, rama, autor, fecha y mensaje).
5. Si `dredd eval` se ejecuta sobre el mismo commit, reemplaza los informes (`i_<shorthash>/` y `<estudiante>_<shorthash>.md`). Si hubo nuevos commits tras `git pull` (hash diferente), genera un nuevo conjunto `i_<nuevo_shorthash>/` y `<estudiante>_<nuevo_shorthash>.md`, preservando los anteriores.

---

## 2. Estructura de Directorios

Para una práctica `TP0` y un estudiante `TP0-Enehuen`:

```text
TP0/
└── TP0-Enehuen/
    ├── repo/                             <-- Clon Git (.git intacto para git pull)
    │   ├── .git/
    │   ├── Makefile
    │   ├── main.c
    │   └── ...
    ├── i_a1b2c3d/                        <-- Informes de herramientas para commit a1b2c3d
    │   ├── compilacion.log
    │   ├── gaff.md
    │   ├── ripley.md
    │   └── valgrind.md
    ├── TP0-Enehuen_a1b2c3d.md            <-- Consolidado para commit a1b2c3d
    ├── i_e4f5a6b/                        <-- Nuevo conjunto si hubo nuevo commit
    └── TP0-Enehuen_e4f5a6b.md            <-- Nuevo consolidado si hubo nuevo commit
```

Las entregas basadas en el flujo Moodle o que ya posean carpetas `rN` (`r1/`, `r1i/`) continuarán siendo evaluadas con su esquema correspondiente sin alteraciones.

---

## 3. Especificación de Comandos CLI (`dredd github`)

### 3.1. Sub-aplicación Typer `github`
En `src/dredd/cli.py`:
```python
github_app = typer.Typer(
    name="github",
    help="Comandos de integración con GitHub (clone, comment, pr-fix).",
    no_args_is_help=True,
)
app.add_typer(github_app, name="github")
```

### 3.2. Comando `dredd github clone`
```bash
dredd github clone <practica> <directorio_destino> <repo_url>
```
* **Parámetros:**
  * `practica` (str): Nombre o ruta de la actividad (ej. `TP0`). Se resuelve mediante `resolve_submissions_dir(workspace_dir, practica)`.
  * `directorio_destino` (str): Nombre de la carpeta del estudiante (ej. `TP0-Enehuen`).
  * `repo_url` (str): URL de clonación de GitHub (HTTPS o SSH).
* **Comportamiento:**
  1. Resuelve `submissions_dir` para la práctica (ej. `<ws>/TP0` o `<ws>/TP0-submissions`).
  2. Determina la ruta destino: `student_dir = submissions_dir / directorio_destino` y `repo_dir = student_dir / "repo"`.
  3. Si `repo_dir / .git` existe:
     - Ejecuta `git -C <repo_dir> fetch` y `git -C <repo_dir> pull`.
     - Informa si se incorporaron nuevos commits o si ya se encuentra al día.
  4. Si `repo_dir` no existe:
     - Crea `student_dir` y ejecuta `git clone <repo_url> <repo_dir>`.
     - Verifica código de salida. Si falla, limpia la carpeta incompleta y lanza error con salida estándar de Git.
  5. Imprime resumen con rama activa, commit SHA actual y autor.

### 3.3. Comandos `dredd github comment` y `dredd github pr-fix`
* Se vinculan a las funciones existentes `cmd_comment` y `cmd_pr_fix`.
* Los comandos en raíz `dredd comment` y `dredd pr-fix` no se preservan en su ubicación original.

---

## 4. Adaptación del Ciclo de Evaluación (`dredd eval`)

### 4.1. Detección de `repo/` en entregas
En `src/dredd/cli.py` (`ejecutar_evaluacion`):
* Si `student_dir / "repo"` es un directorio con `.git` o código fuente:
  * El directorio de código a compilar/analizar es `target_path = student_dir / "repo"`.
  * No se aplica reformat ni creación de `r1`.
* En caso contrario:
  * Mantiene el comportamiento preexistente (`find_existing_revision_folders` o aplanamiento a `r1`).

### 4.2. Extracción de metadatos de Git
En `src/dredd/core/git_ops.py` (`get_repo_metadata`):
* Extrae `revision` (shorthash, 7-8 caracteres, ej: `git rev-parse --short HEAD`).
* Extrae `full_hash` (`git rev-parse HEAD`).
* Extrae rama, fecha, autor y último mensaje de commit.

### 4.3. Nombres de directorios e informes
* `shorthash = meta.revision or "r1"`
* Directorio de informes individuales: `i_dir = student_dir / f"i_{shorthash}"`
* Archivo consolidado: `report_file = student_dir / f"{student_name}_{shorthash}.md"`
* Archivo de log de compilación: `student_dir / f"{student_name}_{shorthash}_compilacion.log"`

### 4.4. Criterio de Reemplazo e Historial
* Si se vuelve a ejecutar `dredd eval` sobre el mismo commit:
  * Se sobrescriben los archivos dentro de `i_{shorthash}/` y el reporte `{student}_{shorthash}.md`.
* Si se ejecuta `dredd eval` tras un `git pull` que avanzó el commit a `hash2`:
  * Se crea `i_{hash2}/` y `{student}_{hash2}.md`.
  * Se conservan `i_{hash1}/` y `{student}_{hash1}.md`.
  * El nuevo reporte incluye en sus metadatos referencia al commit anterior si existe.

---

## 5. Pruebas y Validación

1. **Test unitarios en `tests/test_github_ops.py`**:
   - `test_github_clone_new_repo`: Clonación exitosa de un repositorio local/mock a `<practica>/<destino>/repo`.
   - `test_github_clone_existing_pull`: Ejecución de pull incremental cuando `repo/` ya existe.
   - `test_eval_with_repo_structure_shorthash`: Verificación de que `dredd eval` detecta `repo/`, genera `i_<shorthash>/` y el informe `<estudiante>_<shorthash>.md`.
   - `test_eval_idempotency_same_hash`: Verificación de que re-evaluar el mismo commit reemplaza los informes sin duplicar carpetas.
   - `test_eval_new_commit_creates_new_shorthash_set`: Verificación de que un nuevo commit genera un nuevo conjunto de informes preservando el anterior.
   - `test_github_aliases_backwards_compatibility`: Verificación de que `dredd comment` y `dredd pr-fix` siguen funcionando.
2. **Ejecución de la suite completa con `uv run pytest`** asegurando cero regresiones en los 113 tests existentes.
