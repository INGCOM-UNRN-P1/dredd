"""Unit tests for dredd.core.compiler (ESPER compilation with GCC fallback)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from dredd.core.compiler import (
    compile_c_sources,
    compile_with_esper,
    compile_with_gcc,
    CompilationResult,
)


def test_compile_c_sources_empty():
    res = compile_c_sources([])
    assert not res.success
    assert res.compiler_used == "none"


def test_compile_c_sources_with_valid_c(tmp_path: Path):
    c_file = tmp_path / "main.c"
    c_file.write_text("int main(void) { return 0; }\n")

    res = compile_c_sources([c_file], output_bin=tmp_path / "main_bin")
    assert res.success
    assert res.output_bin is not None
    assert res.output_bin.is_file()
    assert res.compiler_used in ("esper", "gcc")


def test_compile_c_sources_with_syntax_error(tmp_path: Path):
    c_file = tmp_path / "bad.c"
    c_file.write_text("int main(void) { return invalid_symbol; }\n")

    res = compile_c_sources([c_file])
    assert not res.success
    assert res.compiler_used in ("esper", "gcc")
    if res.compiler_used == "esper":
        assert len(res.translated_diagnostics) > 0


def test_compile_with_esper_mock(tmp_path: Path):
    c_file = tmp_path / "sample.c"
    c_file.write_text("int main() { return 0; }")

    mock_report = MagicMock()
    mock_report.passed = True
    mock_report.raw_stderr = ""
    mock_diag = MagicMock()
    mock_diag.file_path = "sample.c"
    mock_diag.line_number = 1
    mock_diag.severity.value = "WARNING"
    mock_diag.title_es = "Advertencia de prueba"
    mock_diag.explanation_es = "Explicación"
    mock_diag.suggestion_es = "Sugerencia"
    mock_diag.raw_message = "raw warning"
    mock_diag.code_snippet = None
    mock_report.diagnostics = [mock_diag]

    with patch("dredd.core.compiler._try_import_esper", return_value=lambda args: mock_report):
        res = compile_with_esper([c_file])
        assert res is not None
        assert res.success
        assert res.compiler_used == "esper"
        assert len(res.translated_diagnostics) == 1
        assert res.translated_diagnostics[0]["title_es"] if "title_es" in res.translated_diagnostics[0] else "Advertencia de prueba" in res.translated_diagnostics[0]["translated_message"]


def test_compile_fallback_to_gcc_when_esper_fails(tmp_path: Path):
    c_file = tmp_path / "sample.c"
    c_file.write_text("int main(void) { return 0; }\n")

    with patch("dredd.core.compiler.compile_with_esper", return_value=None):
        res = compile_c_sources([c_file], output_bin=tmp_path / "gcc_bin")
        assert res.success
        assert res.compiler_used == "gcc"
        assert (tmp_path / "gcc_bin").is_file()
