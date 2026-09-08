# Subcomando `dredd github` y versionado de informes por shorthash - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar el subcomando `dredd github` con `clone`, mover los comandos preexistentes de GitHub (`comment`, `pr-fix`) a su nueva ubicación bajo `dredd github`, y adaptar el ciclo de evaluación para estructurar repositorios en `repo/` con informes por shorthash (`i_<shorthash>/` y `<estudiante>_<shorthash>.md`).

**Architecture:** Módulo `git_ops.py` provee las funciones de clonación/actualización con `git pull` y extracción de metadatos de commit (shorthash, full SHA, autor, fecha). `cli.py` define la sub-app Typer `github` y reubica `comment` y `pr-fix` allí, mientras que `ejecutar_evaluacion` detecta `repo/`, genera `i_<shorthash>/` y `<estudiante>_<shorthash>.md`, aplicando reemplazo si el hash no cambia o un nuevo conjunto si hay un commit diferente.

**Tech Stack:** Python 3.10+, Typer, Git CLI vía `subprocess`, Pytest.

## Global Constraints
- Ubicación de repositorios clonados: `<practica>/<directorio_destino>/repo`.
- Ubicación de informes intermedios: `<practica>/<directorio_destino>/i_<shorthash>/`.
- Ubicación de informe consolidado: `<practica>/<directorio_destino>/<directorio_destino>_<shorthash>.md`.
- Reubicación estricta: `comment` y `pr-fix` pasan a ser `dredd github comment` y `dredd github pr-fix`.
- Español rioplatense con voseo en salidas y reportes.

---

### Task 1: Operaciones Git para clonación/actualización y metadatos extendidos

**Files:**
- Modify: `src/dredd/core/git_ops.py`
- Test: `tests/test_github_ops.py`

**Interfaces:**
- Produces:
  - `clone_submission_repo(submissions_dir: Path, student_dir_name: str, repo_url: str) -> tuple[Path, bool, str]`
    - Retorna `(repo_path, is_new_clone, status_message)`
  - `RepoMetadata.full_hash: str`
  - `RepoMetadata.author: str`
  - `RepoMetadata.commit_message: str`

- [ ] **Step 1: Escribir tests que fallen para `clone_submission_repo` y metadatos extendidos**
- [ ] **Step 2: Ejecutar pytest para verificar que fallan**
- [ ] **Step 3: Implementar `clone_submission_repo` y extender `get_repo_metadata`**
- [ ] **Step 4: Ejecutar pytest para verificar que pasan**
- [ ] **Step 5: Commit**

---

### Task 2: Sub-aplicación `dredd github` y reubicación de comandos

**Files:**
- Modify: `src/dredd/cli.py`
- Test: `tests/test_cli.py` y `tests/test_github_ops.py`

**Interfaces:**
- Produces:
  - `github_app = typer.Typer(...)`
  - `dredd github clone <practica> <directorio_destino> <repo_url>`
  - `dredd github comment <exercise> <student> ...`
  - `dredd github pr-fix <exercise> <student> ...`
  - Remoción de comandos raíz `@app.command("comment")` y `@app.command("pr-fix")`.

- [ ] **Step 1: Escribir tests en `tests/test_github_ops.py` para la invocación CLI de `dredd github clone`, `comment` y `pr-fix`**
- [ ] **Step 2: Ejecutar pytest y verificar fallos**
- [ ] **Step 3: Implementar `github_app` en `src/dredd/cli.py`, reubicar comandos y registrar `app.add_typer(github_app, name="github")`**
- [ ] **Step 4: Actualizar llamadas en `tests/test_cli.py` si hacían referencia a los comandos movidos**
- [ ] **Step 5: Ejecutar pytest y verificar que pasan**
- [ ] **Step 6: Commit**

---

### Task 3: Adaptación del ciclo de evaluación para `repo/` e informes `i_<shorthash>/`

**Files:**
- Modify: `src/dredd/cli.py`
- Modify: `src/dredd/core/reporter.py`
- Test: `tests/test_github_ops.py`

**Interfaces:**
- Consumes: `get_repo_metadata`, `generate_student_report`, `run_ripley_analysis`
- Produces:
  - Detección de `<student_dir>/repo` como `target_path`.
  - Generación de informes en `student_dir / f"i_{shorthash}"`.
  - Generación de consolidado en `student_dir / f"{student_name}_{shorthash}.md"`.
  - Metadatos en reporte: Hash corto, Hash completo, Rama, Fecha, Autor, Mensaje.
  - Sobrescritura si el hash es idéntico; creación de nuevo set si el hash cambia.

- [ ] **Step 1: Escribir test en `tests/test_github_ops.py` para el flujo de evaluación con `repo/` y shorthash**
- [ ] **Step 2: Ejecutar pytest para verificar que falla**
- [ ] **Step 3: Modificar `cli.py` y `reporter.py` para soportar `repo/` y naming con `shorthash`**
- [ ] **Step 4: Ejecutar pytest para verificar que pasa**
- [ ] **Step 5: Commit**

---

### Task 4: Verificación integral y suite completa

- [ ] **Step 1: Ejecutar la suite completa con `uv run pytest`**
- [ ] **Step 2: Verificar que los 113+ tests pasen sin fallos ni regresiones**
- [ ] **Step 3: Commit final y resumen de entrega**
