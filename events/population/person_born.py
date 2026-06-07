"""
Ruta: events/population/person_born.py
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class PersonBornEvent:
    entity_id: int
    mother_id: int
    father_id: int
    x: int
    y: int
    gender: str
    tick: int