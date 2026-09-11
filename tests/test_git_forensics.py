"""Tests para el módulo git-forensics de Dredd."""

import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typer.testing import CliRunner
from dredd.cli import app
from dredd.core.git_anomaly import auditar_git_forensics

runner = CliRunner()


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Alumno"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "alumno@unrn.edu.ar"], check=True, capture_output=True)


def test_git_forensics_no_git(tmp_path: Path):
    non_git = tmp_path / "plain"
    non_git.mkdir()
    res = auditar_git_forensics(non_git)
    assert not res["es_repo_git"]
    assert res["riesgo"] == "DESCONOCIDO"

    cli_res = runner.invoke(app, ["git-forensics", str(non_git)])
    assert cli_res.exit_code == 1


def test_git_forensics_empty_git(tmp_path: Path):
    repo = tmp_path / "empty_git"
    repo.mkdir()
    init_git_repo(repo)
    res = auditar_git_forensics(repo)
    assert res["es_repo_git"]
    assert res["total_commits"] == 0


def test_git_forensics_normal_commits(tmp_path: Path):
    repo = tmp_path / "normal_git"
    repo.mkdir()
    init_git_repo(repo)

    (repo / "f1.c").write_text("int f1() { return 1; }")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Commit 1"], check=True, capture_output=True)

    (repo / "f2.c").write_text("int f2() { return 2; }")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Commit 2"], check=True, capture_output=True)

    res = auditar_git_forensics(repo)
    assert res["es_repo_git"]
    assert res["total_commits"] == 2
    assert not res["alteraciones_fecha_detectadas"]
    assert not res["rebase_masivo_detectado"]
    assert res["riesgo"] == "BAJO"

    cli_res = runner.invoke(app, ["git-forensics", str(repo), "--json"])
    assert cli_res.exit_code == 0
    assert '"riesgo": "BAJO"' in cli_res.stdout


def test_git_forensics_author_committer_skew(tmp_path: Path):
    repo = tmp_path / "skew_git"
    repo.mkdir()
    init_git_repo(repo)

    env = os.environ.copy()
    past_date = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    now_date = datetime.now(timezone.utc).isoformat()
    env["GIT_AUTHOR_DATE"] = past_date
    env["GIT_COMMITTER_DATE"] = now_date

    (repo / "mod.c").write_text("int mod() { return 0; }")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Commit con fecha forzada"], check=True, capture_output=True, env=env)

    res = auditar_git_forensics(repo, max_skew_seconds=300)
    assert res["alteraciones_fecha_detectadas"]
    assert any(a["tipo"] == "desfase_autor_committer" for a in res["anomalias"])


def test_git_forensics_rebase_masivo(tmp_path: Path):
    repo = tmp_path / "rebase_git"
    repo.mkdir()
    init_git_repo(repo)

    env = os.environ.copy()
    t_now = datetime.now(timezone.utc)

    for i in range(3):
        (repo / f"file_{i}.txt").write_text(f"contenido {i}")
        author_dt = (t_now - timedelta(hours=10 - (i * 3))).isoformat()
        committer_dt = t_now.isoformat()
        env["GIT_AUTHOR_DATE"] = author_dt
        env["GIT_COMMITTER_DATE"] = committer_dt
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True, env=env)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", f"Commit {i}"], check=True, capture_output=True, env=env)

    res = auditar_git_forensics(repo)
    assert res["total_commits"] == 3
    assert res["rebase_masivo_detectado"]
    assert res["riesgo"] == "ALTO"

    cli_res = runner.invoke(app, ["git-forensics", str(repo), "--fail-on-anomaly"])
    assert cli_res.exit_code == 1
