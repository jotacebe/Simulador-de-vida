"""Módulo de Búfer Atómico Universal del ciclo de ejecución."""

from typing import List, Dict, Tuple, Any, Optional

class PendingChanges:
    """Contenedor de mutaciones encoladas para el estado del mundo."""

    def __init__(self) -> None:
        self.movements: Dict[int, Tuple[int, int]] = {}
        self.infections: List[int] = []
        self.recoveries: List[int] = []
        self.divorces: List[Tuple[int, int]] = []
        self.marriages: Dict[int, int] = {}
        self.pregnancy_updates: Dict[int, Dict[str, Any]] = {}
        self.births: List[Dict[str, Any]] = []
        self.age_increments: Dict[int, float] = {}
        self.adoptions: List[Dict[str, Any]] = []
        self.deaths: Dict[int, str] = {} 
        self.days_to_add: float = 0.0

    def register_movement(self, entity_id: int, x: int, y: int) -> None:
        self.movements[entity_id] = (x, y)

    def register_birth(self, mother_id: int, father_id: Optional[int], x: int, y: int, genome: Any) -> None:
        self.births.append({
            "mother_id": mother_id,
            "father_id": father_id,
            "x": x,
            "y": y,
            "genome": genome
        })

    def register_death(self, entity_id: int, reason: str = "Desconocido") -> None:
        if entity_id not in self.deaths:
            self.deaths[entity_id] = reason

    def register_marriage(self, p1: int, p2: int) -> None:
        self.marriages[p1] = p2

    def register_divorce(self, p1: int, p2: int) -> None:
        self.divorces.append((p1, p2))

    def register_adoption(self, child_id: int, parent_a: int, parent_b: Optional[int] = None) -> None:
        self.adoptions.append({"child_id": child_id, "parent_a": parent_a, "parent_b": parent_b})
    
    def register_infection(self, entity_id: int) -> None:
        self.infections.append(entity_id)

    def register_recovery(self, entity_id: int) -> None:
        self.recoveries.append(entity_id)
    
    def register_time_pass(self, days: float) -> None:
        self.days_to_add += days

    def register_pregnancy_update(self, entity_id: int, is_pregnant: bool, 
                                  pregnancy_days: float, failed_increment: int = 0,
                                  litter_size: int = 1) -> None:
        """Registra el avance de gestación incorporando el tamaño de camada."""
        self.pregnancy_updates[entity_id] = {
            "is_pregnant": is_pregnant,
            "pregnancy_days": float(pregnancy_days),
            "failed_increment": int(failed_increment),
            "litter_size": int(litter_size)
        }
    
    def register_age_increment(self, entity_id: int, increment_days: float) -> None:
        if entity_id not in self.age_increments:
            self.age_increments[entity_id] = 0.0
        self.age_increments[entity_id] += float(increment_days)
    
    def clear(self) -> None:
        self.movements.clear()
        self.infections.clear()
        self.recoveries.clear()
        self.divorces.clear()
        self.marriages.clear()
        self.pregnancy_updates.clear()
        self.births.clear()
        self.age_increments.clear()
        self.adoptions.clear()
        self.deaths.clear()
        self.days_to_add = 0.0