"""`dredd cohorte`: planilla de seguimiento de una cohorte de Classroom (Ola 25)."""

import csv
import json
import re
import subprocess
import sys
from datetime import datetime

from dredd.core.seguimiento import analizar_cohorte, escribir, frecuentes, veredicto

RIPLEY_FALSO = r'''
import json, pathlib, sys
codigo = pathlib.Path("src/main.c").read_text()
errores = 1 if "goto" in codigo else 0
compila = "ROTO" not in codigo
hallazgos = [{"codigo": "0x1006h", "severidad": "error", "categoria": "control", "mensaje": "goto",
              "enlace": "https://ingcom-unrn-p1.github.io/x1006h"}] if errores else []
print(json.dumps({"compilation": {"success": compila}, "metrics": {"ast_errors_count": errores,
      "ast_findings_count": errores}, "tests": {"total": 2, "passed": 2 - errores, "failed": errores},
      "hallazgos": hallazgos}))
'''


def _repo(base, nombre, codigo, fecha):
    d = base / nombre
    (d / "src").mkdir(parents=True)
    git = ["git", "-C", str(d)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "-c", "user.name=github-classroom[bot]", "-c", "user.email=b@x", "commit", "-q",
                    "--allow-empty", "-m", "init"], check=True)
    if codigo is not None:
        (d / "src" / "main.c").write_text(codigo, encoding="utf-8")
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "-c", f"user.name={nombre}", "-c", "user.email=a@x", "commit", "-q", "-m", "e",
                        "--date", fecha], check=True, env={"GIT_COMMITTER_DATE": fecha, "PATH": "/usr/bin:/bin"})


def test_planilla_de_la_cohorte(tmp_path):
    ripley = tmp_path / "ripley"
    ripley.write_text(f"#!{sys.executable}\n{RIPLEY_FALSO}", encoding="utf-8")
    ripley.chmod(0o755)
    entregas = tmp_path / "entregas"
    _repo(entregas, "tp1-ana", "int main(void) { return 0; }", "2026-11-03T10:00:00-03:00")
    _repo(entregas, "tp1-beto", "goto", "2026-11-01T10:00:00-03:00")
    _repo(entregas, "tp1-caro", None, "")
    _repo(entregas, "tp1-dani", "ROTO", "2026-11-02T10:00:00-03:00")
    informe = analizar_cohorte(entregas, ruta="src", prefijo="tp1-", ripley=str(ripley),
                               fecha_limite=datetime.fromisoformat("2026-11-02T23:59:00-03:00"))
    por_alumno = {e["alumno"]: e for e in informe["entregas"]}
    assert {a: e["estado"] for a, e in por_alumno.items()} == {
        "ana": "aprobada", "beto": "con errores", "caro": "sin entrega", "dani": "no compila"}
    assert por_alumno["ana"]["atraso_horas"] == 10.0 and por_alumno["beto"]["atraso_horas"] == 0.0
    assert por_alumno["caro"]["commits"] == 0  # el commit del bot de Classroom no cuenta
    assert informe["frecuentes"][0]["codigo"] == "0x1006h"

    # Índice por concepto sobre las entregas analizadas (ni la vacía ni... la que no compila también cuenta).
    assert informe["analizadas"] == 3
    assert [(t["categoria"], t["alumnos"], t["porcentaje"]) for t in informe["temas"]] == [("control", 1, 33.3)]

    csv_, md, js, conceptos = escribir(informe, tmp_path / "salida")
    anonimo = conceptos.read_text(encoding="utf-8")
    assert "33.3 %" in anonimo and "1/3" in anonimo
    assert not re.search(r"\b(ana|beto|caro|dani)\b|tp1-", anonimo)
    filas = list(csv.DictReader(csv_.open(encoding="utf-8")))
    assert [f["alumno"] for f in filas] == ["ana", "beto", "caro", "dani"]
    texto = md.read_text(encoding="utf-8")
    assert "| 1 | 1 | 1 | 1 | 0 |" in texto and "[0x1006h](https://" in texto
    assert json.loads(js.read_text(encoding="utf-8"))["totales"]["alumnos"] == 4


def test_veredicto_por_perfil():
    con_estilo = {"compilation": {"success": True}, "metrics": {"ast_errors_count": 0, "ast_findings_count": 3},
                  "tests": {"failed": 0}}
    con_error = {"compilation": {"success": True}, "metrics": {"ast_errors_count": 1}, "tests": {}}
    assert not veredicto(con_estilo) and veredicto(con_estilo, "exam")
    assert veredicto(con_error) and not veredicto(con_error, "relaxed")
    assert veredicto({"compilation": {"success": False}}, "relaxed")


def test_frecuentes_cuenta_alumnos_no_ocurrencias():
    h = {"codigo": "0x0003h", "mensaje": "m"}
    res = frecuentes({"a": [h, h, h], "b": [h], "c": [{"codigo": "0x1006h"}]})
    assert res[0] == {"codigo": "0x0003h", "alumnos": 2, "categoria": None, "mensaje": "m", "enlace": None}
