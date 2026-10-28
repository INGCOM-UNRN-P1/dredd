"""Ola 17: en las actividades de TDAs dredd corre `motoko check --json`, suma sus hallazgos a
hallazgos.json (los descuenta deckard en el criterio de diseño) y agrega la sección de calidad de
abstracción al informe."""

from pathlib import Path

import pytest

from dredd.core.cohorte import a_hallazgos
from dredd.core.config import DreddConfig, MappingRule, ToolChecksConfig
from dredd.core.ecosystem import resolve_sibling_cli
from dredd.core.reporter import write_individual_tool_reports
from dredd.core.ripley_client import _carpetas_de_tdas, _collect_motoko


necesita_motoko = pytest.mark.skipif(not resolve_sibling_cli("motoko"), reason="hace falta motoko")


@pytest.fixture
def entrega(tmp_path: Path) -> Path:
    ej = tmp_path / "ejercicios" / "ejercicio1"
    ej.mkdir(parents=True)
    (ej / "pila.h").write_text("typedef struct s_pila pila_t;\nint pila_tope(const pila_t *p);\n"
                               "pila_t *pila_crear(void);\n", encoding="utf-8")
    (ej / "pila.c").write_text('#include <stdlib.h>\n#include "pila.h"\nstruct s_pila { int tope; };\n'
                               "pila_t *pila_crear(void) { return calloc(1, sizeof(pila_t)); }\n"
                               "int pila_tope(const pila_t *p) { return p->tope; }\n", encoding="utf-8")
    (ej / "main.c").write_text('#include "pila.h"\nstruct s_pila { int tope; };\n'
                               "int main(void) { pila_t *p = pila_crear(); return p->tope; }\n", encoding="utf-8")
    sin_hacer = tmp_path / "ejercicios" / "ejercicio2"
    sin_hacer.mkdir()
    (sin_hacer / "cola.h").write_text("typedef struct { int frente; } cola_t;\n", encoding="utf-8")
    lib = tmp_path / "libs" / "p1_test"
    lib.mkdir(parents=True)
    (lib / "p1.h").write_text("typedef struct { int x; } p1_t;\n", encoding="utf-8")
    return tmp_path


def test_el_tema_de_la_actividad_activa_motoko():
    cfg = DreddConfig(mapeos=[MappingRule(zip_pattern="", entrega="TP5", tema="tad"),
                              MappingRule(zip_pattern="", entrega="TP1", tema="control")])
    assert not cfg.checks.motoko_enabled
    assert cfg.get_effective_checks("TP5").motoko_enabled
    assert not cfg.get_effective_checks("TP1").motoko_enabled
    assert ToolChecksConfig.from_dict({"motoko": {"enabled": True}}).motoko_enabled
    assert ToolChecksConfig.from_dict(ToolChecksConfig(motoko_enabled=True).to_dict()).motoko_enabled
    assert "tema: tad" in cfg.to_yaml()


def test_carpetas_sin_los_ejercicios_sin_completar(entrega):
    assert [p.name for p in _carpetas_de_tdas(entrega, {"ejercicio2"})] == ["ejercicio1"]
    assert _carpetas_de_tdas(entrega / "libs", set()) == [entrega / "libs"]


@necesita_motoko
def test_motoko_en_la_entrega_y_en_hallazgos(entrega):
    motoko = _collect_motoko(entrega, {"ejercicio2"})
    codigos = sorted((f["rule_code"], f["file"]) for f in motoko["findings"])
    assert ("MOT004", "ejercicios/ejercicio1/main.c") in codigos
    assert ("MOT002", "ejercicios/ejercicio1/main.c") in codigos
    assert not any("libs/" in f or "ejercicio2" in f for _, f in codigos)
    mot002 = next(f for f in motoko["findings"] if f["rule_code"] == "MOT002")
    assert "pila_tope(p)" in mot002["suggestion"]

    hallazgos = a_hallazgos({"motoko": motoko})
    assert {h["herramienta"] for h in hallazgos} == {"motoko"}
    assert {h["categoria"] for h in hallazgos} == {"tad"}  # deckard: criterio modularidad_y_diseño


@necesita_motoko
def test_seccion_de_calidad_de_abstraccion(entrega, tmp_path):
    rni = tmp_path / "i_abc1234"
    generados = write_individual_tool_reports(rni, {"motoko": _collect_motoko(entrega, {"ejercicio2"})})
    texto = generados["motoko"].read_text(encoding="utf-8")
    assert texto.startswith("## 🧱 Calidad de abstracción (TDAs)")
    assert "`MOT004`" in texto and "modularidad_y_diseño" in texto
    # Sin el perfil de TDAs no hay sección (y una vieja no sobrevive).
    assert "motoko" not in write_individual_tool_reports(rni, {})
    assert not (rni / "motoko.md").exists()


def test_sin_motoko_instalado_lo_dice(tmp_path, monkeypatch):
    import dredd.core.ripley_client as rc

    monkeypatch.setattr(rc, "resolve_sibling_cli", lambda nombre: None)
    motoko = rc._collect_motoko(tmp_path, set())
    assert motoko == {"disponible": False, "findings": [], "resumen": [], "tdas": 0}
    texto = write_individual_tool_reports(tmp_path / "r", {"motoko": motoko})["motoko"].read_text(encoding="utf-8")
    assert "no está instalado" in texto
