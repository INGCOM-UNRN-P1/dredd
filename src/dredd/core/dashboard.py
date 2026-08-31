"""Dashboard Web local liviano para visualización de calificaciones y auditoría en Dredd."""

from __future__ import annotations

import json
import http.server
import socketserver
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dredd Dashboard - Calificaciones y Auditoría Docente</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }
        h1, h2 { color: #38bdf8; }
        .card { background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 24px; border: 1px solid #334155; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-box { background: #334155; border-radius: 6px; padding: 16px; text-align: center; }
        .stat-val { font-size: 28px; font-weight: bold; color: #4ade80; }
        .stat-lbl { color: #94a3b8; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid #334155; }
        th { background: #0f172a; color: #38bdf8; }
        tr:hover { background: #334155; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-pass { background: #166534; color: #4ade80; }
        .badge-fail { background: #991b1b; color: #f87171; }
    </style>
</head>
<body>
    <h1>⚖️ Dredd - Tablero Docente en Tiempo Real</h1>
    <div class="grid">
        <div class="stat-box"><div class="stat-val" id="total-entregas">0</div><div class="stat-lbl">Entregas Evaluadas</div></div>
        <div class="stat-box"><div class="stat-val" id="promedio-nota">0.0</div><div class="stat-lbl">Promedio General</div></div>
        <div class="stat-box"><div class="stat-val" id="tasa-aprobacion">0%</div><div class="stat-lbl">Tasa de Aprobación</div></div>
        <div class="stat-box"><div class="stat-val" id="alertas-plagio">0</div><div class="stat-lbl">Alertas de Plagio</div></div>
    </div>
    <div class="card">
        <h2>Listado de Estudiantes y Calificaciones</h2>
        <table id="tabla-estudiantes">
            <thead>
                <tr>
                    <th>Estudiante</th>
                    <th>Entrega</th>
                    <th>Nota Final</th>
                    <th>Estado</th>
                    <th>Plagio Máx</th>
                </tr>
            </thead>
            <tbody>
            </tbody>
        </table>
    </div>
    <script>
        fetch('/api/data')
            .then(r => r.json())
            .then(d => {
                document.getElementById('total-entregas').innerText = d.total || 0;
                document.getElementById('promedio-nota').innerText = (d.promedio || 0).toFixed(1);
                document.getElementById('tasa-aprobacion').innerText = (d.aprobacion || 0) + '%';
                document.getElementById('alertas-plagio').innerText = d.plagio_alertas || 0;
                const tb = document.querySelector('#tabla-estudiantes tbody');
                tb.innerHTML = '';
                (d.estudiantes || []).forEach(e => {
                    const tr = document.createElement('tr');
                    const bClass = e.nota >= 4.0 ? 'badge-pass' : 'badge-fail';
                    const bTxt = e.nota >= 4.0 ? 'APROBADO' : 'DESAPROBADO';
                    tr.innerHTML = `<td><b>${e.nombre}</b></td><td>${e.entrega}</td><td><b>${e.nota}</b></td><td><span class="badge ${bClass}">${bTxt}</span></td><td>${e.plagio}%</td>`;
                    tb.appendChild(tr);
                });
            });
    </script>
</body>
</html>
"""


class DashboardDataServer:
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self.data = data or {
            "total": 0,
            "promedio": 0.0,
            "aprobacion": 0,
            "plagio_alertas": 0,
            "estudiantes": [],
        }

    def generar_html(self) -> str:
        return DASHBOARD_HTML


def iniciar_dashboard(
    data: Dict[str, Any],
    port: int = 8000,
    host: str = "127.0.0.1",
) -> Any:
    """Inicia un servidor HTTP local para servir el dashboard."""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            elif self.path == "/api/data":
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            else:
                self.send_error(404, "Not Found")

        def log_message(self, format, *args):
            pass  # Silenciar logs

    server = socketserver.TCPServer((host, port), Handler)
    return server
