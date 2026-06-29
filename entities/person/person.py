"""Módulo de la entidad biológica y social principal.

Responsabilidad:
Definir a la entidad autónoma con estados fisiológicos y psicológicos dinámicos.
Maneja de forma independiente el linaje biológico (inmutable) y la filiación 
legal/adoptiva (dinámica), permitiendo un rastreo preciso del fitness evolutivo.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from core.config.simulation_config import SimulationConfig
from entities.person.genome import Genome
from systems.diseases.pathogen import Pathogen


class Person:
    """Entidad autónoma con estados fisiológicos y psicológicos dinámicos."""

    def __init__(
        self,
        config: SimulationConfig,
        entity_id: int,
        x: int,
        y: int,
        age: float = 0.0,
        genome: Optional[Genome] = None,
        gender: Optional[str] = None,
        species: str = "human",
    ) -> None:
        """Inicializa una nueva entidad biológica en la simulación.

        Args:
            config: Configuración global de la simulación.
            entity_id: Identificador único del agente.
            x: Coordenada espacial X inicial.
            y: Coordenada espacial Y inicial.
            age: Edad base en días.
            genome: Genotipo de la entidad (se genera uno base si es None).
            gender: Género del agente ("M" o "F").
            species: Identificador de la especie biológica.
        """
        self._config = config
        self._entity_id = entity_id
        self._species = species

        self._x = x
        self._y = y
        self._age = age
        self._gender = gender if gender else random.choice(["M", "F"])
        self._genome = genome if genome else Genome(species_baseline=species)

        self._health_state = "sano"
        self._is_adult = False
        self._is_senior = False

        # ---------------- Historial Inmunológico y Carga Viral ----------------
        self._active_pathogens: Dict[str, Pathogen] = {}
        self._immune_memory: Dict[str, float] = {}  # Memoria adquirida por familia viral

        # ---------------- Relaciones y Reproducción ----------------
        self._partner_id: Optional[int] = None
        self._marital_status = "soltero"
        self._relationship_days = 0.0

        self._is_pregnant = False
        self._pregnancy_days = 0.0
        self._failed_pregnancies = 0
        
        # Separación entre hijos criados (social) y engendrados (genético)
        self._children_count = 0             # Hijos criados (Incluye adoptados)
        self._biological_children_count = 0  # Hijos estrictamente biológicos (Fitness)
        self._litter_size_gestating = 1

        # Linaje Biológico (Inmutable tras el nacimiento)
        self._mother_id: Optional[int] = None
        self._father_id: Optional[int] = None
        self._parents: List[int] = []
        
        # Filiación Legal / Social (Adoptiva)
        self._adoptive_parents: List[int] = []

        # ---------------- Psicología y Memoria ----------------
        self._memory: Dict[str, Any] = {
            "trauma_overcrowding": 0.0,
            "trauma_sickness": 0.0,
            "preferred_sector": None,
            "rebellion_cooldown": 0.0,
        }

        self._emotions: Dict[str, float] = {
            "stress": 0.0,
            "happiness": 0.8,
            "energy": 1.0,
        }

        self._check_milestones()

    # ==========================================
    # PROPERTIES BÁSICAS Y BIOLÓGICAS
    # ==========================================
    @property
    def entity_id(self) -> int:
        return self._entity_id

    @property
    def species(self) -> str:
        return self._species

    @property
    def age(self) -> float:
        return self._age

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y

    @property
    def gender(self) -> str:
        return self._gender

    @property
    def health_state(self) -> str:
        return self._health_state

    @property
    def genome(self) -> Genome:
        return self._genome

    @property
    def is_adult(self) -> bool:
        return self._is_adult

    @property
    def is_senior(self) -> bool:
        return self._is_senior

    # ==========================================
    # PROPERTIES SOCIALES Y REPRODUCTIVAS
    # ==========================================
    @property
    def is_pregnant(self) -> bool:
        return self._is_pregnant

    @property
    def marital_status(self) -> str:
        return self._marital_status

    @property
    def partner_id(self) -> Optional[int]:
        return self._partner_id

    @property
    def children_count(self) -> int:
        """Retorna el número de hijos criados (biológicos + adoptados)."""
        return self._children_count

    @property
    def biological_children_count(self) -> int:
        """Retorna el número de hijos estrictamente biológicos (Fitness evolutivo)."""
        return self._biological_children_count

    @property
    def parents(self) -> List[int]:
        """Retorna los IDs de los padres estrictamente biológicos."""
        return self._parents
        
    @property
    def adoptive_parents(self) -> List[int]:
        """Retorna los IDs de los padres legales/adoptivos."""
        return self._adoptive_parents

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
    def litter_size_gestating(self) -> int:
        return self._litter_size_gestating

    @property
    def memory(self) -> Dict[str, Any]:
        return self._memory

    @property
    def emotions(self) -> Dict[str, float]:
        return self._emotions

    @property
    def active_pathogens(self) -> Dict[str, Pathogen]:
        return self._active_pathogens

    @property
    def is_sick(self) -> bool:
        """Indica si el agente padece actualmente alguna infección."""
        return len(self._active_pathogens) > 0

    @property
    def effective_sociability(self) -> float:
        """Calcula la sociabilidad actual afectada por las emociones."""
        base = self._genome.sociability
        stress_penalty = self._emotions["stress"] * 0.4
        happiness_bonus = (self._emotions["happiness"] - 0.5) * 0.2
        return max(0.1, min(2.0, base - stress_penalty + happiness_bonus))

    @property
    def effective_temperament(self) -> float:
        """Calcula el temperamento actual afectado por traumas de memoria."""
        base = self._genome.temperament
        trauma = min(1.0, self._memory["trauma_sickness"] + self._memory["trauma_overcrowding"])
        return max(0.1, min(2.0, base - (trauma * 0.5)))

    # ==========================================
    # SISTEMA INMUNOLÓGICO Y SALUD
    # ==========================================
    def get_specific_immunity(self, family: str) -> float:
        """Calcula la resistencia combinando Genética (Innata) e Historial (Adquirida)."""
        base_innate = max(0.1, self._genome.immunity - ((1.0 - self._emotions["energy"]) * 0.2))
        acquired_bonus = self._immune_memory.get(family, 0.0)
        return min(3.0, base_innate + acquired_bonus)

    def infect(self, pathogen: Pathogen) -> None:
        """Infecta al agente con una cepa específica y aplica penalizaciones emocionales."""
        self._active_pathogens[pathogen.pathogen_id] = pathogen
        self._health_state = "enfermo"
        self.update_emotion("stress", 0.3)
        self.update_emotion("energy", -0.4)

    def recover(self, pathogen_id: str) -> None:
        """Elimina el patógeno y genera anticuerpos (memoria inmunológica)."""
        if pathogen_id in self._active_pathogens:
            pathogen = self._active_pathogens.pop(pathogen_id)

            # El cuerpo genera defensas específicas para esa familia viral
            current_acquired = self._immune_memory.get(pathogen.family, 0.0)
            self._immune_memory[pathogen.family] = min(1.5, current_acquired + 0.4)

        if not self._active_pathogens:
            self._health_state = "sano"

    def set_health_state(self, new_state: str) -> None:
        """Mantiene compatibilidad con subsistemas antiguos de salud."""
        if new_state == "sano":
            self._active_pathogens.clear()
            self._health_state = "sano"

    # ==========================================
    # MÉTODOS DE COMPORTAMIENTO RESTANTES
    # ==========================================
    def set_position(self, x: int, y: int) -> None:
        """Actualiza las coordenadas espaciales del agente."""
        self._x, self._y = x, y

    def add_age(self, increment_days: float) -> None:
        """Suma días biológicos al agente y comprueba si alcanza nuevas etapas vitales."""
        self._age += increment_days
        self._check_milestones()

    def _check_milestones(self) -> None:
        """Verifica y actualiza las etapas de desarrollo biológico (Adulto/Anciano)."""
        time_cfg = self._config.time
        if self._age >= time_cfg.adult_age_days:
            self._is_adult = True
        if self._age >= time_cfg.senior_age_days:
            self._is_senior = True

    def register_marriage(self, partner_id: int) -> None:
        """Vincula al agente con su nueva pareja legal."""
        self._partner_id = partner_id
        self._marital_status = "casado"
        self._relationship_days = 0.0
        self.update_emotion("happiness", 0.4)

    def register_divorce(self) -> None:
        """Rompe el vínculo conyugal y aplica penalizaciones psicológicas."""
        self._partner_id = None
        self._marital_status = "divorciado"
        self.update_emotion("stress", 0.5)
        self.update_emotion("happiness", -0.5)

    def update_pregnancy(self, status: bool, days: float = 0.0, litter_size: int = 1) -> None:
        """Actualiza el estado de gestación fisiológica."""
        self._is_pregnant = bool(status)
        self._pregnancy_days = float(days)
        self._litter_size_gestating = int(litter_size) if status else 1

    def add_failed_pregnancy(self) -> None:
        """Registra un aborto espontáneo sumando estrés traumático."""
        self._failed_pregnancies += 1
        self.update_emotion("stress", 0.6)

    def add_child(self) -> None:
        """Incrementa el contador legal/social de descendencia criada."""
        self._children_count += 1
        self.update_emotion("happiness", 0.5)

    def add_biological_child(self) -> None:
        """Registra un éxito evolutivo (hijo biológico) y asume su crianza inicial."""
        self._biological_children_count += 1
        self.add_child()

    def add_relationship_days(self, days: float) -> None:
        """Suma tiempo al contador de longevidad del matrimonio."""
        self._relationship_days += days

    def set_parents(self, mother_id: int, father_id: Optional[int] = None) -> None:
        """Asigna exclusivamente el linaje biológico en el momento de nacer.
        
        No debe utilizarse para adopciones legales.
        """
        self._mother_id = mother_id
        self._father_id = father_id
        self._parents = [mother_id]
        if father_id is not None:
            self._parents.append(father_id)

    def add_adoptive_parent(self, parent_id: int) -> None:
        """Registra un vínculo de filiación legal y social sin alterar la genética.
        
        Args:
            parent_id: El ID de la persona que adopta al agente.
        """
        if parent_id not in self._adoptive_parents:
            self._adoptive_parents.append(parent_id)
            self.update_emotion("happiness", 0.3)

    def update_emotion(self, emotion: str, amount: float) -> None:
        """Modifica de forma segura los valores psicológicos [0.0 - 1.0]."""
        if emotion in self._emotions:
            new_value = self._emotions[emotion] + amount
            self._emotions[emotion] = max(0.0, min(1.0, new_value))

    def is_fertile(self) -> bool:
        """Evalúa si la entidad se encuentra en etapa reproductiva."""
        repo_cfg = self._config.reproduction
        return repo_cfg.min_fertility_age_days <= self._age <= repo_cfg.max_fertility_age_days

    def can_reproduce(self) -> bool:
        """Verifica si la entidad cumple con todas las condiciones para gestar."""
        return self.is_fertile() and not self._is_pregnant and not self.is_sick

    def get_longevity(self) -> float:
        """Retorna el gen de longevidad expresado."""
        return self._genome.longevity

    def get_immunity(self) -> float:
        """Retorna el valor de inmunidad genérica base (Fallback)."""
        return max(0.1, self._genome.immunity - ((1.0 - self._emotions["energy"]) * 0.2))