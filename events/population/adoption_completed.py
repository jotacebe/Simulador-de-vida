"""
Ruta: events/population/adoption_completed.py
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AdoptionCompletedEvent:
    """Evento publicado cuando se consuma una adopción.
    
    Attributes:
        child_id: ID de la entidad adoptada.
        parent_a_id: ID del primer progenitor adoptivo.
        parent_b_id: ID del segundo progenitor adoptivo (None si es monoparental).
        tick: Número de tick en el que ocurrió la adopción.
        is_single_parent: True si la adopción es monoparental (soltero/viudo/divorciado).
    """
    child_id: int
    parent_a_id: int
    parent_b_id: Optional[int]
    tick: int
    is_single_parent: bool = False