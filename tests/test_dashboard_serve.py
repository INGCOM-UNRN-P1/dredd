"""Tests unitarios e integrales para dredd serve-dashboard y dredd dashboard."""

import json
from pathlib import Path
import threading
import time
import urllib.request
import pytest
from typer.testing import CliRunner

from dredd.cli import app
from dredd.core.dashboard import (
    recolectar_datos_dashboard,
    iniciar_dashboard,
    DashboardDataServer,
    DASHBOARD_HTML,
)

runner = CliRunner()


def test_recolectar_datos_dashboard_defaults(tmp_path: Path):
    datos = recolectar_datos_dashboard(entregas_dir=tmp_path / "vacio")
    assert datos["total"] >= 1
    assert "promedio" in datos
    assert "aprobacion" in datos
    assert "plagio_alertas" in datos
    assert isinstance(datos["estudiantes"], list)


def test_recolectar_datos_dashboard_con_entregas(tmp_path: Path):
    entregas = tmp_path / "entregas"
    entregas.mkdir()

    # Alumno 1: Aprobado
    a1 = entregas / "juan_perez"
    a1.mkdir()
    (a1 / "alumno_r1.md").write_text("# Informe\nNota: 8.5\nPlagio: 10%\n", encoding="utf-8")

    # Alumno 2: Desaprobado con alerta de plagio
    a2 = entregas / "maria_gomez"
    a2.mkdir()
    (a2 / "alumno_r1.md").write_text("# Informe\nNota: 3.0\nPlagio: 75%\n", encoding="utf-8")

    datos = recolectar_datos_dashboard(entregas_dir=entregas)
    assert datos["total"] == 2
    assert datos["promedio"] == 5.8
    assert datos["aprobacion"] == 50.0
    assert datos["plagio_alertas"] == 1
    assert any(e["nombre"] == "Juan Perez" and e["nota"] == 8.5 for e in datos["estudiantes"])
    assert any(e["nombre"] == "Maria Gomez" and e["plagio"] == 75.0 for e in datos["estudiantes"])


def test_servidor_http_endpoints_y_verbose():
    datos_test = {
        "total": 1,
        "promedio": 10.0,
        "aprobacion": 100.0,
        "plagio_alertas": 0,
        "estudiantes": [{"id": "1", "nombre": "Test", "entrega": "TP1", "nota": 10.0, "plagio": 0.0}],
    }
    logs_capturados = []
    server = iniciar_dashboard(
        data=datos_test,
        port=8991,
        verbose=True,
        logger_func=lambda msg: logs_capturados.append(msg),
    )
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    # Bypass cualquier proxy local para pruebas en loopback
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)

    try:
        # 1. Endpoint principal /
        req_root = urllib.request.Request("http://127.0.0.1:8991/")
        with opener.open(req_root) as resp:
            assert resp.status == 200
            contenido = resp.read().decode("utf-8")
            assert "Dredd - Tablero Docente" in contenido

        # 2. Endpoint de datos /api/data
        req_data = urllib.request.Request("http://127.0.0.1:8991/api/data")
        with opener.open(req_data) as resp:
            assert resp.status == 200
            api_data = json.loads(resp.read().decode("utf-8"))
            assert api_data["total"] == 1
            assert api_data["promedio"] == 10.0

        # 3. Endpoint de salud /health
        req_health = urllib.request.Request("http://127.0.0.1:8991/health")
        with opener.open(req_health) as resp:
            assert resp.status == 200
            health_data = json.loads(resp.read().decode("utf-8"))
            assert health_data["status"] == "ok"
    finally:
        server.shutdown()
        server.server_close()

    # Verificar que el modo verbose registró las peticiones
    assert len(logs_capturados) >= 3
    assert any("GET / " in l or "GET / HTTP" in l for l in logs_capturados)
    assert any("/api/data" in l for l in logs_capturados)


def test_cli_dashboard_help():
    res1 = runner.invoke(app, ["serve-dashboard", "--help"])
    assert res1.exit_code == 0
    assert "--port" in res1.stdout
    assert "--verbose" in res1.stdout
    assert "--entregas" in res1.stdout

    res2 = runner.invoke(app, ["dashboard", "--help"])
    assert res2.exit_code == 0
    assert "--verbose" in res2.stdout
