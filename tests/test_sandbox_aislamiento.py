"""El sandbox de dredd no debe exponer archivos fuera del workspace (N-DREDD-02).

Antes, el fallback sin nostromo y el «Sandbox Blindado» montaban `/` completo
en solo lectura: una entrega podía leer soluciones canónicas, entregas de
otros estudiantes o claves del docente.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from dredd.core import sandbox
from dredd.core.sandbox import (
    ENV_PERMITIR_SIN_SANDBOX,
    MENSAJE_SIN_SANDBOX,
    execute_sandboxed,
    execute_shielded_sandbox,
)

LECTOR_C = r"""
#include <stdio.h>
int main(int argc, char *argv[])
{
    FILE *f = fopen(argv[1], "r");
    if (f == NULL)
    {
        puts("BLOQUEADO");
        return 0;
    }
    char linea[64] = {0};
    fgets(linea, sizeof linea, f);
    printf("LEIDO:%s", linea);
    fclose(f);
    return 0;
}
"""


def _bwrap_funcional(requerir_red_aislada: bool) -> bool:
    bwrap = shutil.which("bwrap")
    return bool(bwrap) and sandbox._flags_aislamiento(bwrap, requerir_red_aislada) is not None


@pytest.fixture
def escenario(tmp_path: Path):
    """Workspace con el binario lector y un secreto fuera del workspace."""
    if not shutil.which("gcc"):
        pytest.skip("requiere gcc")
    workspace = tmp_path / "entrega"
    workspace.mkdir()
    fuente = workspace / "lector.c"
    fuente.write_text(LECTOR_C)
    binario = workspace / "lector"
    subprocess.run(["gcc", "-o", str(binario), str(fuente)], check=True)
    (workspace / "propio.txt").write_text("dato del workspace\n")
    secreto = tmp_path / "docente" / "solucion_canonica.c"
    secreto.parent.mkdir()
    secreto.write_text("SECRETO\n")
    return workspace, binario, secreto


@pytest.fixture
def sin_nostromo(monkeypatch):
    """Fuerza la ruta propia de dredd (la que antes montaba `/`)."""
    monkeypatch.setattr(sandbox, "_try_import_nostromo", lambda: None)
    monkeypatch.delenv(ENV_PERMITIR_SIN_SANDBOX, raising=False)


@pytest.mark.skipif(not _bwrap_funcional(False), reason="requiere bubblewrap funcional")
def test_sandbox_no_lee_fuera_del_workspace(escenario, sin_nostromo):
    workspace, binario, secreto = escenario
    ret, out, err, _ = execute_sandboxed([str(binario), str(secreto)], workspace=workspace)
    assert ret == 0, err
    assert "SECRETO" not in out
    assert "BLOQUEADO" in out


@pytest.mark.skipif(not _bwrap_funcional(False), reason="requiere bubblewrap funcional")
def test_sandbox_si_lee_el_workspace(escenario, sin_nostromo):
    workspace, binario, _ = escenario
    ret, out, err, _ = execute_sandboxed(["./lector", "propio.txt"], workspace=workspace)
    assert ret == 0, err
    assert "LEIDO:dato del workspace" in out


@pytest.mark.skipif(not _bwrap_funcional(True), reason="requiere bubblewrap con red aislable")
def test_sandbox_blindado_no_lee_fuera_del_workspace(escenario, sin_nostromo):
    workspace, binario, secreto = escenario
    ret, out, err, _ = execute_shielded_sandbox([str(binario), str(secreto)], workspace=workspace)
    assert ret == 0, err
    assert "SECRETO" not in out
    assert "BLOQUEADO" in out


def test_sin_sandbox_no_ejecuta_salvo_autorizacion(escenario, sin_nostromo, monkeypatch):
    workspace, binario, secreto = escenario
    monkeypatch.setattr(sandbox.shutil, "which", lambda _nombre: None)

    for ejecutar in (execute_sandboxed, execute_shielded_sandbox):
        ret, out, err, _ = ejecutar([str(binario), str(secreto)], workspace=workspace)
        assert ret == -1
        assert out == ""
        assert err == MENSAJE_SIN_SANDBOX

    monkeypatch.setenv(ENV_PERMITIR_SIN_SANDBOX, "1")
    ret, out, _, _ = execute_sandboxed([str(binario), str(workspace / "propio.txt")], workspace=workspace)
    assert ret == 0
    assert "LEIDO:dato del workspace" in out


def test_comando_bwrap_no_monta_la_raiz(tmp_path: Path):
    binario = tmp_path / "prog"
    binario.write_text("")
    cmd = sandbox._comando_bwrap("bwrap", [str(binario)], str(tmp_path), ["--unshare-all"])
    pares = list(zip(cmd, cmd[1:], cmd[2:]))
    assert ("--ro-bind", "/", "/") not in pares
    assert ("--bind", "/", "/") not in pares
    # el workspace se monta después de --tmpfs /tmp para no quedar oculto
    assert cmd.index("--tmpfs") < cmd.index("--bind")
