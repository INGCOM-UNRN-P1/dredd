"""Unit tests for Dredd native AST and P1 rules checker."""

from pathlib import Path
from dredd.core.ast_checker import audit_c_file, check_regla_0x000Bh, check_regla_0x001Ch, check_regla_0xEEEE


def test_audit_detects_global_variable(tmp_path: Path):
    src = tmp_path / "global_var.c"
    src.write_text(
        """#include <stdio.h>
int contador_global = 0;
int main(void) {
    contador_global++;
    return 0;
}
""",
        encoding="utf-8",
    )
    findings = audit_c_file(src)
    assert any(f["rule_id"] == "0x000Bh" for f in findings)


def test_audit_detects_gets_usage(tmp_path: Path):
    src = tmp_path / "inseguro.c"
    src.write_text(
        """#include <stdio.h>
int main(void) {
    char buf[100];
    gets(buf);
    return 0;
}
""",
        encoding="utf-8",
    )
    findings = audit_c_file(src)
    assert any(f["rule_id"] == "0x001Ch" for f in findings)


def test_audit_clean_file_no_findings(tmp_path: Path):
    src = tmp_path / "limpio.c"
    src.write_text(
        """#include <stdio.h>

int duplicar(const int valor) {
    return valor * 2;
}

int main(void) {
    int numero = 5;
    int resultado = duplicar(numero);
    printf("%d\\n", resultado);
    return 0;
}
""",
        encoding="utf-8",
    )
    findings = audit_c_file(src)
    # No debe haber errores bloqueantes
    assert not any(f["severity"] == "ERROR" for f in findings)
