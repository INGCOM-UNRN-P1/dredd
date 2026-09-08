"""Unit tests for GitHub operations: cloning, updating, and shorthash metadata."""

from pathlib import Path
import subprocess
import pytest

from dredd.core.git_ops import clone_submission_repo, get_repo_metadata


def _create_git_repo(repo_path: Path, filename: str = "main.c", content: str = "int main(void) { return 0; }\n") -> str:
    """Helper para crear un repositorio git local real para tests."""
    repo_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
    
    file_path = repo_path / filename
    file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True, capture_output=True)
    
    sha_proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path, check=True, capture_output=True, text=True)
    return sha_proc.stdout.strip()


def test_get_repo_metadata_extended(tmp_path: Path):
    repo = tmp_path / "test_repo"
    full_sha = _create_git_repo(repo, content="int main(void) { return 42; }\n")

    meta = get_repo_metadata(repo)
    assert meta.branch == "main"
    assert meta.revision == full_sha[:7] or meta.revision in full_sha
    assert meta.full_hash == full_sha
    assert meta.author == "Test User"
    assert meta.commit_message == "Initial commit"
    assert meta.commit_date != ""


def test_clone_submission_repo_new_and_update(tmp_path: Path):
    # Crear origen remoto
    remote_origin = tmp_path / "remote_origin"
    full_sha = _create_git_repo(remote_origin)

    submissions_dir = tmp_path / "TP0"
    submissions_dir.mkdir()

    # 1. Clonar
    repo_path, is_new, msg = clone_submission_repo(
        submissions_dir=submissions_dir,
        student_dir_name="TP0-Enehuen",
        repo_url=str(remote_origin),
    )

    assert is_new is True
    assert repo_path == submissions_dir / "TP0-Enehuen" / "repo"
    assert (repo_path / ".git").is_dir()
    assert (repo_path / "main.c").is_file()

    # 2. Re-ejecutar sin cambios -> pull informa al día
    repo_path_2, is_new_2, msg_2 = clone_submission_repo(
        submissions_dir=submissions_dir,
        student_dir_name="TP0-Enehuen",
        repo_url=str(remote_origin),
    )
    assert is_new_2 is False
    assert "actualizado" in msg_2.lower()

    # 3. Nuevo commit en el origen -> pull descarga actualización
    (remote_origin / "nuevo.c").write_text("void foo(void) {}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=remote_origin, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Segundo commit"], cwd=remote_origin, check=True, capture_output=True)

    repo_path_3, is_new_3, msg_3 = clone_submission_repo(
        submissions_dir=submissions_dir,
        student_dir_name="TP0-Enehuen",
        repo_url=str(remote_origin),
    )
    assert is_new_3 is False
    assert (repo_path_3 / "nuevo.c").is_file()
