"""
Ruta: events/population/person_died.py
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class PersonDiedEvent:
    entity_id: int
    age: int
    cause: str
    tick: int