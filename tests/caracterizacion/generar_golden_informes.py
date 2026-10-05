"""Genera golden_informes.json: los .md que escribe `write_individual_tool_reports` para varios
análisis que pasan por todas sus secciones. Se generó ANTES de partir la función."""

import hashlib
import json
import tempfile
from pathlib import Path

AQUI = Path(__file__).parent


def _caso(i, ok, **extra):
    base = {"name": f"caso{i}", "passed": ok, "input_data": f"{i}\n", "expected_output": f"{i * 2}\n",
            "actual_output": f"{i * 2 if ok else i}\n", "return_code": 0 if ok else 1, "timed_out": False,
            "memory_leak": False, "diff": "" if ok else f"-{i * 2}\n+{i}\n", "sanitizer_error": ""}
    base.update(extra)
    return base


def analisis():
    lleno = {
        "compilation": {"success": False, "compiler_used": "gcc", "is_project": False, "human_summary": "Falló.",
                        "raw_stderr": "main.c:3:5: error: x", "files": {"main.c": {"success": False}, "util.c": {"success": True}},
                        "translated_diagnostics": [{"file": "main.c", "line": 3, "message": "falta ;", "suggestion": "agregá ;",
                                                    "rule_code": "E1", "rule_name": "punto y coma"}]},
        "ast_findings": [{"file": "main.c", "line": 4, "rule_code": "0x3001h", "rule_id": "0x3001h", "rule_name": "malloc",
                          "message": "sin verificar", "suggestion": "verificá", "severity": "ERROR"},
                         {"file": "util.c", "line": 9, "rule_code": "KAN001", "rule_id": "KAN001", "rule_name": "gets",
                          "message": "gets", "suggestion": "fgets", "severity": "CRITICO", "source_plugin": "security"}],
        "style_findings": [{"file": "main.c", "line": 1, "rule_code": "0x0001h", "rule_id": "0x0001h", "name": "nombre",
                            "message": "estilo", "suggestion": "s", "autofixable": True, "alias": "A1", "code_line": "int X;",
                            "explanation": "e", "example_bad": "int X;", "example_good": "int x;"}],
        "spunkmeyer_findings": [{"file": "main.c", "line": 7, "rule_code": "0x300Ah", "name": "cast", "message": "cast",
                                 "suggestion": "sin cast", "explanation": "x", "example_bad": "(int*)malloc", "example_good": "malloc"}],
        "tests": {"total": 3, "passed": 1, "has_test_target": True, "is_project": False,
                  "cases": [_caso(1, True), _caso(2, False), _caso(3, False, memory_leak=True, sanitizer_error="leak", timed_out=True)]},
        "valgrind": {"executed": True, "clean": False, "errors": [{"kind": "InvalidRead", "message": "Invalid read of size 4"}, {"kind": "Leak_DefinitelyLost", "message": "8 bytes"}]},
        "binary_findings": [{"file": "a.out", "message": "binario"}],
        "baseline_info": {"has_baseline": True, "completed": ["ej1"], "uncompleted": ["ej2"]},
        "similarity": {"pares": [{"a": "x", "b": "y", "similitud": 0.9}]},
        "oral_questions": [{"concepto": "punteros", "linea": 4, "respuesta_esperada": "r"}],
    }
    vacio = {"compilation": {"success": True}, "tests": {"cases": []}, "valgrind": {}}
    medio = dict(lleno, compilation={"success": True, "files": {"main.c": {"success": True}}},
                 valgrind={"executed": True, "clean": True, "errors": []}, binary_findings=[], baseline_info={})
    return {"lleno": lleno, "vacio": vacio, "medio": medio}


def golden():
    from dredd.core.reporter import write_individual_tool_reports

    resultado = {}
    for nombre, datos in analisis().items():
        with tempfile.TemporaryDirectory() as tmp:
            generados = write_individual_tool_reports(Path(tmp) / "r1i", json.loads(json.dumps(datos)))
            resultado[nombre] = {clave: hashlib.sha256(ruta.read_bytes()).hexdigest()
                                 for clave, ruta in sorted(generados.items())}
    return resultado


if __name__ == "__main__":
    (AQUI / "golden_informes.json").write_text(json.dumps(golden(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
