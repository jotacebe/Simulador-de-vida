"""
Ruta: core/state/pending_changes.py
Responsabilidad: Búfer atómico universal de cambios del ciclo de ejecución.
"""
from typing import List, Dict, Tuple, Any, Optional

class PendingChanges:
    def __init__(self):
        self.movements: Dict[int, Tuple[int, int]] = {}
        self.infections: List[int] = []
        self.recoveries: List[int] = []
        self.divorces: List[Tuple[int, int]] = []
        self.marriages: Dict[int, int] = {}
        self.pregnancy_updates: Dict[int, Dict[str, Any]] = {}
        self.births: List[Dict[str, Any]] = []
        self.age_increments: Dict[int, float] = {}  # Actualizado a float (días continuos)
        self.adoptions: List[Dict[str, Any]] = []
        self.deaths: Dict[int, str] = {} 
        self.days_to_add: float = 0.0

    def register_movement(self, entity_id: int, x: int, y: int) -> None:
        self.movements[entity_id] = (x, y)

    def register_birth(self, mother_id: int, father_id: Optional[int], x: int, y: int, genome: Any) -> None:
        """
        Registra un nuevo nacimiento en la cola de cambios pendientes,
        guardando el objeto Genome completo.
        """
        self.births.append({
            "mother_id": mother_id,
            "father_id": father_id,
            "x": x,
            "y": y,
            "genome": genome  # Contenedor genético completo
        })

    def register_death(self, entity_id: int, reason: str = "Desconocido") -> None:
        if entity_id not in self.deaths:
            self.deaths[entity_id] = reason

    def register_marriage(self, p1: int, p2: int) -> None:
        self.marriages[p1] = p2

    def register_divorce(self, p1: int, p2: int) -> None:
        self.divorces.append((p1, p2))

    def register_adoption(self, child_id: int, parent_a: int, parent_b: Any = None) -> None:
        self.adoptions.append({"child_id": child_id, "parent_a": parent_a, "parent_b": parent_b})
    
    def register_infection(self, entity_id: int) -> None:
        self.infections.append(entity_id)

    def register_recovery(self, entity_id: int) -> None:
        self.recoveries.append(entity_id)
    
    def register_time_pass(self, days: float) -> None:
        """Registra el paso del tiempo global en días continuos."""
        self.days_to_add += days

    def register_pregnancy_update(self, entity_id: int, is_pregnant: bool, pregnancy_days: float) -> None:
        # Guardamos como diccionario para que world_state.py lo lea correctamente
        self.pregnancy_updates[entity_id] = {
            "is_pregnant": is_pregnant,
            "pregnancy_days": float(pregnancy_days)
        }
    
    def register_age_increment(self, entity_id: int, increment_days: float) -> None:
        """Registra cuántos días biológicos debe envejecer una entidad de forma acumulativa."""
        if entity_id not in self.age_increments:
            self.age_increments[entity_id] = 0.0
        self.age_increments[entity_id] += float(increment_days)
    
    def clear(self) -> None:
        """Limpia el búfer transaccional para el siguiente tick reiniciando la instancia."""
        self.__init__()