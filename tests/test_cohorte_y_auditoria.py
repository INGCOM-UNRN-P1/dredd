"""Hallazgos comunes, «Para repasar», errores por cohorte (QoL #331) y registro de auditoría."""

import json
from pathlib import Path

from typer.testing import CliRunner

from dredd.cli import app
from dredd.core.auditoria import leer_registros, registrar, versiones_distintas
from dredd.core.cohorte import agrupar_cohorte, escribir

runner = CliRunner()


def _analisis(*codigos):
    return {"ast_findings": [{"rule_code": c, "severity": "ERROR", "file": "main.c", "line": i + 1,
                              "message": f"falla {c}", "source_plugin": "gaff"} for i, c in enumerate(codigos)]}


def test_hallazgos_y_para_repasar(tmp_path):
    hallazgos = escribir(tmp_path / "r1i", _analisis("0x3001h", "0x3001h", "0x1002h", "KAN001"))
    assert {h["id"] for h in hallazgos} == {"gaff:0x3001h", "gaff:0x1002h", "gaff:KAN001"}
    repaso = (tmp_path / "r1i" / "para_repasar.md").read_text(encoding="utf-8")
    assert "## Para repasar" in repaso and "/memoria-dinamica" in repaso and "/x3001h" in repaso


def test_cluster_por_estudiante_y_ultima_revision(tmp_path):
    escribir(tmp_path / "ana" / "r1i", _analisis("0x3001h", "0x1002h"))
    escribir(tmp_path / "ana" / "r2i", _analisis("0x3001h"))  # corrigió 0x1002h en la segunda
    escribir(tmp_path / "luis" / "r1i", _analisis("0x3001h"))
    datos = agrupar_cohorte(tmp_path)
    assert datos["estudiantes"] == 2
    assert datos["errores"][0] == {"id": "gaff:0x3001h", "alumnos": 2, "porcentaje": 100.0, "categoria": "memoria",
                                   "enlace": datos["errores"][0]["enlace"], "ejemplo": "falla 0x3001h"}
    assert len(datos["errores"]) == 1
    res = runner.invoke(app, ["cluster-errors", str(tmp_path), "--json"])
    assert json.loads(res.stdout)["temas"][0]["categoria"] == "memoria"


def test_auditoria(tmp_path, monkeypatch):
    import dredd.core.auditoria as auditoria

    registrar(tmp_path / "ana" / "r1i", "ana", "tp1", "r1", commit="abc")
    monkeypatch.setattr(auditoria, "versiones_del_ecosistema", lambda: {"gaff": "9.9.9"})
    registrar(tmp_path / "luis" / "r1i", "luis", "tp1", "r1")
    registrar(tmp_path / "eva" / "r1i", "eva", "tp1", "r1")
    registros = leer_registros(tmp_path)
    assert len(registros) == 3 and registros[0]["commit"] == "abc"
    distintas = versiones_distintas(registros)
    assert list(distintas) == [str(tmp_path / "ana" / "r1i" / "auditoria.json")]
    res = runner.invoke(app, ["audit-versions", str(tmp_path), "--alumno", "luis", "--json"])
    assert [r["alumno"] for r in json.loads(res.stdout)["registros"]] == ["luis"]
