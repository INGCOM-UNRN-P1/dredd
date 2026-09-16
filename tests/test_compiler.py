"""Unit tests for dredd.core.compiler (DAEDALUS/ESPER compilation with GCC fallback)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from dredd.core.compiler import (
    compile_c_sources,
    compile_with_daedalus,
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
    assert res.compiler_used in ("daedalus", "esper", "gcc")


def test_compile_c_sources_with_syntax_error(tmp_path: Path):
    c_file = tmp_path / "bad.c"
    c_file.write_text("int main(void) { return invalid_symbol; }\n")

    res = compile_c_sources([c_file])
    assert not res.success
    assert res.compiler_used in ("daedalus", "esper", "gcc")
    if res.compiler_used in ("daedalus", "esper"):
        assert len(res.translated_diagnostics) > 0


def test_compile_with_daedalus_mock(tmp_path: Path):
    c_file = tmp_path / "sample.c"
    c_file.write_text("int main() { return 0; }")

    mock_res = MagicMock()
    mock_res.exito = True
    mock_res.codigo_retorno = 0
    mock_res.binario = tmp_path / "sample_bin"
    mock_res.stderr_crudo = ""
    mock_res.stdout_crudo = ""
    mock_diag = MagicMock()
    mock_diag.archivo = "sample.c"
    mock_diag.linea = 1
    mock_diag.severidad = "warning"
    mock_diag.titulo = "Advertencia de prueba"
    mock_diag.explicacion = "Explicación"
    mock_diag.sugerencia = "Sugerencia"
    mock_diag.mensaje_original = "raw warning"
    mock_diag.code_snippet = None
    mock_diag.flag = "-Wtest"
    mock_diag.cita_iso_c = None
    mock_res.diagnosticos = [mock_diag]

    with patch("dredd.core.compiler._try_import_daedalus", return_value=lambda *args, **kwargs: mock_res):
        res = compile_with_daedalus([c_file])
        assert res is not None
        assert res.success
        assert res.compiler_used == "daedalus"
        assert len(res.translated_diagnostics) == 1
        assert "Advertencia de prueba" in res.translated_diagnostics[0]["translated_message"]


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

    with patch("dredd.core.compiler.compile_with_daedalus", return_value=None):
        with patch("dredd.core.compiler._try_import_esper", return_value=lambda args: mock_report):
            res = compile_with_esper([c_file])
            assert res is not None
            assert res.success
            assert res.compiler_used == "esper"
            assert len(res.translated_diagnostics) == 1
            assert "Advertencia de prueba" in res.translated_diagnostics[0]["translated_message"]


def test_compile_fallback_to_gcc_when_esper_fails(tmp_path: Path):
    c_file = tmp_path / "sample.c"
    c_file.write_text("int main(void) { return 0; }\n")

    with patch("dredd.core.compiler.compile_with_daedalus", return_value=None):
        with patch("dredd.core.compiler.compile_with_esper", return_value=None):
            res = compile_c_sources([c_file], output_bin=tmp_path / "gcc_bin")
            assert res.success
            assert res.compiler_used == "gcc"
            assert (tmp_path / "gcc_bin").is_file()
