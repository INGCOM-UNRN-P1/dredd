"""Exportador de calificaciones de Dredd a formato SIU Guaraní (CSV estandarizado)."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def exportar_acta_guarani(
    estudiantes_data: List[Dict[str, Any]],
    output_path: Path,
    nota_aprobacion: float = 4.0,
    nota_promocion: float = 7.0,
) -> Path:
    """Genera un archivo CSV con las columnas estándar de actas de SIU Guaraní."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        # Cabecera estándar SIU Guaraní
        writer.writerow(["Legajo", "Apellido y Nombre", "Documento", "Nota", "Condicion", "Fecha", "Observaciones"])

        fecha_str = datetime.now().strftime("%d/%m/%Y")
        for est in estudiantes_data:
            legajo = est.get("legajo", est.get("id", "00000"))
            nombre = est.get("nombre", "Estudiante")
            dni = est.get("dni", "")
            nota = float(est.get("nota", 0.0))

            if nota >= nota_promocion:
                condicion = "Promocionado"
            elif nota >= nota_aprobacion:
                condicion = "Aprobado"
            elif nota > 0:
                condicion = "Desaprobado"
            else:
                condicion = "Ausente"

            obs = est.get("observaciones", "")
            writer.writerow([legajo, nombre, dni, f"{nota:.1f}", condicion, fecha_str, obs])

    return output_path
