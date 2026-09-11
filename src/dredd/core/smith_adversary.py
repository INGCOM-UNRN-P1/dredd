"""Generador y ejecutor de pruebas adversarias y de estrés en lote (integración smith)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Dict, List, Optional


@dataclass
class CasoAdversario:
    nombre: str
    categoria: str
    payload: str
    descripcion: str


CASOS_ADVERSARIOS_ESTANDAR: List[CasoAdversario] = [
    CasoAdversario(
        nombre="adv_int_overflow",
        categoria="enteros",
        payload="2147483647\n-2147483648\n0\n",
        descripcion="Valores extremos de INT_MAX, INT_MIN y cero.",
    ),
    CasoAdversario(
        nombre="adv_negative_bounds",
        categoria="enteros",
        payload="-1\n-999999\n",
        descripcion="Entradas negativas donde se esperan dimensiones o índices positivos.",
    ),
    CasoAdversario(
        nombre="adv_format_string",
        categoria="seguridad",
        payload="%s%s%s%x%n%d\n",
        descripcion="Secuencia de especificadores de formato printf para auditoría de inyección.",
    ),
    CasoAdversario(
        nombre="adv_empty_input",
        categoria="borde",
        payload="",
        descripcion="Entrada vacía inmediata (EOF súbito).",
    ),
    CasoAdversario(
        nombre="adv_whitespace_burst",
        categoria="borde",
        payload="   \t\t\n   \n\r\n\t  \n",
        descripcion="Ráfagas de espacios en blanco, tabulaciones y saltos de línea.",
    ),
    CasoAdversario(
        nombre="adv_long_buffer",
        categoria="desborde",
        payload=("A" * 4096) + "\n",
        descripcion="Cadena continua de 4096 bytes sin espacios para estresar búferes scanf/gets.",
    ),
]


@dataclass
class ReporteAdversario:
    estudiante: str
    total_casos: int
    casos_superados: int
    crashes: int
    detalles: List[Dict[str, str]]

    def to_dict(self) -> dict:
        return {
            "estudiante": self.estudiante,
            "total_casos": self.total_casos,
            "casos_superados": self.casos_superados,
            "crashes": self.crashes,
            "detalles": self.detalles,
        }


def inyectar_casos_adversarios(directorio_tests: Path) -> List[Path]:
    """Escribe los casos de prueba adversarios en la carpeta tests/ indicada."""
    directorio_tests.mkdir(parents=True, exist_ok=True)
    rutas = []
    for caso in CASOS_ADVERSARIOS_ESTANDAR:
        f_in = directorio_tests / f"{caso.nombre}.in"
        f_in.write_text(caso.payload, encoding="utf-8")
        rutas.append(f_in)
    return rutas


def evaluar_con_casos_adversarios(
    binario: Path,
    timeout_seg: float = 2.0,
) -> ReporteAdversario:
    """Ejecuta todos los casos adversarios contra un binario compilado y detecta caídas (SIGSEGV/SIGABRT)."""
    estudiante = binario.parent.name
    total = len(CASOS_ADVERSARIOS_ESTANDAR)
    superados = 0
    crashes = 0
    detalles: List[Dict[str, str]] = []

    for c in CASOS_ADVERSARIOS_ESTANDAR:
        try:
            proc = subprocess.run(
                [str(binario.resolve())],
                input=c.payload,
                capture_output=True,
                text=True,
                timeout=timeout_seg,
                cwd=str(binario.parent.resolve()),
            )
            # Código < 0 indica terminación por señal (ej. -11 SIGSEGV, -6 SIGABRT)
            if proc.returncode < 0 or proc.returncode in (134, 139):
                crashes += 1
                detalles.append({
                    "caso": c.nombre,
                    "estado": "CRASH",
                    "codigo": str(proc.returncode),
                    "mensaje": f"Crash ante entrada adversaria: {c.descripcion}",
                })
            else:
                superados += 1
                detalles.append({
                    "caso": c.nombre,
                    "estado": "OK",
                    "codigo": str(proc.returncode),
                    "mensaje": "Manejó la entrada sin colapsar.",
                })
        except subprocess.TimeoutExpired:
            crashes += 1
            detalles.append({
                "caso": c.nombre,
                "estado": "TIMEOUT",
                "codigo": "-1",
                "mensaje": f"Bucle infinito ante entrada: {c.descripcion}",
            })
        except Exception as e:
            crashes += 1
            detalles.append({
                "caso": c.nombre,
                "estado": "ERROR",
                "codigo": "-2",
                "mensaje": str(e),
            })

    return ReporteAdversario(
        estudiante=estudiante,
        total_casos=total,
        casos_superados=superados,
        crashes=crashes,
        detalles=detalles,
    )
