"""Comparador de desempeño y benchmarking algorítmico de toda la cohorte de estudiantes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import resource
import subprocess
import time
from typing import Dict, List, Optional


@dataclass
class MetricasAlumno:
    estudiante: str
    tiempo_ms: float
    memoria_rss_kb: int
    exit_code: int
    ok: bool

    def to_dict(self) -> dict:
        return {
            "estudiante": self.estudiante,
            "tiempo_ms": round(self.tiempo_ms, 2),
            "memoria_rss_kb": self.memoria_rss_kb,
            "exit_code": self.exit_code,
            "ok": self.ok,
        }


@dataclass
class CohorteBenchReport:
    total_evaluados: int
    alumnos_exitosos: int
    tiempo_promedio_ms: float
    tiempo_mediana_ms: float
    memoria_promedio_kb: float
    ranking: List[MetricasAlumno]

    def to_dict(self) -> dict:
        return {
            "total_evaluados": self.total_evaluados,
            "alumnos_exitosos": self.alumnos_exitosos,
            "tiempo_promedio_ms": round(self.tiempo_promedio_ms, 2),
            "tiempo_mediana_ms": round(self.tiempo_mediana_ms, 2),
            "memoria_promedio_kb": round(self.memoria_promedio_kb, 2),
            "ranking": [m.to_dict() for m in self.ranking],
        }


def medir_ejecucion_individual(
    binario: Path,
    input_data: str = "",
    timeout_seg: float = 5.0,
    cwd: Optional[Path] = None,
) -> MetricasAlumno:
    """Mide tiempo de reloj y memoria RSS máxima consumida por un binario."""
    estudiante_nom = binario.parent.name
    if not binario.is_file():
        return MetricasAlumno(estudiante=estudiante_nom, tiempo_ms=0.0, memoria_rss_kb=0, exit_code=-1, ok=False)

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(binario.resolve())],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout_seg,
            cwd=str(cwd.resolve()) if cwd else str(binario.parent.resolve()),
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        # Obtener uso de recursos aproximado
        rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
        rss_kb = rusage.ru_maxrss

        return MetricasAlumno(
            estudiante=estudiante_nom,
            tiempo_ms=dt_ms,
            memoria_rss_kb=rss_kb,
            exit_code=proc.returncode,
            ok=(proc.returncode == 0),
        )
    except subprocess.TimeoutExpired:
        return MetricasAlumno(
            estudiante=estudiante_nom,
            tiempo_ms=timeout_seg * 1000.0,
            memoria_rss_kb=0,
            exit_code=-1,
            ok=False,
        )
    except Exception:
        return MetricasAlumno(
            estudiante=estudiante_nom,
            tiempo_ms=0.0,
            memoria_rss_kb=0,
            exit_code=-2,
            ok=False,
        )


def comparar_desempeno_cohorte(
    directorio_entregas: Path,
    nombre_binario: str = "main",
    input_data: str = "",
    timeout_seg: float = 5.0,
) -> CohorteBenchReport:
    """Ejecuta benchmarking comparativo sobre todas las entregas que contengan el binario."""
    dir_base = Path(directorio_entregas)
    candidatos_bin = sorted(list(dir_base.glob(f"*/{nombre_binario}")) + list(dir_base.glob(f"*/*/{nombre_binario}")))

    metricas: List[MetricasAlumno] = []
    for b in candidatos_bin:
        m = medir_ejecucion_individual(b, input_data=input_data, timeout_seg=timeout_seg)
        metricas.append(m)

    # Ordenar ranking por éxito, luego menor tiempo, luego menor memoria
    metricas.sort(key=lambda x: (not x.ok, x.tiempo_ms, x.memoria_rss_kb))

    exitosos = [m for m in metricas if m.ok]
    cant_exitosos = len(exitosos)

    if exitosos:
        tiempos = [m.tiempo_ms for m in exitosos]
        mems = [m.memoria_rss_kb for m in exitosos]
        prom_t = sum(tiempos) / len(tiempos)
        tiempos_sorted = sorted(tiempos)
        med_t = tiempos_sorted[len(tiempos_sorted) // 2]
        prom_m = sum(mems) / len(mems)
    else:
        prom_t = 0.0
        med_t = 0.0
        prom_m = 0.0

    return CohorteBenchReport(
        total_evaluados=len(metricas),
        alumnos_exitosos=cant_exitosos,
        tiempo_promedio_ms=prom_t,
        tiempo_mediana_ms=med_t,
        memoria_promedio_kb=prom_m,
        ranking=metricas,
    )
