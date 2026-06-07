"""
Ruta: events/population/relationship_created.py
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class RelationshipCreatedEvent:
    person_a_id: int
    person_b_id: int
    compatibility_score: float
    tick: int