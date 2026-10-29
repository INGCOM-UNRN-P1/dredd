"""Banco organizado por tema, ids genéricos con mapeo y casos de funciones con driver (Ola 32)."""

import shutil
from pathlib import Path

import pytest

from dredd.core.guide_integration import ID_GENERICO, id_en_banco, load_activity_guide
from dredd.core.ripley_client import evaluate_guide_testcases

DRIVER = """#include <stdio.h>
#include <string.h>
int doble(int n);
int main(void)
{
    char f[64];
    int n;
    while (scanf("%63s %d", f, &n) == 2)
        printf("%d\\n", doble(n));
    return 0;
}
"""


def _banco(tmp_path: Path) -> Path:
    banco = tmp_path / "banco"
    doble = banco / "funciones" / "ej-doble"
    (doble / "tests" / "funciones").mkdir(parents=True)
    (doble / "ejercicio.yaml").write_text("id: ej-doble\ntitulo: Doble\ntema: funciones\nbloom: 1\n", encoding="utf-8")
    (doble / "tests" / "funciones" / "driver.c").write_text(DRIVER, encoding="utf-8")
    for i, n in enumerate((0, -3, 21), 1):
        (doble / "tests" / "funciones" / f"doble_{i:02d}.in").write_text(f"doble {n}\n", encoding="utf-8")
        (doble / "tests" / "funciones" / f"doble_{i:02d}.out").write_text(f"{2 * n}\n", encoding="utf-8")
    # Un ejercicio del banco con id genérico (como los TDA): no tiene que tomarse por el `ejercicio1` de un TP.
    tda = banco / "tipos_datos_abstractos" / "ejercicio1"
    (tda / "tests").mkdir(parents=True)
    (tda / "ejercicio.yaml").write_text("id: ejercicio1\ntitulo: TDA\ntema: tad\nbloom: 3\n", encoding="utf-8")
    (tda / "tests" / "a.in").write_text("x\n", encoding="utf-8")
    return banco


def _ws(tmp_path: Path, mapeo: str = "") -> Path:
    ws = tmp_path / "ws"
    (ws / "guias" / "e").mkdir(parents=True)
    (ws / "dredd.yaml").write_text(
        f"workspace:\n  deckard_bank_dir: {_banco(tmp_path)}\nmapeos:\n- entrega: e\n  guia: guias/e/guia.yaml\n{mapeo}",
        encoding="utf-8")
    (ws / "guias" / "e" / "guia.yaml").write_text("nombre: E\nejercicios:\n- id: ej-doble\n- id: ejercicio1\n",
                                                  encoding="utf-8")
    return ws


def test_ids_genericos_solo_con_mapeo():
    assert ID_GENERICO.match("ejercicio10") and ID_GENERICO.match("entrega_2") and not ID_GENERICO.match("ej-doble")
    assert id_en_banco("ejercicio1") is None
    assert id_en_banco("ejercicio1", {"ejercicio1": "ej-doble"}) == "ej-doble"
    assert id_en_banco("ejercicio1", None, {"banco": "ej-doble"}) == "ej-doble"
    assert id_en_banco("ej-doble") == "ej-doble"


def test_banco_por_tema_y_mapeo(tmp_path):
    guia = load_activity_guide(_ws(tmp_path), "e", tmp_path / "ws")
    por_id = {e.id: e for e in guia.exercises}
    assert por_id["ej-doble"].exercise_dir.name == "ej-doble" and por_id["ej-doble"].tiene_casos
    assert not por_id["ejercicio1"].tiene_casos           # el TDA del banco no se cuela

    mapeado = load_activity_guide(_ws(tmp_path / "m", "  ejercicios_banco:\n    ejercicio1: ej-doble\n"), "e",
                                  tmp_path / "m" / "ws")
    assert {e.id: e.tiene_casos for e in mapeado.exercises} == {"ej-doble": True, "ejercicio1": True}


@pytest.mark.skipif(shutil.which("gcc") is None, reason="requiere gcc")
def test_casos_de_funciones_con_el_main_del_alumno(tmp_path):
    guia = load_activity_guide(_ws(tmp_path), "e", tmp_path / "ws")
    entrega = tmp_path / "entrega"
    entrega.mkdir()
    (entrega / "doble.c").write_text(
        "#include <stdio.h>\nint doble(int n);\nint doble(int n) { return n + n; }\n"
        'int main(void) { printf("hola\\n"); return 0; }\n', encoding="utf-8")
    casos = [c for c in evaluate_guide_testcases(entrega, guia, "archivos_individuales") if "funciones" in c["name"]]
    assert len(casos) == 3 and all(c["passed"] for c in casos)

    (entrega / "doble.c").write_text("int otra(int n);\nint otra(int n) { return n; }\nint main(void) { return 0; }\n",
                                     encoding="utf-8")
    casos = [c for c in evaluate_guide_testcases(entrega, guia, "archivos_individuales") if "funciones" in c["name"]]
    assert casos and not any(c["passed"] for c in casos)
    assert "driver de las funciones" in casos[0]["sanitizer_error"]
