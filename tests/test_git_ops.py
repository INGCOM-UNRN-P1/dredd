"""Unit tests for Dredd git operations."""

from pathlib import Path
import subprocess

from dredd.core.git_ops import get_repo_metadata, ensure_submission_repo


def test_get_repo_metadata_plain_folder(tmp_path: Path):
    folder = tmp_path / "alvarez_juan"
    folder.mkdir()
    (folder / "main.c").write_text("int main(void) { return 0; }\n")

    meta = get_repo_metadata(folder)
    assert "main.c" in meta.files_list
    assert meta.date_str != ""


def test_get_repo_metadata_git_repo(tmp_path: Path):
    repo = tmp_path / "repo_git"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "docente@unrn.edu.ar"], capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Docente"], capture_output=True)
    
    (repo / "main.c").write_text("int main(void) { return 0; }\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Initial commit"], capture_output=True)

    meta = get_repo_metadata(repo)
    assert meta.revision != ""
    assert len(meta.recent_commits) == 1
    assert "Initial commit" in meta.recent_commits[0]
