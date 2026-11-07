"""API REST (FastAPI) del contador de hábitos.

Endpoints:
    GET    /                         -> interfaz HTML
    GET    /api/habitos              -> listar_habitos
    POST   /api/habitos              -> agregar_habito
    POST   /api/habitos/{id}/marcar  -> marcar_habito (completado hoy)
    DELETE /api/habitos/{id}         -> eliminar_habito
    GET    /api/estado               -> almacenamiento en uso (postgres | memoria)

Si la variable de entorno DATABASE_URL apunta a un PostgreSQL disponible, los datos
se guardan ahí; si no, la aplicación arranca igual y guarda en memoria.
"""

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.habitos import (
    ContadorHabitos,
    HabitoInvalido,
    HabitoNoEncontrado,
    HabitoYaMarcado,
)
from app.repositorios import crear_repositorio

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(message)s")

RUTA_INDEX = Path(__file__).resolve().parent.parent / "static" / "index.html"

app = FastAPI(title="Contador de Hábitos")

_contador = ContadorHabitos(repositorio=crear_repositorio())


def get_contador() -> ContadorHabitos:
    """Dependencia que entrega el almacenamiento; se reemplaza en las pruebas."""
    return _contador


class NuevoHabito(BaseModel):
    nombre: str


class HabitoRespuesta(BaseModel):
    id: int
    nombre: str
    racha: int
    completado_hoy: bool
    total_completados: int


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(RUTA_INDEX)


@app.get("/api/estado")
def estado(contador: ContadorHabitos = Depends(get_contador)) -> dict:
    return {"almacenamiento": contador.almacenamiento}


@app.get("/api/habitos", response_model=list[HabitoRespuesta])
def listar_habitos(contador: ContadorHabitos = Depends(get_contador)):
    return contador.listar_habitos()


@app.post(
    "/api/habitos",
    response_model=HabitoRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def agregar_habito(datos: NuevoHabito, contador: ContadorHabitos = Depends(get_contador)):
    try:
        return contador.agregar_habito(datos.nombre)
    except HabitoInvalido as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/api/habitos/{habito_id}/marcar", response_model=HabitoRespuesta)
def marcar_habito(habito_id: int, contador: ContadorHabitos = Depends(get_contador)):
    try:
        return contador.marcar_habito(habito_id)
    except HabitoNoEncontrado as error:
        raise HTTPException(status_code=404, detail=str(error))
    except HabitoYaMarcado as error:
        raise HTTPException(status_code=409, detail=str(error))


@app.delete("/api/habitos/{habito_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_habito(habito_id: int, contador: ContadorHabitos = Depends(get_contador)):
    try:
        contador.eliminar_habito(habito_id)
    except HabitoNoEncontrado as error:
        raise HTTPException(status_code=404, detail=str(error))
