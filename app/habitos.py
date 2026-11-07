"""Lógica de negocio del contador de hábitos.

Se mantiene separada del framework web y del almacenamiento para poder probarla
de forma aislada. El "reloj" y el repositorio se inyectan, así las pruebas pueden
controlar la fecha de "hoy" y elegir dónde se guardan los datos.
"""

from datetime import date, timedelta
from typing import Callable

from app.modelos import Habito
from app.repositorios import RepositorioHabitos, RepositorioMemoria

LONGITUD_MAXIMA_NOMBRE = 50


class HabitoNoEncontrado(Exception):
    """El hábito solicitado no existe."""


class HabitoInvalido(Exception):
    """Los datos del hábito no son válidos (nombre vacío, duplicado, etc.)."""


class HabitoYaMarcado(Exception):
    """El hábito ya fue marcado en la fecha indicada."""


def calcular_racha(fechas: set[date], hoy: date) -> int:
    """Cuenta los días consecutivos completados hasta hoy.

    Si el hábito todavía no se marcó hoy, la racha sigue viva si se marcó
    ayer (el usuario aún tiene el resto del día para marcarlo).
    """
    if hoy in fechas:
        dia = hoy
    elif hoy - timedelta(days=1) in fechas:
        dia = hoy - timedelta(days=1)
    else:
        return 0

    racha = 0
    while dia in fechas:
        racha += 1
        dia -= timedelta(days=1)
    return racha


class ContadorHabitos:
    def __init__(
        self,
        reloj: Callable[[], date] = date.today,
        repositorio: RepositorioHabitos | None = None,
    ):
        self._reloj = reloj
        self._repositorio = repositorio if repositorio is not None else RepositorioMemoria()

    @property
    def almacenamiento(self) -> str:
        return self._repositorio.nombre

    # ---------- Consultas ----------

    def listar_habitos(self) -> list[dict]:
        return [self._a_dict(h) for h in self._repositorio.listar()]

    def obtener_habito(self, habito_id: int) -> dict:
        return self._a_dict(self._buscar(habito_id))

    # ---------- Comandos ----------

    def agregar_habito(self, nombre: str) -> dict:
        nombre_limpio = (nombre or "").strip()
        if not nombre_limpio:
            raise HabitoInvalido("El nombre del hábito no puede estar vacío")
        if len(nombre_limpio) > LONGITUD_MAXIMA_NOMBRE:
            raise HabitoInvalido(
                f"El nombre no puede superar {LONGITUD_MAXIMA_NOMBRE} caracteres"
            )
        if any(h.nombre.lower() == nombre_limpio.lower() for h in self._repositorio.listar()):
            raise HabitoInvalido(f"Ya existe un hábito llamado '{nombre_limpio}'")

        return self._a_dict(self._repositorio.agregar(nombre_limpio))

    def marcar_habito(self, habito_id: int) -> dict:
        habito = self._buscar(habito_id)
        hoy = self._reloj()
        if hoy in habito.fechas_completadas:
            raise HabitoYaMarcado(f"'{habito.nombre}' ya fue marcado hoy")
        self._repositorio.registrar_fecha(habito_id, hoy)
        return self.obtener_habito(habito_id)

    def eliminar_habito(self, habito_id: int) -> None:
        self._buscar(habito_id)
        self._repositorio.eliminar(habito_id)

    # ---------- Auxiliares ----------

    def _buscar(self, habito_id: int) -> Habito:
        habito = self._repositorio.obtener(habito_id)
        if habito is None:
            raise HabitoNoEncontrado(f"No existe el hábito con id {habito_id}")
        return habito

    def _a_dict(self, habito: Habito) -> dict:
        hoy = self._reloj()
        return {
            "id": habito.id,
            "nombre": habito.nombre,
            "racha": calcular_racha(habito.fechas_completadas, hoy),
            "completado_hoy": hoy in habito.fechas_completadas,
            "total_completados": len(habito.fechas_completadas),
        }
