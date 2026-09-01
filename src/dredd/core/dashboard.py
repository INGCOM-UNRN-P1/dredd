"""Dashboard Web local liviano para visualización de calificaciones y auditoría en Dredd."""

from __future__ import annotations

from datetime import datetime
import http.server
import json
import os
from pathlib import Path
import re
import socketserver
import sys
from typing import Any, Callable, Dict, List, Optional


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
            })
            .catch(err => console.error("Error al cargar datos del dashboard:", err));
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


class ReusableTCPServer(socketserver.TCPServer):
    """TCPServer con SO_REUSEADDR activado para reiniciar sin esperar liberación del socket."""
    allow_reuse_address = True
    daemon_threads = True


def crear_handler_dashboard(
    data: Dict[str, Any],
    verbose: bool = False,
    logger_func: Optional[Callable[[str], None]] = None,
):
    """Crea una clase RequestHandler ligada al estado y configuración del dashboard."""
    class DashboardHTTPHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            elif self.path == "/api/data":
                payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            elif self.path in ("/health", "/api/health"):
                res = json.dumps({"status": "ok", "total_estudiantes": data.get("total", 0)}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(res)))
                self.end_headers()
                self.wfile.write(res)
            else:
                self.send_error(404, f"Ruta '{self.path}' no encontrada")

        def log_message(self, format: str, *args: Any) -> None:
            if not verbose:
                return
            hora = datetime.now().strftime("%H:%M:%S")
            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
            linea = f"[{hora}] [HTTP] {client_ip} - {format % args}"
            if logger_func:
                logger_func(linea)
            else:
                sys.stderr.write(linea + "\n")
                sys.stderr.flush()

    return DashboardHTTPHandler


