"""
Ruta: entities/person/person.py
"""
import random
from typing import Optional, List, Dict, Any
from .genome import Genome
from core.config.simulation_config import SimulationConfig

class Person:
    def __init__(self, 
                 config: SimulationConfig,
                 entity_id: int, 
                 x: int, 
                 y: int, 
                 age: float = 0.0, 
                 genome: Optional[Genome] = None, 
                 gender: Optional[str] = None):
        
        self._config = config
        self._entity_id = entity_id
        self._x = x
        self._y = y
        self._age = age 
        self._gender = gender if gender else random.choice(["M", "F"])
        self._genome = genome if genome else Genome()
        
        self._is_sick = False
        self._health_state = "sano" 
        self._is_adult = False
        self._is_senior = False
        
        self._partner_id = None
        self._marital_status = "soltero"
        self._relationship_days = 0.0
        
        self._is_pregnant = False
        self._pregnancy_days = 0.0
        self._failed_pregnancies = 0
        self._children_count = 0
        
        self._mother_id = None
        self._father_id = None
        self._parents = []

        # Estructura Cognitiva Formalizada: Evita errores de KeyError o atributos dinámicos
        self._memory: Dict[str, Any] = {
            "trauma_overcrowding": 0.0,
            "trauma_sickness": 0.0,
            "preferred_sector": None,
            "rebellion_cooldown": 0.0
        }

        self._check_milestones()

    # ==========================================
    # PROPERTIES 
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
    def partner_id(self) -> Optional[int]: return self._partner_id
    @property
    def is_sick(self) -> bool: return self._is_sick
    @property
    def genome(self) -> Genome: return self._genome
    @property
    def children_count(self) -> int: return self._children_count
    @property
    def parents(self) -> List[int]: return self._parents
    @property
    def mother_id(self) -> Optional[int]: return self._mother_id
    @property
    def father_id(self) -> Optional[int]: return self._father_id
    @property
    def relationship_days(self) -> float: return self._relationship_days
    @property
    def pregnancy_days(self) -> float: return float(self._pregnancy_days)
    @property
    def is_adult(self) -> bool: return self._is_adult
    @property
    def is_senior(self) -> bool: return self._is_senior
    @property
    def memory(self) -> Dict[str, Any]: 
        """Expone la memoria cognitiva de forma segura para los sistemas."""
        return self._memory

    # ==========================================
    # MÉTODOS DE COMPORTAMIENTO (API de Estado)
    # ==========================================

    def set_position(self, x: int, y: int):
        self._x, self._y = x, y

    def add_age(self, increment_days: float):
        self._age += increment_days
        self._check_milestones()

    def _check_milestones(self):
        time_cfg = self._config.time
        if self._age >= time_cfg.adult_age_days:
            self._is_adult = True
        if self._age >= time_cfg.senior_age_days:
            self._is_senior = True

    def set_health_state(self, new_state: str):
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
        self._relationship_days += days

    def set_parents(self, mother_id: int, father_id: Optional[int] = None):
        self._mother_id = mother_id
        self._father_id = father_id
        self._parents = [mother_id]
        if father_id is not None:
            self._parents.append(father_id)
    
    # ==========================================
    # LÓGICA DE NEGOCIO (Encapsulada)
    # ==========================================
    def is_fertile(self) -> bool:
        repo_cfg = self._config.reproduction
        return repo_cfg.min_fertility_age_days <= self._age <= repo_cfg.max_fertility_age_days

    def can_reproduce(self) -> bool:
        return self.is_fertile() and not self._is_pregnant and not self._is_sick

    def get_longevity(self) -> float:
        return self._genome.longevity

    def get_immunity(self) -> float:
        return self._genome.immunity