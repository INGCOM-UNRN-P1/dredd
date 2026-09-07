"""Unit tests for binary detection, filtering, and reporting in Dredd."""

import io
from pathlib import Path
import zipfile

from dredd.core.binary_check import (
    audit_and_purge_binaries_from_dir,
    is_binary_file,
)
from dredd.core.ingest import extract_archive_payload
from dredd.core.reporter import (
    generate_personalized_feedback_markdown,
    write_individual_tool_reports,
)


def test_is_binary_file_by_extension():
    assert is_binary_file("main.o")[0] is True
    assert is_binary_file("libtest.a")[0] is True
    assert is_binary_file("ejercicio.exe")[0] is True
    assert is_binary_file("module.so")[0] is True
    assert is_binary_file("lib.dylib")[0] is True
    assert is_binary_file("main.c")[0] is False
    assert is_binary_file("main.h")[0] is False
    assert is_binary_file("Makefile")[0] is False


def test_is_binary_file_by_magic_bytes():
    elf_bytes = b"\x7fELF\x02\x01\x01\x00"
    is_bin, reason = is_binary_file("programa_sin_extension", elf_bytes)
    assert is_bin is True
    assert "Linux ELF" in reason

    pe_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
    is_bin, reason = is_binary_file("test_bin", pe_bytes)
    assert is_bin is True
    assert "Windows PE" in reason

    c_source = b"#include <stdio.h>\nint main(void) { return 0; }\n"
    assert is_binary_file("main.c", c_source)[0] is False


def test_audit_and_purge_binaries_from_dir(tmp_path: Path):
    source_c = tmp_path / "main.c"
    source_c.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    bin_o = tmp_path / "main.o"
    bin_o.write_bytes(b"\x7fELF\x02\x01\x01\x00fake_binary_code")

    bin_exe = tmp_path / "sub" / "run.exe"
    bin_exe.parent.mkdir(parents=True, exist_ok=True)
    bin_exe.write_bytes(b"MZ\x90\x00executable")

    findings = audit_and_purge_binaries_from_dir(tmp_path)

    # Verifica que se generaron 2 hallazgos de severidad ERROR
    assert len(findings) == 2
    assert all(f["severity"] == "ERROR" for f in findings)
    reported_files = {f["file"] for f in findings}
    assert "main.o" in reported_files
    assert "sub/run.exe" in reported_files

    # Verifica que los archivos binarios fueron PURGADOS del disco
    assert source_c.exists()
    assert not bin_o.exists()
    assert not bin_exe.exists()


def test_extract_archive_payload_filters_and_collects_binaries():
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("ejercicios/ej1/main.c", "int main() { return 0; }")
        z.writestr("ejercicios/ej1/main.o", b"\x7fELF\x02fake_object")
        z.writestr("ejercicios/ej1/ejecutable.exe", b"MZfake_exe")

    bin_collector = []
    extracted = extract_archive_payload(bio.getvalue(), binary_collector=bin_collector)

    # Solo main.c debe ser extraído como fuente
    extracted_names = [e[0] for e in extracted]
    assert extracted_names == ["ejercicios/ej1/main.c"]

    # Los binarios deben haber sido interceptados por el collector
    collector_names = [b[0] for b in bin_collector]
    assert "ejercicios/ej1/main.o" in collector_names
    assert "ejercicios/ej1/ejecutable.exe" in collector_names


def test_reporter_marks_binary_errors(tmp_path: Path):
    analysis = {
        "compilation": {"success": True, "files": {}},
        "ast_findings": [],
        "tests": {"total": 1, "passed": 1, "failed": 0},
        "binary_findings": [
            {
                "file": "ejercicio1/main.o",
                "rule_code": "0x000Fh",
                "severity": "ERROR",
                "message": "Archivo binario precompilado no permitido",
                "suggestion": "Ejecutar make clean",
            }
        ],
    }

    rni_dir = tmp_path / "r1i"
    generated = write_individual_tool_reports(rni_dir, analysis)

    assert "binarios" in generated
    bin_content = generated["binarios"].read_text(encoding="utf-8")
    assert "Archivos Binarios Prohibidos Filtrados" in bin_content
    assert "ejercicio1/main.o" in bin_content

    feedback = generate_personalized_feedback_markdown(
        student_name="Perez Juan",
        exercise_name="entrega_4",
        analysis=analysis,
    )
    assert "ENTREGA NO APROBADA (Archivos binarios prohibidos detectados)" in feedback
    assert "Archivos Binarios (.o, .a, .exe):** ❌" in feedback
