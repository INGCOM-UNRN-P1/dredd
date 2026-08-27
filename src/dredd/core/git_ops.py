"""Operaciones de Git para gestionar carpetas de caché local de estudiantes."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import subprocess
from typing import Dict, List, Optional


@dataclass
class RepoMetadata:
    branch: str = "main"
    revision: str = ""
    date_str: str = ""
    files_list: str = ""
    recent_commits: List[str] = field(default_factory=list)


def resolve_submissions_dir(workspace_dir: Path | str, exercise_or_path: Path | str) -> tuple[str, Path]:
    """Resuelve el nombre de la actividad y la ruta real del directorio de entregas.

    Soporta:
    - Directorio directo pasado como argumento (ej: 'entrega-3_1238305/', './campus/entrega_1')
    - Directorio relativo en el workspace: <workspace>/<exercise>/
    - Directorio de submissions: <workspace>/<exercise>-submissions/
    - Slug limpio sin sufijo.
    """
    ws = Path(workspace_dir).resolve()
    raw = Path(exercise_or_path)

    # 1. Si es una ruta existente directa (absoluta o relativa a CWD)
    if raw.is_dir():
        clean_name = raw.name.rstrip("/\\") or raw.resolve().name
        return clean_name, raw.resolve()

    raw_str = str(exercise_or_path).rstrip("/\\")
    slug = Path(raw_str).name or raw_str

    # 2. Si existe en el workspace tal como se especificó
    cand_ws = ws / raw_str
    if cand_ws.is_dir():
        return slug, cand_ws.resolve()

    # 3. Si existe <slug> en el workspace
    cand_slug = ws / slug
    if cand_slug.is_dir():
        return slug, cand_slug.resolve()

    # 4. Si existe <slug>-submissions en el workspace
    cand_sub = ws / f"{slug}-submissions"
    if cand_sub.is_dir():
        return slug, cand_sub.resolve()

    # 5. Si existe <raw_str>-submissions en el workspace
    cand_raw_sub = ws / f"{raw_str}-submissions"
    if cand_raw_sub.is_dir():
        return slug, cand_raw_sub.resolve()

    # 6. Fallback predeterminado para nuevas descargas/clonaciones
    return slug, (ws / f"{slug}-submissions").resolve()


def ensure_submission_repo(
    org: str,
    exercise: str,
    student: str,
    workspace_dir: Path,
    auth_token: Optional[str] = None,
    submissions_dir: Optional[Path] = None,
) -> Path:
    """Clona o actualiza el repositorio del estudiante en <submissions_dir>/<student>/."""
    if submissions_dir is None:
        exercise_slug, sub_dir = resolve_submissions_dir(workspace_dir, exercise)
    else:
        sub_dir = Path(submissions_dir)

    sub_dir.mkdir(parents=True, exist_ok=True)
    repo_path = sub_dir / student

    if repo_path.is_dir() and (repo_path / ".git").is_dir():
        # Actualización limpia
        subprocess.run(["git", "-C", str(repo_path), "restore", "*"], capture_output=True)
        subprocess.run(["git", "-C", str(repo_path), "reset", "--hard", "HEAD"], capture_output=True)
        pull_res = subprocess.run(["git", "-C", str(repo_path), "pull"], capture_output=True, text=True)
        if pull_res.returncode != 0:
            raise RuntimeError(f"Error al actualizar '{student}' con git pull: {pull_res.stderr.strip()}")
    elif repo_path.is_dir():
        # Directorio local preexistente (entregas locales / Moodle descompactadas)
        return repo_path
    else:
        # Clonación inicial desde GitHub
        repo_url = f"https://github.com/{org}/{student}.git"
        clone_res = subprocess.run(["git", "clone", repo_url, str(repo_path)], capture_output=True, text=True)
        if clone_res.returncode != 0:
            raise RuntimeError(f"Error al clonar '{repo_url}': {clone_res.stderr.strip()}")

    return repo_path


def generate_tree_output(root_dir: Path, max_depth: int = 6) -> str:
    """Genera una representación jerárquica estilo 'tree' del directorio omitiendo archivos ocultos."""
    if not root_dir.exists() or not root_dir.is_dir():
        return ""

    lines = ["."]

    def _walk(current_dir: Path, prefix: str = "", depth: int = 1):
        if depth > max_depth:
            return

        try:
            entries = sorted(
                [e for e in current_dir.iterdir() if not e.name.startswith(".")],
                key=lambda x: (not x.is_dir(), x.name.lower()),
            )
        except Exception:
            return

        total = len(entries)
        for i, entry in enumerate(entries):
            is_last = (i == total - 1)
            connector = "└── " if is_last else "├── "
            display_name = f"{entry.name}/" if entry.is_dir() else entry.name
            lines.append(f"{prefix}{connector}{display_name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk(entry, prefix=prefix + extension, depth=depth + 1)

    _walk(root_dir)
    return "\n".join(lines)


def get_repo_metadata(repo_path: Path) -> RepoMetadata:
    """Extrae metadatos de versión de Git sobre el repositorio local del estudiante."""
    tree_output = generate_tree_output(repo_path)

    if not (repo_path / ".git").is_dir():
        return RepoMetadata(
            date_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            files_list=tree_output,
        )

    branch_proc = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    branch = branch_proc.stdout.strip() or "main"

    rev_proc = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    revision = rev_proc.stdout.strip() or "unknown"

    log_proc = subprocess.run(
        ["git", "-C", str(repo_path), "log", "-n", "5", "--oneline"],
        capture_output=True,
        text=True,
    )
    commits = [line.strip() for line in log_proc.stdout.splitlines() if line.strip()]

    return RepoMetadata(
        branch=branch,
        revision=revision,
        date_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        files_list=tree_output,
        recent_commits=commits,
    )
