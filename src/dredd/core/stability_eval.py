"""Evaluador de estabilidad temporal y determinismo de ejecutables C mediante corridas reiteradas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List, Optional, Set


@dataclass
class ResultadoEstabilidad:
    ejecutable: str
    estable: bool
    total_corridas: int
    salidas_distintas: int
    codigos_retorno: List[int]
    duraciones_ms: List[float]
    detalle: str

    def to_dict(self) -> dict:
        return {
            "ejecutable": self.ejecutable,
            "estable": self.estable,
            "total_corridas": self.total_corridas,
            "salidas_distintas": self.salidas_distintas,
            "codigos_retorno": self.codigos_retorno,
            "duraciones_ms": [round(d, 2) for d in self.duraciones_ms],
            "detalle": self.detalle,
        }


def evaluar_estabilidad_binario(
    ruta_binario: Path,
    input_data: str = "",
    repeticiones: int = 5,
    timeout_seg: float = 3.0,
    cwd: Optional[Path] = None,
) -> ResultadoEstabilidad:
    """Ejecuta el binario N veces bajo idéntico payload para evaluar determinismo de salida y retorno."""
    bin_path = Path(ruta_binario)
    if not bin_path.is_file():
        return ResultadoEstabilidad(
            ejecutable=bin_path.name,
            estable=False,
            total_corridas=0,
            salidas_distintas=0,
            codigos_retorno=[],
            duraciones_ms=[],
            detalle=f"El ejecutable '{bin_path}' no existe.",
        )

    import time
    salidas: List[str] = []
    codigos: List[int] = []
    duraciones: List[float] = []

    for _ in range(repeticiones):
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(bin_path.resolve())],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout_seg,
                cwd=str(cwd.resolve()) if cwd else None,
            )
            dt = (time.perf_counter() - t0) * 1000.0
            salidas.append(proc.stdout)
            codigos.append(proc.returncode)
            duraciones.append(dt)
        except subprocess.TimeoutExpired:
            salidas.append("[TIMEOUT]")
            codigos.append(-1)
            duraciones.append(timeout_seg * 1000.0)
        except Exception as e:
            salidas.append(f"[ERROR: {e}]")
            codigos.append(-2)
            duraciones.append(0.0)

    conjunto_salidas = set(salidas)
    conjunto_codigos = set(codigos)
    cant_distintas = len(conjunto_salidas)

    es_estable = (cant_distintas == 1) and (len(conjunto_codigos) == 1)

    if es_estable:
        detalle = f"Comportamiento 100% determinista y reproducible a lo largo de {repeticiones} ejecuciones."
    else:
        detalle = (
            f"Inestabilidad temporal detectada: se registraron {cant_distintas} salidas distintas y "
            f"códigos de salida variantes {list(conjunto_codigos)}. Posible uso de memoria no inicializada o semillas aleatorias."
        )

    return ResultadoEstabilidad(
        ejecutable=bin_path.name,
        estable=es_estable,
        total_corridas=repeticiones,
        salidas_distintas=cant_distintas,
        codigos_retorno=codigos,
        duraciones_ms=duraciones,
        detalle=detalle,
    )
