from dataclasses import dataclass, field
from datetime import date


@dataclass
class Habito:
    id: int
    nombre: str
    fechas_completadas: set[date] = field(default_factory=set)
