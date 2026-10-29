"""Targets del docente (dredd.mk de deckard) en la corrección (Ola 30)."""

import json
import shutil
from pathlib import Path

import pytest

from dredd.core.auditoria import resultado_del_analisis
from dredd.core.targets_docente import aplicar_a_nota, correr, proteger, seccion_markdown, verificar

pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="requiere make")

RAIZ_MK = "librerias:\n\t@true\n-include local.mk\n-include dredd.mk\n"
EJ_MK = "ROOT_DIR = ../..\nall:\n\t@true\n-include local.mk\n-include $(ROOT_DIR)/dredd.mk\n"
DREDD_MK = """DREDD_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
DREDD_EJERCICIO := $(notdir $(CURDIR))
.PHONY: dredd-ocultas dredd-estilo
dredd-ocultas:
ifneq ($(filter $(DREDD_EJERCICIO),suma lista),)
\t@test -f solucion_ok
\t@cat $(DREDD_DIR)/.dredd/dato.txt
else
\t@echo "no aplica"
endif
dredd-estilo:
ifneq ($(filter $(DREDD_EJERCICIO),suma),)
\t@echo '{"hallazgos": 2}' > estilo.json
else
\t@echo "no aplica"
endif
"""
TARGETS = {
    "schema_version": "1.0.0", "guia": "G", "ejercicios": ["suma", "lista"],
    "targets": [
        {"nombre": "ocultas", "target": "dredd-ocultas", "descripcion": "Casos ocultos", "tipo": "pruebas_ocultas",
         "ejercicios": ["suma", "lista"], "produce": "codigo", "archivo": None, "peso": 30, "visible": False},
        {"nombre": "estilo", "target": "dredd-estilo", "descripcion": "Estilo", "tipo": "comando",
         "ejercicios": ["suma"], "produce": "json", "archivo": "estilo.json", "peso": 10, "visible": True},
    ],
}


@pytest.fixture
def practica(tmp_path):
    entrega, docente = tmp_path / "entrega", tmp_path / "docente"
    for eid in ("suma", "lista"):
        (entrega / "ejercicios" / eid).mkdir(parents=True)
        (entrega / "ejercicios" / eid / "Makefile").write_text(EJ_MK, encoding="utf-8")
    (entrega / "ejercicios" / "suma" / "solucion_ok").write_text("", encoding="utf-8")   # lista falla
    (entrega / "Makefile").write_text(RAIZ_MK, encoding="utf-8")
    (docente / ".dredd").mkdir(parents=True)
    (docente / ".dredd" / "dato.txt").write_text("oculto\n", encoding="utf-8")
    (docente / "dredd.mk").write_text(DREDD_MK, encoding="utf-8")
    (docente / "targets.json").write_text(json.dumps(TARGETS), encoding="utf-8")
    return entrega, docente


def test_corre_los_targets_y_deja_la_entrega_como_estaba(practica):
    entrega, docente = practica
    corrida = correr(entrega, docente).to_dict()
    por = {(r["target"], r["ejercicio"]): r for r in corrida["resultados"]}
    assert por[("dredd-ocultas", "suma")]["aprobado"] and "oculto" in por[("dredd-ocultas", "suma")]["salida"]
    assert not por[("dredd-ocultas", "lista")]["aprobado"]
    assert por[("dredd-estilo", "suma")]["datos"] == {"hallazgos": 2}
    # ocultas: la mitad (30 × 0,5) + estilo entero (10) sobre 40
    assert corrida["puntaje"] == pytest.approx(25 / 40) and corrida["peso_total"] == 40
    assert not (entrega / "dredd.mk").exists() and not (entrega / ".dredd").exists()
    assert corrida["alertas"] == []


def test_el_gancho_no_se_puede_usurpar(practica):
    entrega, docente = practica
    (entrega / "dredd.mk").write_text("dredd-ocultas:\n\t@true\n", encoding="utf-8")
    (entrega / "ejercicios" / "lista" / "local.mk").write_text("dredd-ocultas:\n\t@true\n", encoding="utf-8")
    corrida = correr(entrega, docente).to_dict()
    assert any("su propio dredd.mk" in a for a in corrida["alertas"])
    assert any("ejercicios/lista/local.mk define dredd-ocultas" in a for a in corrida["alertas"])
    lista = next(r for r in corrida["resultados"] if r["target"] == "dredd-ocultas" and r["ejercicio"] == "lista")
    assert not lista["aprobado"]            # vale la receta del docente, no la del alumno


def test_seccion_para_el_alumno_y_nota(practica):
    entrega, docente = practica
    datos = correr(entrega, docente).to_dict()
    alumno = seccion_markdown(datos, para_alumno=True)
    assert "Estilo" in alumno and "Casos ocultos" not in alumno and "```text" not in alumno
    docente_md = seccion_markdown(datos)
    assert "Casos ocultos" in docente_md and "Puntaje ponderado" in docente_md
    assert aplicar_a_nota(10.0, {"puntaje": 25 / 40, "peso_total": 40}) == pytest.approx(6.0 + 2.5)
    assert aplicar_a_nota(8.0, None) == 8.0
    resultado = resultado_del_analisis({"compilation": {"success": True}, "tests": {}, "targets_docente": datos})
    assert resultado["targets_docente"]["peso_total"] == 40


def test_verificar(practica, tmp_path):
    _, docente = practica
    assert verificar(docente) == []
    (docente / "dredd.mk").write_text("dredd-ocultas:\n\t@true\n", encoding="utf-8")
    assert verificar(docente) == [f"{docente}: el target dredd-estilo está en targets.json pero no en dredd.mk"]
    assert "falta dredd.mk" in verificar(tmp_path / "nada")[0]


def test_proteger_sin_nada_raro(practica):
    entrega, _ = practica
    assert proteger(entrega) == []


def test_config_validate_y_carpeta_de_la_actividad(practica, tmp_path):
    from dredd.core.config import load_dredd_config, validate_workspace

    _, docente = practica
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "dredd.yaml").write_text(
        f"mapeos:\n- entrega: tp3\n  source: github\n  targets_docente: {docente}\n", encoding="utf-8")
    cfg = load_dredd_config(ws)
    assert cfg.get_targets_dir("tp3") == docente
    assert ("OK", "targets:tp3", f"2 targets del docente en {docente}") in validate_workspace(ws)
