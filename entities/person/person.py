"""
Ruta: entities/person/person.py
"""
import random
from typing import Optional, List
from .genome import Genome

class Person:
    def __init__(self, 
                 entity_id: int, 
                 x: int, 
                 y: int, 
                 age: float = 0.0, 
                 genome: Optional[Genome] = None, 
                 gender: Optional[str] = None):
        
        # 1. Identidad y Posición (Privados)
        self._entity_id = entity_id
        self._x = x
        self._y = y
        self._age = age # AHORA REPRESENTA ESTRICTAMENTE DÍAS
        self._gender = gender if gender else random.choice(["M", "F"])
        self._genome = genome if genome else Genome()
        
        # 2. Estado de Salud (Privados)
        self._is_sick = False
        self._health_state = "sano" 
        self._is_adult = False
        self._is_senior = False
        
        # 3. Relaciones (Privados)
        self._partner_id = None
        self._marital_status = "soltero"
        self._relationship_days = 0.0
        
        # 4. Reproducción (Privados)
        self._is_pregnant = False
        self._pregnancy_days = 0.0
        self._failed_pregnancies = 0
        self._children_count = 0
        
        # 5. Genealogía (Privados)
        self._mother_id = None
        self._father_id = None
        self._parents = []

        # Inicialización de hitos según la edad en días proporcionada
        self._check_milestones()

    # ==========================================
    # PROPERTIES (Para lectura compatible)
    # ==========================================
    @property
    def entity_id(self) -> int: return self._entity_id
    @property
    def age(self) -> float: return self._age
    @property
    def x(self) -> int: return self._x
    @property
    def y(self) -> int: return self._y
    @property
    def gender(self) -> str: return self._gender
    @property
    def health_state(self) -> str: return self._health_state
    @property
    def is_pregnant(self) -> bool: return self._is_pregnant
    @property
    def marital_status(self) -> str: return self._marital_status
    @property
    def partner_id(self) -> Optional[int]: 
        return self._partner_id
    @property
    def is_sick(self) -> bool:
        return self._is_sick
    @property
    def genome(self) -> Genome:
        return self._genome
    @property
    def children_count(self) -> int: 
        return self._children_count
    @property
    def parents(self) -> List[int]: 
        return self._parents
    @property
    def mother_id(self) -> Optional[int]:
        return self._mother_id
    @property
    def father_id(self) -> Optional[int]:
        return self._father_id
    @property
    def relationship_days(self) -> float:
        return self._relationship_days
    @property
    def pregnancy_days(self) -> float:
        return float(self._pregnancy_days)
    @property
    def is_adult(self) -> bool: return self._is_adult
    @property
    def is_senior(self) -> bool: return self._is_senior
    

    # ==========================================
    # MÉTODOS DE COMPORTAMIENTO (API de Estado)
    # ==========================================

    def set_position(self, x: int, y: int):
        self._x, self._y = x, y

    def add_age(self, increment_days: float):
        """
        Incrementa la edad en días y autogestiona los hitos biológicos.
        """
        # 1. Incrementamos la edad directamente en días
        self._age += increment_days
        
        # 2. Autogestión de hitos
        self._check_milestones()

    def _check_milestones(self):
        """Lógica interna centralizada para actualizar banderas vitales según días de vida."""
        if self._age >= 6570.0:   # 18 años * 365
            self._is_adult = True
        
        if self._age >= 21900.0:  # 60 años * 365
            self._is_senior = True

    def set_health_state(self, new_state: str):
        """Gestiona el cambio de salud y la bandera is_sick automáticamente."""
        self._health_state = new_state
        self._is_sick = (new_state == "enfermo")

    def register_marriage(self, partner_id: int):
        self._partner_id = partner_id
        self._marital_status = "casado"
        self._relationship_days = 0.0

    def register_divorce(self):
        self._partner_id = None
        self._marital_status = "divorciado"

    def update_pregnancy(self, status: bool, days: float = 0.0):
        self._is_pregnant = bool(status)
        self._pregnancy_days = float(days)

    def add_failed_pregnancy(self):
        self._failed_pregnancies += 1

    def add_child(self):
        self._children_count += 1

    def add_relationship_days(self, days: float):
        """Incrementa los días de relación actual."""
        self._relationship_days += days

    def set_parents(self, mother_id: int, father_id: Optional[int] = None):
        """Asigna los padres del agente y actualiza la lista interna."""
        self._mother_id = mother_id
        self._father_id = father_id
        
        # Reconstruye la lista de padres automáticamente
        self._parents = [mother_id]
        if father_id is not None:
            self._parents.append(father_id)
    
    # ==========================================
    # LÓGICA DE NEGOCIO (Encapsulada)
    # ==========================================
    def is_fertile(self) -> bool:
        # Entre 18 años (6570 días) y 50 años (18250 días)
        return 6570.0 <= self._age <= 18250.0

    def can_reproduce(self) -> bool:
        return self.is_fertile() and not self._is_pregnant and not self._is_sick

    def get_longevity(self) -> float:
        return self._genome.longevity

    def get_immunity(self) -> float:
        return self._genome.immunity