"""
Ruta: events/population/marriage_created.py
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class MarriageCreatedEvent:
    person_a_id: int
    person_b_id: int
    tick: int