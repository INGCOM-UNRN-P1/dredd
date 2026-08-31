"""Caché de evaluación y compilación por hash SHA-256 de archivos fuente en Dredd."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def calcular_hash_archivos(rutas: List[Path]) -> str:
    """Calcula un hash SHA-256 combinado de una lista de archivos fuente."""
    hasher = hashlib.sha256()
    for r in sorted(rutas):
        p = Path(r)
        if p.is_file():
            hasher.update(p.name.encode("utf-8"))
            hasher.update(p.read_bytes())
    return hasher.hexdigest()


class EvaluationCache:
    """Gestor de caché en disco para resultados de compilación y análisis."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (Path.home() / ".cache" / "dredd" / "eval_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _ruta_cache(self, hash_fuentes: str, herramienta: str) -> Path:
        return self.cache_dir / f"{hash_fuentes}_{herramienta}.json"

    def obtener(self, hash_fuentes: str, herramienta: str) -> Optional[Dict[str, Any]]:
        """Recupera el resultado cacheado si existe."""
        p = self._ruta_cache(hash_fuentes, herramienta)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def guardar(self, hash_fuentes: str, herramienta: str, resultado: Dict[str, Any]) -> None:
        """Guarda un resultado de evaluación en caché."""
        p = self._ruta_cache(hash_fuentes, herramienta)
        try:
            p.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def limpiar(self) -> int:
        """Elimina todos los archivos del caché."""
        count = 0
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
                count += 1
            except Exception:
                pass
        return count
