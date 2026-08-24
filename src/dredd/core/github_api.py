"""Integración con GitHub CLI (gh) para resolución de PRs y publicación de comentarios."""

import json
from pathlib import Path
import shutil
import subprocess
from typing import Optional


def is_gh_installed() -> bool:
    """Verifica si la herramienta gh (GitHub CLI) está disponible en el PATH."""
    return shutil.which("gh") is not None


def get_open_pr_number(org: str, student: str) -> Optional[int]:
    """Descubre dinámicamente el número de Pull Request abierto para el estudiante."""
    if not is_gh_installed():
        return 1

    repo_full_name = f"{org}/{student}"
    try:
        proc = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repo_full_name,
                "--state",
                "open",
                "--json",
                "number",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            prs = json.loads(proc.stdout)
            if prs and isinstance(prs, list) and len(prs) > 0:
                return int(prs[0].get("number", 1))
    except Exception:
        pass

    return 1


def post_pr_comment(
    org: str,
    student: str,
    report_file: Path,
    pr_number: Optional[int] = None,
) -> bool:
    """Publica el archivo Markdown del informe como comentario en el PR del alumno."""
    if not is_gh_installed():
        raise RuntimeError("GitHub CLI ('gh') no está instalado o autenticado.")

    if not report_file.exists():
        raise FileNotFoundError(f"El informe '{report_file}' no existe.")

    pr_num = pr_number or get_open_pr_number(org, student) or 1
    pr_url = f"https://github.com/{org}/{student}/pull/{pr_num}"

    proc = subprocess.run(
        ["gh", "pr", "comment", pr_url, "-F", str(report_file)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Error al enviar comentario a {pr_url}: {proc.stderr.strip()}")

    return True


def open_pr_in_browser(org: str, student: str, pr_number: Optional[int] = None) -> None:
    """Abre la vista de archivos modificados del PR en el navegador web local."""
    pr_num = pr_number or get_open_pr_number(org, student) or 1
    pr_files_url = f"https://github.com/{org}/{student}/pull/{pr_num}/files"

    opener = shutil.which("xdg-open") or shutil.which("firefox") or shutil.which("google-chrome")
    if opener:
        subprocess.Popen([opener, pr_files_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def create_or_repair_pr(
    org: str,
    student: str,
    repo_path: Path,
    branch_name: str = "correccion",
    base_branch: str = "main",
    title: str = "Corrección",
    body: str = "Pull Request de corrección automática generado por Dredd.",
) -> bool:
    """Crea o repara una rama y Pull Request de corrección para un estudiante (reemplaza prfix.sh)."""
    if not is_gh_installed():
        raise RuntimeError("GitHub CLI ('gh') no está instalado o autenticado.")

    # 1. Asegurar rama local
    subprocess.run(["git", "-C", str(repo_path), "checkout", "-B", branch_name], capture_output=True)
    subprocess.run(["git", "-C", str(repo_path), "push", "-f", "--set-upstream", "origin", branch_name], capture_output=True)

    # 2. Crear PR mediante gh
    repo_full_name = f"{org}/{student}"
    proc = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo_full_name,
            "--base",
            base_branch,
            "--head",
            branch_name,
            "--title",
            title,
            "--body",
            body,
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return proc.returncode == 0 or "already exists" in (proc.stderr or "").lower()

