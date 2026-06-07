"""
Ruta: events/population/adoption_completed.py
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class AdoptionCompletedEvent:
    child_id: int
    parent_a_id: int
    parent_b_id: Optional[int]  # Puede ser un adoptante soltero
    tick: int