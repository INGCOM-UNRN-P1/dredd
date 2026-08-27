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


def test_resolve_submissions_dir_direct_folder(tmp_path: Path):
    from dredd.core.git_ops import resolve_submissions_dir

    custom_dir = tmp_path / "entrega-3_1238305"
    custom_dir.mkdir()

    slug, path = resolve_submissions_dir(tmp_path, "entrega-3_1238305/")
    assert slug == "entrega-3_1238305"
    assert path == custom_dir.resolve()

    slug2, path2 = resolve_submissions_dir(tmp_path, str(custom_dir))
    assert slug2 == "entrega-3_1238305"
    assert path2 == custom_dir.resolve()


def test_ensure_submission_repo_local_dir_no_git(tmp_path: Path):
    entregas = tmp_path / "entrega-1"
    entregas.mkdir()
    est = entregas / "perez_juan"
    est.mkdir()
    (est / "main.c").write_text("int main() { return 0; }\n")

    res_path = ensure_submission_repo(
        org="TEST_ORG",
        exercise="entrega-1",
        student="perez_juan",
        workspace_dir=tmp_path,
        submissions_dir=entregas,
    )
    assert res_path == est
    assert (res_path / "main.c").is_file()


def test_generate_tree_output_subdirectories(tmp_path: Path):
    from dredd.core.git_ops import generate_tree_output

    folder = tmp_path / "submission"
    folder.mkdir()
    (folder / "README.md").write_text("# Doc\n")
    sub1 = folder / "ejercicio1"
    sub1.mkdir()
    (sub1 / "main.c").write_text("int main(){}\n")
    (sub1 / "Makefile").write_text("all:\n")

    tree = generate_tree_output(folder)
    assert "." in tree
    assert "ejercicio1/" in tree
    assert "main.c" in tree
    assert "Makefile" in tree
    assert "README.md" in tree
    assert "├── " in tree or "└── " in tree
    assert "│   " in tree or "    " in tree

