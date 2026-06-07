"""
Ruta: events/population/divorce_occurred.py
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class DivorceOccurredEvent:
    person_a_id: int
    person_b_id: int
    reason: str  # Ejemplo: "incompatibilidad", "enfermedad", "libre_albedrio"
    tick: int