def recolectar_datos_dashboard(
    entregas_dir: Optional[Path] = None,
    data_json: Optional[Path] = None,
) -> Dict[str, Any]:
    """Recolecta métricas de calificaciones y plagio desde archivos JSON o reportes de entregas."""
    if data_json and data_json.is_file():
        try:
            with open(data_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    estudiantes: List[Dict[str, Any]] = []
    if entregas_dir and entregas_dir.is_dir():
        for sub in sorted(entregas_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue

            nombre_alumno = sub.name.replace("_", " ").title()
            nota = 0.0
            plagio_pct = 0.0
            entrega_nombre = sub.name

            # Buscar reporte en Markdown
            reportes = list(sub.glob("*r*.md")) + list(sub.glob("*.md"))
            if reportes:
                reporte_mas_reciente = max(reportes, key=lambda p: p.stat().st_mtime)
                try:
                    contenido = reporte_mas_reciente.read_text(encoding="utf-8")
                    # Buscar nota
                    match_nota = re.search(r"[Nn]ota[:\s]+(\d+(?:\.\d+)?)", contenido)
                    if match_nota:
                        nota = float(match_nota.group(1))
                    else:
                        nota = 7.0

                    # Buscar plagio si fue registrado
                    match_plagio = re.search(r"[Pp]lagio[:\s]+(\d+(?:\.\d+)?)%", contenido)
                    if match_plagio:
                        plagio_pct = float(match_plagio.group(1))
                except Exception:
                    nota = 7.0
            else:
                nota = 0.0

            estudiantes.append({
                "id": sub.name,
                "nombre": nombre_alumno,
                "entrega": entrega_nombre,
                "nota": round(nota, 1),
                "plagio": round(plagio_pct, 1),
            })

    if not estudiantes:
        # Datos demostrativos iniciales cuando aún no hay entregas evaluadas
        estudiantes = [
            {"id": "1001", "nombre": "Alumno Demo 1", "entrega": "TP1 - Punteros", "nota": 8.5, "plagio": 12.0},
            {"id": "1002", "nombre": "Alumno Demo 2", "entrega": "TP1 - Punteros", "nota": 4.0, "plagio": 5.0},
            {"id": "1003", "nombre": "Alumno Demo 3", "entrega": "TP1 - Punteros", "nota": 2.0, "plagio": 85.0},
        ]

    total = len(estudiantes)
    promedio = sum(e["nota"] for e in estudiantes) / total if total > 0 else 0.0
    aprobados = sum(1 for e in estudiantes if e["nota"] >= 4.0)
    tasa_aprobacion = round((aprobados / total) * 100, 1) if total > 0 else 0.0
    alertas_plagio = sum(1 for e in estudiantes if e.get("plagio", 0) >= 50.0)

    return {
        "total": total,
        "promedio": round(promedio, 1),
        "aprobacion": tasa_aprobacion,
        "plagio_alertas": alertas_plagio,
        "estudiantes": estudiantes,
    }


def iniciar_dashboard(
    data: Dict[str, Any],
    port: int = 8000,
    host: str = "127.0.0.1",
    verbose: bool = False,
    logger_func: Optional[Callable[[str], None]] = None,
) -> ReusableTCPServer:
    """Instancia y enlaza el servidor HTTP sin bloquear la ejecución."""
    handler_class = crear_handler_dashboard(data=data, verbose=verbose, logger_func=logger_func)
    server = ReusableTCPServer((host, port), handler_class)
    return server


def servir_dashboard(
    data: Dict[str, Any],
    port: int = 8000,
    host: str = "127.0.0.1",
    verbose: bool = False,
    console: Any = None,
    entregas_path: Optional[Path] = None,
) -> None:
    """Inicia el servidor HTTP y mantiene la escucha activa hasta interrupción por usuario."""
    def _log_consola(msg: str) -> None:
        if console:
            console.print(f"[dim cyan]{msg}[/dim cyan]")
        else:
            sys.stderr.write(msg + "\n")
            sys.stderr.flush()

    try:
        server = iniciar_dashboard(
            data=data,
            port=port,
            host=host,
            verbose=verbose,
            logger_func=_log_consola if verbose else None,
        )
    except OSError as e:
        if console:
            console.print(f"[bold red]Error: No se pudo enlazar el servidor en {host}:{port}.[/bold red]")
            console.print(f"[red]{e}[/red]")
            console.print(f"[yellow]Probá indicando otro puerto: dredd serve-dashboard --port {port + 1}[/yellow]")
        else:
            sys.stderr.write(f"Error: No se pudo enlazar en {host}:{port}: {e}\n")
        raise

    url = f"http://localhost:{port}" if host in ("127.0.0.1", "0.0.0.0") else f"http://{host}:{port}"
    if console:
        console.print(f"[bold cyan]⚖️ Servidor de Dashboard Docente activo en:[/bold cyan] [bold green]{url}[/bold green]")
        if verbose:
            console.print(f"[dim]• Modo detallado (verbose) activo: registrando peticiones HTTP en vivo[/dim]")
            console.print(f"[dim]• Host/Puerto de escucha: {host}:{port}[/dim]")
            if entregas_path:
                console.print(f"[dim]• Directorio de entregas: {entregas_path.resolve()}[/dim]")
            console.print(f"[dim]• Entregas cargadas: {data.get('total', 0)} | Promedio: {data.get('promedio', 0.0)} | Aprobación: {data.get('aprobacion', 0)}%[/dim]")
            console.print(f"[dim]• Endpoints disponibles:[/dim]")
            console.print(f"  [cyan]GET {url}/[/cyan]          (Dashboard HTML interactivo)")
            console.print(f"  [cyan]GET {url}/api/data[/cyan]  (Datos JSON de calificaciones y plagio)")
            console.print(f"  [cyan]GET {url}/health[/cyan]    (Chequeo de estado del servicio)")
        console.print("[dim]Presioná Ctrl+C para detener el servidor.[/dim]\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if console:
            console.print("\n[bold yellow]Deteniendo servidor de dashboard docente...[/bold yellow]")
    finally:
        server.shutdown()
        server.server_close()
        if console:
            console.print("[bold green]✓ Servidor detenido correctamente.[/bold green]")
