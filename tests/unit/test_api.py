"""Pruebas de los endpoints HTTP (app/main.py) usando el TestClient de FastAPI.

Cada prueba recibe un ContadorHabitos nuevo (inyectado con dependency_overrides),
de modo que las pruebas quedan aisladas entre sí y no comparten estado.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.habitos import ContadorHabitos
from app.main import app, get_contador


@pytest.fixture
def contador():
    return ContadorHabitos(reloj=lambda: date(2026, 11, 7))


@pytest.fixture
def cliente(contador):
    app.dependency_overrides[get_contador] = lambda: contador
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_index_sirve_la_pagina_html(cliente):
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "Contador de Hábitos" in respuesta.text


def test_get_contador_devuelve_la_instancia_global():
    assert isinstance(get_contador(), ContadorHabitos)
    assert get_contador() is get_contador()


# ---------------------------------------------------------------- GET /api/habitos

def test_listar_habitos_vacio(cliente):
    respuesta = cliente.get("/api/habitos")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_listar_habitos_con_datos(cliente, contador):
    # Arrange
    contador.agregar_habito("Leer")
    # Act
    respuesta = cliente.get("/api/habitos")
    # Assert
    assert [h["nombre"] for h in respuesta.json()] == ["Leer"]


# ---------------------------------------------------------------- POST /api/habitos

def test_agregar_habito_responde_201_y_lo_guarda(cliente, contador):
    respuesta = cliente.post("/api/habitos", json={"nombre": "Tomar agua"})
    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "Tomar agua"
    assert len(contador.listar_habitos()) == 1


def test_agregar_habito_invalido_responde_400(cliente):
    respuesta = cliente.post("/api/habitos", json={"nombre": "   "})
    assert respuesta.status_code == 400
    assert "vacío" in respuesta.json()["detail"]


def test_agregar_habito_sin_cuerpo_responde_422(cliente):
    respuesta = cliente.post("/api/habitos", json={})
    assert respuesta.status_code == 422


# ---------------------------------------------------------------- POST /api/habitos/{id}/marcar

def test_marcar_habito_responde_200_con_racha(cliente, contador):
    habito = contador.agregar_habito("Leer")
    respuesta = cliente.post(f"/api/habitos/{habito['id']}/marcar")
    assert respuesta.status_code == 200
    assert respuesta.json()["racha"] == 1
    assert respuesta.json()["completado_hoy"] is True


def test_marcar_habito_inexistente_responde_404(cliente):
    respuesta = cliente.post("/api/habitos/99/marcar")
    assert respuesta.status_code == 404


def test_marcar_habito_dos_veces_responde_409(cliente, contador):
    habito = contador.agregar_habito("Leer")
    cliente.post(f"/api/habitos/{habito['id']}/marcar")
    respuesta = cliente.post(f"/api/habitos/{habito['id']}/marcar")
    assert respuesta.status_code == 409


# ---------------------------------------------------------------- DELETE /api/habitos/{id}

def test_eliminar_habito_responde_204(cliente, contador):
    habito = contador.agregar_habito("Leer")
    respuesta = cliente.delete(f"/api/habitos/{habito['id']}")
    assert respuesta.status_code == 204
    assert contador.listar_habitos() == []


def test_eliminar_habito_inexistente_responde_404(cliente):
    respuesta = cliente.delete("/api/habitos/99")
    assert respuesta.status_code == 404
