"""Unit tests for Dredd Moodle ingest, mapping, and database persistence."""

import io
from pathlib import Path
import zipfile

from dredd.core.db import DatabaseManager, StudentRecord
from dredd.core.ingest import (
    MoodleIngestor,
    normalize_encoding,
    parse_moodle_zip_filename,
    parse_student_folder_name,
)
from dredd.core.mapping import MappingStore, heuristic_match


def test_parse_moodle_zip_filename():
    res = parse_moodle_zip_filename("Entrega #1-1228009.zip")
    assert res.activity_id == "1228009"
    assert "entrega-1" in res.activity_slug


def test_parse_student_folder_name():
    res = parse_student_folder_name("Alvarez Juan_1848964_assignsubmission_file")
    assert res.student_name == "Alvarez Juan"
    assert res.submission_id == "1848964"
    assert "alvarez-juan" in res.student_slug


def test_normalize_encoding_cp1252():
    cp1252_bytes = "int número = 42;".encode("cp1252")
    text, enc = normalize_encoding(cp1252_bytes)
    assert "número" in text


def test_heuristic_match():
    assert heuristic_match("ejercicio1.c", ["ejercicio1", "ejercicio2"]) == "ejercicio1"
    assert heuristic_match("ej1.c", ["ejercicio1", "ejercicio2"]) == "ejercicio1"
    assert heuristic_match("tp1_ej2_solucion.c", ["ejercicio1", "ejercicio2"]) == "ejercicio2"


def test_database_manager_revisions(tmp_path: Path):
    db_file = tmp_path / ".metadata.db"
    db = DatabaseManager(db_file)

    student = StudentRecord("123", "Perez Juan", "perez-juan_123", "999")
    db.upsert_student(student)

    rev_id = db.add_revision(
        student_slug="perez-juan_123",
        version_num=1,
        sources_hash="hash123",
        folder_path=str(tmp_path / "r1"),
        sources=[{"filename": "main.c", "file_hash": "abc", "size_bytes": 100}],
        ignored=[],
    )
    assert rev_id == 1

    latest = db.get_latest_revision("perez-juan_123")
    assert latest["version_num"] == 1
    assert latest["sources_hash"] == "hash123"


def test_moodle_ingestor_process_zip(tmp_path: Path):
    zip_path = tmp_path / "Entrega #1-1228009.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "Alvarez Juan_101_assignsubmission_file/main.c",
            "int main(void) { return 0; }\n",
        )

    ingestor = MoodleIngestor(workspace_dir=tmp_path)
    info, results = ingestor.process_zip(zip_path)

    assert len(results) == 1
    assert (tmp_path / info.activity_slug / "alvarez-juan_101" / "r1" / "main.c").exists()
    assert not (tmp_path / info.activity_slug / "alvarez-juan_101" / "r1f").exists()


def test_moodle_ingestor_nested_zip_with_multi_wrapper_and_tar(tmp_path: Path):
    import tarfile
    from dredd.core.ingest import extract_archive_payload, is_allowed_file, _get_common_root_prefix

    assert is_allowed_file("Makefile")
    assert is_allowed_file("CMakeLists.txt")
    assert is_allowed_file("rules.mk")
    assert not is_allowed_file("__MACOSX/foo/Makefile")
    assert not is_allowed_file(".DS_Store")
    assert not is_allowed_file(".vscode/settings.json")

    # Multi-level wrapper test
    names = [
        "wrap1/wrap2/Makefile",
        "wrap1/wrap2/ejercicios/ej1/main.c",
        "wrap1/wrap2/.DS_Store",
    ]
    assert _get_common_root_prefix(names) == "wrap1/wrap2/"

    # Nested zip with backslashes
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("subfolder\\ejercicios\\ej1\\main.c", "int main() { return 0; }")
        z.writestr("subfolder\\Makefile", "all:\n\tgcc main.c")
    files = extract_archive_payload(bio.getvalue())
    extracted_names = {f[0] for f in files}
    assert "ejercicios/ej1/main.c" in extracted_names
    assert "Makefile" in extracted_names

    # TAR payload (fallback Thiago Iriarte case)
    tar_bio = io.BytesIO()
    with tarfile.open(fileobj=tar_bio, mode="w") as tf:
        ti = tarfile.TarInfo(name="wrap/ejercicios/ej1/main.c")
        c_bytes = b"int main() { return 1; }"
        ti.size = len(c_bytes)
        tf.addfile(ti, io.BytesIO(c_bytes))
    tar_files = extract_archive_payload(tar_bio.getvalue())
    assert len(tar_files) == 1
    assert tar_files[0][0] == "ejercicios/ej1/main.c"


