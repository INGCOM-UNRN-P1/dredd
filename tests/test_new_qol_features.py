"""Tests unitarios para las nuevas features de Dredd: sandbox con límites, evasión de seguridad, devoluciones en Markdown y matriz HTML de plagio."""

from pathlib import Path
from typer.testing import CliRunner
import pytest

from dredd.cli import app
from dredd.core.sandbox import execute_sandboxed, audit_sandbox_evasion
from dredd.core.reporter import generate_personalized_feedback_markdown
from dredd.core.plagiarism import SimilarityMatch, generate_plagiarism_html_report

runner = CliRunner()


def test_sandbox_execution_clean(tmp_path: Path):
    c_code = tmp_path / "hello.c"
    c_code.write_text('#include <stdio.h>\nint main(void) { printf("Hola Sandbox\\n"); return 0; }\n')
    bin_file = tmp_path / "hello_bin"
    
    from dredd.core.compiler import compile_c_sources
    comp = compile_c_sources([c_code], output_bin=bin_file)
    assert comp.success

    ret, stdout, stderr, timed_out = execute_sandboxed([str(bin_file)], max_memory_mb=64, timeout=5.0)
    assert ret == 0
    assert "Hola Sandbox" in stdout
    assert not timed_out


def test_audit_sandbox_evasion_detects_ptrace_and_forkbomb():
    malicious_code = """
#include <unistd.h>
#include <sys/ptrace.h>
#include <stdlib.h>

int main(void) {
    ptrace(PTRACE_TRACEME, 0, 1, 0);
    while (1) {
        fork();
    }
    system("rm -rf /");
    return 0;
}
"""
    findings = audit_sandbox_evasion(malicious_code)
    assert len(findings) >= 3
    rule_codes = {f.rule_code for f in findings}
    assert "SEC_EVASION" in rule_codes
    assert "SEC_FORK" in rule_codes or "SEC_FORKBOMB" in rule_codes
    assert "SEC_EXEC" in rule_codes


def test_generate_personalized_feedback_markdown():
    analysis = {
        "compilation": {"success": True, "compiler_used": "ESPER"},
        "ast_findings": [
            {"rule_code": "0x1001h", "severity": "ESTILO", "suggestion": "Envolvé con llaves"}
        ],
        "tests": {
            "total": 2,
            "passed": 2,
            "failed": 0,
            "cases": [{"name": "caso1", "passed": True}, {"name": "caso2", "passed": True}],
        },
    }
    feedback = generate_personalized_feedback_markdown("Gomez Maria", "tp01", analysis, revision="r1")
    assert "Gomez Maria" in feedback
    assert "ENTREGA APROBADA" in feedback
    assert "0x1001h" in feedback
    assert "ESPER" in feedback


def test_generate_plagiarism_html_report(tmp_path: Path):
    sub_dir = tmp_path / "entregas"
    sub_dir.mkdir()

    s1 = sub_dir / "alumno_a"
    s1.mkdir()
    (s1 / "main.c").write_text("int main(void) { int a = 10; return a; }")

    s2 = sub_dir / "alumno_b"
    s2.mkdir()
    (s2 / "main.c").write_text("int main(void) { int a = 10; return a; }")

    matches = [
        SimilarityMatch(
            student_a="alumno_a",
            student_b="alumno_b",
            similarity_pct=95.0,
            shared_fingerprints=15,
            total_a=15,
            total_b=15,
        )
    ]

    out_html = tmp_path / "plagio.html"
    res_path = generate_plagiarism_html_report(sub_dir, matches, out_html)
    assert res_path.is_file()
    content = res_path.read_text(encoding="utf-8")
    assert "alumno_a" in content
    assert "alumno_b" in content
    assert "95.0%" in content
