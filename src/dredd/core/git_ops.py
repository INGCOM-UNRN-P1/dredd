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


def ensure_submission_repo(
    org: str,
    exercise: str,
    student: str,
    workspace_dir: Path,
    auth_token: Optional[str] = None,
) -> Path:
    """Clona o actualiza el repositorio del estudiante en <workspace>/<exercise>-submissions/<student>/."""
    submissions_dir = workspace_dir / f"{exercise}-submissions"
    submissions_dir.mkdir(parents=True, exist_ok=True)
    repo_path = submissions_dir / student

    if repo_path.is_dir() and (repo_path / ".git").is_dir():
        # Actualización limpia
        subprocess.run(["git", "-C", str(repo_path), "restore", "*"], capture_output=True)
        subprocess.run(["git", "-C", str(repo_path), "reset", "--hard", "HEAD"], capture_output=True)
        pull_res = subprocess.run(["git", "-C", str(repo_path), "pull"], capture_output=True, text=True)
        if pull_res.returncode != 0:
            raise RuntimeError(f"Error al actualizar '{student}' con git pull: {pull_res.stderr.strip()}")
    else:
        # Clonación inicial
        repo_url = f"https://github.com/{org}/{student}.git"
        clone_res = subprocess.run(["git", "clone", repo_url, str(repo_path)], capture_output=True, text=True)
        if clone_res.returncode != 0:
            raise RuntimeError(f"Error al clonar '{repo_url}': {clone_res.stderr.strip()}")

    return repo_path


def get_repo_metadata(repo_path: Path) -> RepoMetadata:
    """Extrae metadatos de versión de Git sobre el repositorio local del estudiante."""
    if not (repo_path / ".git").is_dir():
        return RepoMetadata(
            date_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            files_list="\n".join([f.name for f in repo_path.glob("*") if not f.name.startswith(".")]),
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

    # Listado de archivos
    files = []
    for item in sorted(repo_path.glob("*")):
        if item.name.startswith("."):
            continue
        tipo = "d" if item.is_dir() else "-"
        files.append(f"{tipo} {item.name}")

    return RepoMetadata(
        branch=branch,
        revision=revision,
        date_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        files_list="\n".join(files),
        recent_commits=commits,
    )
