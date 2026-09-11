"""Pruebas de integración de Spunkmeyer en Dredd."""

from pathlib import Path
import pytest

from dredd.core.config import ToolChecksConfig
from dredd.core.ripley_client import audit_antipatterns_with_spunkmeyer, run_ripley_analysis
from dredd.core.reporter import write_individual_tool_reports, generate_personalized_feedback_markdown


C_CODE_WITH_ANTIPATTERNS = """#include <stdio.h>
#include <stdlib.h>

int main(void) {
    FILE *f = fopen("datos.txt", "r");
    if (!f) return 1;

    // 1. Antipatrón 0x4002h: while(!feof())
    while (!feof(f)) {
        int x;
        if (fscanf(f, "%d", &x) == 1) {
            printf("%d\\n", x);
        }
    }
    fclose(f);

    // 2. Antipatrón 0x300Ah: Casteo explícito de malloc
    int *arr = (int *)malloc(10 * sizeof(int));
    if (arr != NULL) {
        arr[0] = 42;
    }

    // 3. Antipatrón 0x3008h: Chequeo redundante de NULL antes de free
    if (arr != NULL) {
        free(arr);
    }

    return 0;
}
"""


def test_audit_antipatterns_with_spunkmeyer_direct(tmp_path: Path):
    c_file = tmp_path / "main.c"
    c_file.write_text(C_CODE_WITH_ANTIPATTERNS, encoding="utf-8")

    checks = ToolChecksConfig(spunkmeyer_enabled=True, ban_feof_loop=True)
    findings = audit_antipatterns_with_spunkmeyer(c_file, checks=checks)

    assert len(findings) >= 2
    rule_codes = {f["rule_code"] for f in findings}
    assert "0x4002h" in rule_codes or "0x300Ah" in rule_codes or "0x3008h" in rule_codes

    for f in findings:
        assert "file" in f
        assert "line" in f
        assert "message" in f
        assert "suggestion" in f


def test_audit_antipatterns_feof_disabled(tmp_path: Path):
    c_file = tmp_path / "main.c"
    c_file.write_text(C_CODE_WITH_ANTIPATTERNS, encoding="utf-8")

    # ban_feof_loop = False -> no debe reportar 0x4002h
    checks = ToolChecksConfig(spunkmeyer_enabled=True, ban_feof_loop=False)
    findings = audit_antipatterns_with_spunkmeyer(c_file, checks=checks)

    rule_codes = {f["rule_code"] for f in findings}
    assert "0x4002h" not in rule_codes


def test_run_ripley_check_includes_spunkmeyer(tmp_path: Path):
    c_file = tmp_path / "main.c"
    c_file.write_text(C_CODE_WITH_ANTIPATTERNS, encoding="utf-8")

    checks = ToolChecksConfig(spunkmeyer_enabled=True, ban_feof_loop=True)
    res = run_ripley_analysis(tmp_path, checks_override=checks)

    assert "spunkmeyer_findings" in res
    assert len(res["spunkmeyer_findings"]) >= 2


def test_reporter_spunkmeyer_markdown_and_feedback(tmp_path: Path):
    rni_dir = tmp_path / "r1i"
    rni_dir.mkdir(parents=True)

    analysis = {
        "compilation": {"success": True, "compiler_used": "gcc"},
        "ast_findings": [],
        "tests": {"total": 1, "passed": 1, "failed": 0},
        "spunkmeyer_findings": [
            {
                "rule_code": "0x300Ah",
                "name": "Casteo explícito del retorno de malloc",
                "file": "main.c",
                "line": 18,
                "message": "Casteo innecesario del retorno de malloc.",
                "suggestion": "Asignar directamente sin casteo explícito.",
                "explanation": "En C no es necesario castear void*.",
                "code_line": "int *arr = (int *)malloc(10 * sizeof(int));",
                "example_bad": "int *p = (int *)malloc(sizeof(int));",
                "example_good": "int *p = malloc(sizeof(int));",
            },
            {
                "rule_code": "0x4002h",
                "name": "Uso de feof() como condición de control de ciclo",
                "file": "main.c",
                "line": 9,
                "message": "El ciclo while(!feof(f)) produce una iteración espuria.",
                "suggestion": "Controlar el ciclo con el valor de retorno de la función de lectura.",
                "explanation": "feof() se activa tras un intento fallido de lectura.",
            },
        ],
    }

    generated = write_individual_tool_reports(rni_dir, analysis)
    assert "spunkmeyer" in generated
    spk_path = rni_dir / "spunkmeyer.md"
    assert spk_path.is_file()

    content = spk_path.read_text(encoding="utf-8")
    assert "Antipatrones Didácticos — Spunkmeyer" in content
    assert "0x300Ah" in content
    assert "0x4002h" in content
    assert "Casteo explícito del retorno de malloc" in content
    assert "Asignar directamente sin casteo explícito." in content

    # Feedback general
    feedback = generate_personalized_feedback_markdown("perez_juan", "tp01", analysis)
    assert "Spunkmeyer" in feedback
    assert "0x300Ah" in feedback
