"""Capa de almacenamiento del contador de hábitos.

Hay dos implementaciones con la misma interfaz:

* ``RepositorioMemoria``: guarda todo en un diccionario (se pierde al reiniciar).
* ``RepositorioPostgres``: guarda en PostgreSQL.

``crear_repositorio()`` decide cuál usar: si la variable de entorno ``DATABASE_URL``
existe y la base de datos responde, usa PostgreSQL; si no, usa memoria. Así la base
de datos es opcional y la aplicación (y el pipeline de CI) funcionan sin ella.
"""

import logging
import os
from datetime import date
from typing import Protocol

from app.modelos import Habito

logger = logging.getLogger(__name__)


class RepositorioHabitos(Protocol):
    nombre: str

    def listar(self) -> list[Habito]: ...

    def obtener(self, habito_id: int) -> Habito | None: ...

    def agregar(self, nombre: str) -> Habito: ...

    def registrar_fecha(self, habito_id: int, fecha: date) -> None: ...

    def eliminar(self, habito_id: int) -> None: ...


class RepositorioMemoria:
    nombre = "memoria"

    def __init__(self) -> None:
        self._habitos: dict[int, Habito] = {}
        self._siguiente_id = 1

    def listar(self) -> list[Habito]:
        return list(self._habitos.values())

    def obtener(self, habito_id: int) -> Habito | None:
        return self._habitos.get(habito_id)

    def agregar(self, nombre: str) -> Habito:
        habito = Habito(id=self._siguiente_id, nombre=nombre)
        self._habitos[habito.id] = habito
        self._siguiente_id += 1
        return habito

    def registrar_fecha(self, habito_id: int, fecha: date) -> None:
        self._habitos[habito_id].fechas_completadas.add(fecha)

    def eliminar(self, habito_id: int) -> None:
        self._habitos.pop(habito_id, None)


class RepositorioPostgres:
    nombre = "postgres"

    ESQUEMA = """
        CREATE TABLE IF NOT EXISTS habitos (
            id     SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS completados (
            habito_id INTEGER NOT NULL REFERENCES habitos(id) ON DELETE CASCADE,
            fecha     DATE    NOT NULL,
            PRIMARY KEY (habito_id, fecha)
        );
    """

    def __init__(self, url: str, timeout: int = 3) -> None:
        import psycopg  # import diferido: el driver solo hace falta si hay base de datos

        self._psycopg = psycopg
        self._url = url
        self._timeout = timeout
        with self._conectar() as conexion:  # falla aquí si la BD no está disponible
            conexion.execute(self.ESQUEMA)

    def _conectar(self):
        return self._psycopg.connect(self._url, connect_timeout=self._timeout)

    def listar(self) -> list[Habito]:
        with self._conectar() as conexion:
            filas = conexion.execute(
                "SELECT h.id, h.nombre, c.fecha FROM habitos h "
                "LEFT JOIN completados c ON c.habito_id = h.id ORDER BY h.id"
            ).fetchall()
        habitos: dict[int, Habito] = {}
        for habito_id, nombre, fecha in filas:
            habito = habitos.setdefault(habito_id, Habito(id=habito_id, nombre=nombre))
            if fecha is not None:
                habito.fechas_completadas.add(fecha)
        return list(habitos.values())

    def obtener(self, habito_id: int) -> Habito | None:
        return next((h for h in self.listar() if h.id == habito_id), None)

    def agregar(self, nombre: str) -> Habito:
        with self._conectar() as conexion:
            (habito_id,) = conexion.execute(
                "INSERT INTO habitos (nombre) VALUES (%s) RETURNING id", (nombre,)
            ).fetchone()
        return Habito(id=habito_id, nombre=nombre)

    def registrar_fecha(self, habito_id: int, fecha: date) -> None:
        with self._conectar() as conexion:
            conexion.execute(
                "INSERT INTO completados (habito_id, fecha) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (habito_id, fecha),
            )

    def eliminar(self, habito_id: int) -> None:
        with self._conectar() as conexion:
            conexion.execute("DELETE FROM habitos WHERE id = %s", (habito_id,))

    def borrar_todo(self) -> None:
        """Vacía las tablas (usado por las pruebas de integración)."""
        with self._conectar() as conexion:
            conexion.execute("TRUNCATE completados, habitos RESTART IDENTITY")


def crear_repositorio(url: str | None = None) -> RepositorioHabitos:
    """Usa PostgreSQL si está configurado y disponible; si no, memoria."""
    url = url if url is not None else os.getenv("DATABASE_URL")
    if not url:
        logger.info("DATABASE_URL no definida: se usará almacenamiento en memoria")
        return RepositorioMemoria()
    try:
        repositorio = RepositorioPostgres(url)
    except Exception as error:  # driver ausente, BD apagada, credenciales malas...
        logger.warning(
            "No se pudo conectar a la base de datos (%s): se usará almacenamiento en memoria",
            error,
        )
        return RepositorioMemoria()
    logger.info("Conectado a PostgreSQL")
    return repositorio
