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


def test_audit_detects_variable_lengths(tmp_path: Path):
    src = tmp_path / "var_lengths.c"
    src.write_text(
        """#include <stdio.h>
int main(void) {
    int p = 1;
    int id = 2;
    int aux = 3;
    int variable_con_nombre_super_recontra_re_largo_que_supera_los_treinta_y_un_caracteres = 4;
    return 0;
}
""",
        encoding="utf-8",
    )
    findings = audit_c_file(src)
    r_0001 = [f for f in findings if f["rule_id"] == "0x0001h"]
    assert any("'p'" in f["message"] for f in r_0001)
    assert any("'id'" in f["message"] for f in r_0001)
    assert any("'aux'" in f["message"] for f in r_0001)
    assert any("variable_con_nombre_super" in f["message"] for f in r_0001)


def test_dredd_gaff_variable_length_analysis(tmp_path: Path):
    from dredd.core.ripley_client import audit_style_with_gaff, run_ripley_analysis
    from dredd.core.config import ToolChecksConfig

    src = tmp_path / "vars.c"
    src.write_text(
        """#include <stdio.h>
int main(void) {
    int id = 10;
    int aux = 20;
    int variable_con_nombre_super_recontra_re_largo_que_supera_los_treinta_y_un_caracteres = 30;
    return 0;
}
""",
        encoding="utf-8",
    )

    # 1. Chequeo directo de audit_style_with_gaff sobre archivo
    findings, _ = audit_style_with_gaff(src)
    msgs = [f["message"] for f in findings if f["rule_code"] in ("0x0001h", "0x0101h", "GAFF011")]
    assert any("'id'" in m for m in msgs)
    assert any("'aux'" in m for m in msgs)
    assert any("variable_con_nombre_super" in m for m in msgs)

    # 2. Chequeo a través de run_ripley_analysis con strict preset (ripley_rules = ['all'])
    strict_cfg = ToolChecksConfig.get_strict_preset()
    res = run_ripley_analysis(tmp_path, checks_override=strict_cfg)
    style_findings = res.get("style_findings", [])
    style_msgs = [f["message"] for f in style_findings if f["rule_code"] in ("0x0001h", "0x0101h", "GAFF011")]
    assert any("'id'" in m for m in style_msgs)
    assert any("'aux'" in m for m in style_msgs)
    assert any("variable_con_nombre_super" in m for m in style_msgs)

    # ast_findings no debe descartarse cuando ripley_rules es ['all']
    ast_findings = res.get("ast_findings", [])
    assert len(ast_findings) > 0
    ast_msgs = [f["message"] for f in ast_findings if f["rule_code"] in ("0x0001h", "GAFF011")]
    assert any("'id'" in m for m in ast_msgs)


def test_check_regla_0x0001_complex_macros_and_function_pointers():
    from dredd.core.ast_checker import check_regla_0x0001, _find_identifier

    # Casos límite: función puntero como argumento, macros multilinea, void
    code = """
    #define DO_SOMETHING(x) do { int _local_macro = (x); } while(0)
    static inline void setup(void (**prev_segv)(int), void (*callback)(void *ctx)) {
        int a = 1;
        int *b = &a;
        char arr[10];
    }
    """
    vars_found = check_regla_0x0001(code)
    var_names = [name for name, _ in vars_found]
    assert "a" in var_names
    assert "b" in var_names
    assert "arr" in var_names
    assert "prev_segv" in var_names
    assert "callback" in var_names
    assert "void" not in var_names

    # _find_identifier con None
    assert _find_identifier(None) is None


def test_audit_style_excludes_p1_test_framework(tmp_path: Path):
    from dredd.core.ripley_client import audit_style_with_gaff

    # Archivo del alumno
    student_c = tmp_path / "main.c"
    student_c.write_text("int main(void) { int id = 1; return id; }\n", encoding="utf-8")

    # Archivo de framework de test provisto por cátedra
    test_dir = tmp_path / "libs" / "p1_test"
    test_dir.mkdir(parents=True)
    p1_h = test_dir / "p1_test.h"
    p1_h.write_text("int p = 1;\n", encoding="utf-8")

    findings, _ = audit_style_with_gaff(tmp_path)
    files_audited = {f["file"] for f in findings}
    assert "main.c" in files_audited
    assert "p1_test.h" not in files_audited


