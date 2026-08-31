"""Empaquetador y despachador de devoluciones pedagógicas individuales en Dredd."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table


def empaquetar_devoluciones_batch(
    entregas_dir: Path,
    output_dir: Path,
    crear_zip: bool = True,
    console: Optional[Console] = None,
) -> Dict[str, Any]:
    """Recopila todos los informes de retroalimentación individuales y los empaqueta."""
    cons = console or Console()
    entregas = Path(entregas_dir).resolve()
    dest = Path(output_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    informes_encontrados: List[Path] = []
    for p in entregas.rglob("informe_*.md"):
        informes_encontrados.append(p)
    for p in entregas.rglob("*_r*.md"):
        if p not in informes_encontrados:
            informes_encontrados.append(p)

    for inf in informes_encontrados:
        target_file = dest / inf.name
        shutil.copy2(inf, target_file)

    zip_path = None
    if crear_zip and informes_encontrados:
        zip_path = dest.parent / f"{dest.name}_feedbacks.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for inf in dest.glob("*.md"):
                zf.write(inf, arcname=inf.name)

    tabla = Table(title="📦 Lote de Devoluciones y Feedbacks Generados", border_style="cyan")
    tabla.add_column("Informes Recopilados", justify="center")
    tabla.add_column("Directorio de Salida", style="cyan")
    tabla.add_column("Archivo ZIP", style="green")

    zip_str = str(zip_path.name) if zip_path else "[dim]No generado[/dim]"
    tabla.add_row(str(len(informes_encontrados)), str(dest), zip_str)
    cons.print(tabla)

    return {
        "total_informes": len(informes_encontrados),
        "directorio": dest,
        "zip": zip_path,
    }