def test_moodle_ingestor_process_zip_force(tmp_path: Path):
    zip_path = tmp_path / "Entrega #2-1228010.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "Perez Juan_102_assignsubmission_file/main.c",
            "int main(void) { return 0; }\n",
        )

    ingestor = MoodleIngestor(workspace_dir=tmp_path)
    info, results = ingestor.process_zip(zip_path)
    assert results[0].version_created == 1

    # Re-ingestar con force=True
    info2, results2 = ingestor.process_zip(zip_path, force=True)
    assert results2[0].version_created == 1
    assert (tmp_path / info2.activity_slug / "perez-juan_102" / "r1" / "main.c").exists()


def test_moodle_ingestor_unknown_activity_creates_skeleton(tmp_path: Path):
    from dredd.core.config import load_dredd_config

    zip_path = tmp_path / "Entrega #4-1240320.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "Alvarez Juan_101_assignsubmission_file/main.c",
            "int main(void) { return 0; }\n",
        )

    ingestor = MoodleIngestor(workspace_dir=tmp_path)
    info, results = ingestor.process_zip(zip_path)

    assert info.is_unknown_activity is True
    assert info.config_created_or_updated is True
    assert "debe ser ajustad" in info.warning_message.lower()

    cfg_path = tmp_path / "dredd.yaml"
    assert cfg_path.is_file()

    cfg = load_dredd_config(tmp_path)
    assert cfg is not None
    rule = cfg.find_mapping_for_activity(info.activity_slug)
    assert rule is not None
    assert rule.entrega == info.activity_slug
    assert rule.titulo == info.activity_name
    assert rule.mode == "archivos_individuales"
    assert "guias" in (rule.guia or "")
    assert rule.matches_zip(zip_path.name)


def test_moodle_ingestor_unknown_activity_appends_to_existing_config(tmp_path: Path):
    from dredd.core.config import load_dredd_config, init_workspace

    init_workspace(tmp_path)
    cfg_before = load_dredd_config(tmp_path)
    assert cfg_before is not None
    initial_mappings_count = len(cfg_before.mapeos)

    zip_path = tmp_path / "Entrega #9-9999999.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "Gomez Luis_105_assignsubmission_file/main.c",
            "int main(void) { return 0; }\n",
        )

    ingestor = MoodleIngestor(workspace_dir=tmp_path)
    info, results = ingestor.process_zip(zip_path)

    assert info.is_unknown_activity is True
    cfg_after = load_dredd_config(tmp_path)
    assert cfg_after is not None
    assert len(cfg_after.mapeos) == initial_mappings_count + 1

    rule = cfg_after.find_mapping_for_activity(info.activity_slug)
    assert rule is not None
    assert rule.entrega == info.activity_slug


def test_cli_moodle_ingest_unknown_warning(tmp_path: Path, monkeypatch):
    from typer.testing import CliRunner
    from dredd.cli import app

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    zip_path = tmp_path / "TP_Especial-55555.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "Perez Juan_101_assignsubmission_file/main.c",
            "int main(void) { return 0; }\n",
        )

    res = runner.invoke(app, ["moodle", "ingest", str(zip_path)])
    assert res.exit_code == 0
    assert "ADVERTENCIA: Práctica desconocida detectada" in res.output
    assert "debe ser ajustada" in res.output.lower()
    assert (tmp_path / "dredd.yaml").is_file()


