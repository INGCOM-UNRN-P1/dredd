"""Detector de entregas fuera de término con cálculo de penalización gradual configurable."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Optional


@dataclass
class InfoPenalizacion:
    a_tiempo: bool
    fecha_entrega: datetime
    fecha_limite: datetime
    minutos_retraso: float
    horas_retraso: float
    puntos_descuento: float
    nota_original: float
    nota_final: float
    detalle: str

    def to_dict(self) -> dict:
        return {
            "a_tiempo": self.a_tiempo,
            "fecha_entrega": self.fecha_entrega.isoformat(),
            "fecha_limite": self.fecha_limite.isoformat(),
            "minutos_retraso": round(self.minutos_retraso, 2),
            "horas_retraso": round(self.horas_retraso, 2),
            "puntos_descuento": round(self.puntos_descuento, 2),
            "nota_original": round(self.nota_original, 2),
            "nota_final": round(self.nota_final, 2),
            "detalle": self.detalle,
        }


def calcular_penalizacion_entrega(
    fecha_entrega: datetime,
    fecha_limite: datetime,
    nota_original: float = 10.0,
    gracia_minutos: int = 15,
    puntos_por_hora: float = 0.25,
    max_descuento: float = 4.0,
) -> InfoPenalizacion:
    """Calcula el descuento gradual aplicable sobre la calificación según retraso temporal."""
    # Asegurar timezones compatibles
    if fecha_entrega.tzinfo is None and fecha_limite.tzinfo is not None:
        fecha_entrega = fecha_entrega.replace(tzinfo=timezone.utc)
    elif fecha_entrega.tzinfo is not None and fecha_limite.tzinfo is None:
        fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)

    delta_segundos = (fecha_entrega - fecha_limite).total_seconds()
    minutos_totales = max(0.0, delta_segundos / 60.0)

    if minutos_totales <= gracia_minutos:
        return InfoPenalizacion(
            a_tiempo=True,
            fecha_entrega=fecha_entrega,
            fecha_limite=fecha_limite,
            minutos_retraso=0.0,
            horas_retraso=0.0,
            puntos_descuento=0.0,
            nota_original=nota_original,
            nota_final=nota_original,
            detalle="Entrega a término (dentro del plazo o período de gracia).",
        )

    # Retraso efectivo descontando gracia
    retraso_efectivo_minutos = minutos_totales - gracia_minutos
    horas_retraso = retraso_efectivo_minutos / 60.0

    # Descuento lineal proporcional con tope
    descuento = min(max_descuento, horas_retraso * puntos_por_hora)
    descuento = round(descuento, 2)
    nota_final = max(0.0, round(nota_original - descuento, 2))

    dias = math.floor(horas_retraso / 24.0)
    horas_resto = math.floor(horas_retraso % 24.0)
    mins_resto = int(retraso_efectivo_minutos % 60)

    tiempo_txt = f"{mins_resto}m"
    if horas_resto > 0 or dias > 0:
        tiempo_txt = f"{horas_resto}h {tiempo_txt}"
    if dias > 0:
        tiempo_txt = f"{dias}d {tiempo_txt}"

    detalle = (
        f"Entrega fuera de término por {tiempo_txt}. "
        f"Descuento aplicado: -{descuento} pts (Tasa: {puntos_por_hora} pts/h, Tope: {max_descuento} pts)."
    )

    return InfoPenalizacion(
        a_tiempo=False,
        fecha_entrega=fecha_entrega,
        fecha_limite=fecha_limite,
        minutos_retraso=minutos_totales,
        horas_retraso=horas_retraso,
        puntos_descuento=descuento,
        nota_original=nota_original,
        nota_final=nota_final,
        detalle=detalle,
    )
