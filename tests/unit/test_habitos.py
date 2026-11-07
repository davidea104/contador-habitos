"""Pruebas unitarias de la lógica de negocio (app/habitos.py).

Cada prueba sigue la estrategia AAA: Arrange (preparar), Act (actuar), Assert (verificar).
Se usa un reloj falso para controlar la fecha de "hoy" y así probar las rachas.
"""

from datetime import date, timedelta

import pytest

from app.habitos import (
    ContadorHabitos,
    HabitoInvalido,
    HabitoNoEncontrado,
    HabitoYaMarcado,
    calcular_racha,
)

HOY = date(2026, 11, 7)


class RelojFalso:
    """Reloj controlable: permite avanzar los días dentro de una prueba."""

    def __init__(self, fecha: date):
        self.fecha = fecha

    def __call__(self) -> date:
        return self.fecha

    def avanzar(self, dias: int = 1) -> None:
        self.fecha += timedelta(days=dias)


@pytest.fixture
def reloj():
    return RelojFalso(HOY)


@pytest.fixture
def contador(reloj):
    return ContadorHabitos(reloj=reloj)


# ---------------------------------------------------------------- agregar_habito

def test_agregar_habito_lo_guarda_en_la_lista_interna(contador):
    # Arrange: contador vacío (fixture)
    # Act
    habito = contador.agregar_habito("Tomar agua")
    # Assert
    assert habito == {
        "id": 1,
        "nombre": "Tomar agua",
        "racha": 0,
        "completado_hoy": False,
        "total_completados": 0,
    }
    assert contador.listar_habitos() == [habito]


def test_agregar_habito_asigna_ids_incrementales(contador):
    primero = contador.agregar_habito("Leer")
    segundo = contador.agregar_habito("Correr")
    assert (primero["id"], segundo["id"]) == (1, 2)


def test_agregar_habito_elimina_espacios_del_nombre(contador):
    habito = contador.agregar_habito("   Meditar   ")
    assert habito["nombre"] == "Meditar"


@pytest.mark.parametrize("nombre", ["", "    ", None])
def test_agregar_habito_rechaza_nombre_vacio(contador, nombre):
    with pytest.raises(HabitoInvalido, match="vacío"):
        contador.agregar_habito(nombre)
    assert contador.listar_habitos() == []


def test_agregar_habito_rechaza_nombre_demasiado_largo(contador):
    with pytest.raises(HabitoInvalido, match="50 caracteres"):
        contador.agregar_habito("x" * 51)


def test_agregar_habito_acepta_nombre_con_longitud_maxima(contador):
    habito = contador.agregar_habito("x" * 50)
    assert len(habito["nombre"]) == 50


def test_agregar_habito_rechaza_duplicados_sin_importar_mayusculas(contador):
    contador.agregar_habito("Tomar agua")
    with pytest.raises(HabitoInvalido, match="Ya existe"):
        contador.agregar_habito("TOMAR AGUA")
    assert len(contador.listar_habitos()) == 1


# ---------------------------------------------------------------- listar_habitos

def test_listar_habitos_vacio_devuelve_lista_vacia(contador):
    assert contador.listar_habitos() == []


def test_listar_habitos_devuelve_todos_en_orden_de_creacion(contador):
    contador.agregar_habito("Leer")
    contador.agregar_habito("Correr")
    nombres = [h["nombre"] for h in contador.listar_habitos()]
    assert nombres == ["Leer", "Correr"]


# ---------------------------------------------------------------- obtener_habito

def test_obtener_habito_existente(contador):
    creado = contador.agregar_habito("Leer")
    assert contador.obtener_habito(creado["id"]) == creado


def test_obtener_habito_inexistente_lanza_error(contador):
    with pytest.raises(HabitoNoEncontrado):
        contador.obtener_habito(99)


# ---------------------------------------------------------------- marcar_habito

def test_marcar_habito_inicia_racha_en_uno(contador):
    # Arrange
    habito = contador.agregar_habito("Leer")
    # Act
    marcado = contador.marcar_habito(habito["id"])
    # Assert
    assert marcado["racha"] == 1
    assert marcado["completado_hoy"] is True
    assert marcado["total_completados"] == 1


def test_marcar_habito_dos_veces_el_mismo_dia_falla(contador):
    habito = contador.agregar_habito("Leer")
    contador.marcar_habito(habito["id"])
    with pytest.raises(HabitoYaMarcado):
        contador.marcar_habito(habito["id"])
    assert contador.obtener_habito(habito["id"])["total_completados"] == 1


def test_marcar_habito_en_dias_consecutivos_aumenta_la_racha(contador, reloj):
    habito = contador.agregar_habito("Leer")
    for _ in range(3):
        contador.marcar_habito(habito["id"])
        reloj.avanzar()
    reloj.avanzar(-1)  # volvemos al último día marcado
    assert contador.obtener_habito(habito["id"])["racha"] == 3


def test_saltarse_un_dia_reinicia_la_racha(contador, reloj):
    habito = contador.agregar_habito("Leer")
    contador.marcar_habito(habito["id"])
    reloj.avanzar(2)  # se salta un día completo
    resultado = contador.marcar_habito(habito["id"])
    assert resultado["racha"] == 1
    assert resultado["total_completados"] == 2


def test_marcar_habito_inexistente_lanza_error(contador):
    with pytest.raises(HabitoNoEncontrado):
        contador.marcar_habito(42)


# ---------------------------------------------------------------- eliminar_habito

def test_eliminar_habito_lo_quita_de_la_lista(contador):
    leer = contador.agregar_habito("Leer")
    correr = contador.agregar_habito("Correr")
    contador.eliminar_habito(leer["id"])
    assert contador.listar_habitos() == [correr]


def test_eliminar_habito_inexistente_lanza_error(contador):
    with pytest.raises(HabitoNoEncontrado):
        contador.eliminar_habito(7)


def test_eliminar_habito_permite_reutilizar_el_nombre(contador):
    habito = contador.agregar_habito("Leer")
    contador.eliminar_habito(habito["id"])
    nuevo = contador.agregar_habito("Leer")
    assert nuevo["id"] == 2  # los ids no se reutilizan


# ---------------------------------------------------------------- calcular_racha

def test_calcular_racha_sin_fechas_es_cero():
    assert calcular_racha(set(), HOY) == 0


def test_calcular_racha_cuenta_dias_consecutivos_hasta_hoy():
    fechas = {HOY, HOY - timedelta(days=1), HOY - timedelta(days=2)}
    assert calcular_racha(fechas, HOY) == 3


def test_calcular_racha_sigue_viva_si_se_marco_ayer_pero_no_hoy():
    fechas = {HOY - timedelta(days=1), HOY - timedelta(days=2)}
    assert calcular_racha(fechas, HOY) == 2


def test_calcular_racha_se_rompe_si_el_ultimo_registro_es_antiguo():
    fechas = {HOY - timedelta(days=2), HOY - timedelta(days=3)}
    assert calcular_racha(fechas, HOY) == 0


def test_calcular_racha_ignora_dias_anteriores_a_un_hueco():
    fechas = {HOY, HOY - timedelta(days=2), HOY - timedelta(days=3)}
    assert calcular_racha(fechas, HOY) == 1
