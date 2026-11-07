"""Pruebas de la capa de almacenamiento (app/repositorios.py).

* Las pruebas de "contrato" se ejecutan contra AMBOS repositorios: si un
  repositorio cumple el contrato, la lógica de negocio funciona igual con él.
  La variante PostgreSQL solo corre si existe la variable TEST_DATABASE_URL;
  si no, se omite (skip) y el resto de las pruebas sigue funcionando.
* Las pruebas de ``crear_repositorio`` verifican el respaldo en memoria
  cuando no hay base de datos, sin necesitar una base de datos real.
"""

import logging
import os
from datetime import date

import pytest

from app.habitos import ContadorHabitos
from app.repositorios import RepositorioMemoria, RepositorioPostgres, crear_repositorio

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
URL_SIN_SERVIDOR = "postgresql://usuario:clave@127.0.0.1:1/inexistente"

DIA_1 = date(2026, 11, 6)
DIA_2 = date(2026, 11, 7)


@pytest.fixture(params=["memoria", "postgres"])
def repositorio(request):
    if request.param == "memoria":
        yield RepositorioMemoria()
        return
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL no definida: se omiten las pruebas con PostgreSQL")
    repo = RepositorioPostgres(TEST_DATABASE_URL)
    repo.borrar_todo()
    yield repo
    repo.borrar_todo()


# ---------------------------------------------------------------- contrato

def test_repositorio_nuevo_esta_vacio(repositorio):
    assert repositorio.listar() == []


def test_agregar_asigna_id_y_se_puede_obtener(repositorio):
    # Act
    creado = repositorio.agregar("Leer")
    # Assert
    obtenido = repositorio.obtener(creado.id)
    assert obtenido.nombre == "Leer"
    assert obtenido.fechas_completadas == set()


def test_listar_devuelve_en_orden_de_creacion(repositorio):
    repositorio.agregar("Leer")
    repositorio.agregar("Correr")
    assert [h.nombre for h in repositorio.listar()] == ["Leer", "Correr"]


def test_obtener_inexistente_devuelve_none(repositorio):
    assert repositorio.obtener(999) is None


def test_registrar_fecha_guarda_las_fechas(repositorio):
    habito = repositorio.agregar("Leer")
    repositorio.registrar_fecha(habito.id, DIA_1)
    repositorio.registrar_fecha(habito.id, DIA_2)
    assert repositorio.obtener(habito.id).fechas_completadas == {DIA_1, DIA_2}


def test_eliminar_quita_el_habito_y_sus_fechas(repositorio):
    leer = repositorio.agregar("Leer")
    correr = repositorio.agregar("Correr")
    repositorio.registrar_fecha(leer.id, DIA_1)

    repositorio.eliminar(leer.id)

    assert [h.id for h in repositorio.listar()] == [correr.id]
    assert repositorio.obtener(leer.id) is None


def test_contador_funciona_con_el_repositorio(repositorio):
    contador = ContadorHabitos(reloj=lambda: DIA_2, repositorio=repositorio)
    habito = contador.agregar_habito("Meditar")
    marcado = contador.marcar_habito(habito["id"])
    assert marcado["racha"] == 1
    assert contador.almacenamiento == repositorio.nombre


# ---------------------------------------------------------------- crear_repositorio

def test_sin_database_url_usa_memoria(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    repositorio = crear_repositorio()
    assert isinstance(repositorio, RepositorioMemoria)


def test_database_url_vacia_usa_memoria():
    assert isinstance(crear_repositorio(""), RepositorioMemoria)


def test_base_de_datos_no_disponible_usa_memoria_y_avisa(caplog):
    with caplog.at_level(logging.WARNING):
        repositorio = crear_repositorio(URL_SIN_SERVIDOR)
    assert isinstance(repositorio, RepositorioMemoria)
    assert "se usará almacenamiento en memoria" in caplog.text


def test_lee_database_url_del_entorno(monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", URL_SIN_SERVIDOR)
    with caplog.at_level(logging.WARNING):
        repositorio = crear_repositorio()
    assert isinstance(repositorio, RepositorioMemoria)
    assert "No se pudo conectar" in caplog.text


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="requiere TEST_DATABASE_URL")
def test_base_de_datos_disponible_usa_postgres():
    assert isinstance(crear_repositorio(TEST_DATABASE_URL), RepositorioPostgres)
