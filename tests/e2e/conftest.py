"""Fixture que levanta la aplicación real (uvicorn) para la prueba de aceptación."""

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def url_app():
    """Paso 1 del flujo: inicia la aplicación y espera a que responda."""
    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(puerto)],
        cwd=RAIZ_PROYECTO,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{puerto}"
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{url}/api/habitos", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail("La aplicación no arrancó a tiempo")
        yield url
    finally:
        proceso.terminate()
        proceso.wait(timeout=5)
