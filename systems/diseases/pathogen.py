"""Módulo que define la estructura biológica de los patógenos y sus mutaciones.

Implementa un sistema de identificación único global para cada cepa,
permitiendo rastrear la genealogía viral (árbol filogenético).

Incluye sistema de relaciones entre familias de patógenos para modelar
inmunidad cruzada (ej: Influenza A y B comparten protección parcial).

Cada patógeno tiene:
- ID único global (ej: "Influenza_000001")
- Familia (ej: "Influenza")
- Generación (número de mutaciones desde el ancestro)
- Ancestro directo (ID del patógeno padre)
- Propiedades: virulencia, transmisibilidad, letalidad
- Probabilidad de ser asintomático
- Periodo de incubación específico
"""

import random
import threading
from typing import Optional, Dict, Set
from enum import Enum


class InfectionPhase(Enum):
    """Fases de progresión de una infección."""
    EXPOSED = "expuesto"
    INCUBATING = "incubando"
    CONTAGIOUS = "contagioso"
    SYMPTOMATIC = "sintomático"
    RECOVERING = "recuperándose"


class Pathogen:
    """Representa una cepa viral específica con capacidad de propagación y mutación."""

    # Contador global para generar IDs únicos
    _counter_lock = threading.Lock()
    _next_id = 1

    # =====================================================================
    # NUEVO: RELACIONES ENTRE FAMILIAS (Punto 7 - Inmunidad Cruzada)
    # =====================================================================
    # Define qué familias de patógenos están relacionadas y comparten
    # inmunidad cruzada. El valor es el grado de similitud (0.0 a 1.0).
    # 0.0 = sin relación, 1.0 = idénticas
    _family_relations: Dict[str, Dict[str, float]] = {
        "Influenza": {"Influenza": 1.0, "Coronavirus": 0.15},
        "Coronavirus": {"Coronavirus": 1.0, "Influenza": 0.15, "SARS": 0.6},
        "SARS": {"SARS": 1.0, "Coronavirus": 0.6, "MERS": 0.5},
        "MERS": {"MERS": 1.0, "SARS": 0.5, "Coronavirus": 0.4},
        "Poxvirus": {"Poxvirus": 1.0, "Bacteriofago_X": 0.05},
        "Bacteriofago_X": {"Bacteriofago_X": 1.0, "Poxvirus": 0.05},
    }

    def __init__(
        self,
        family: str,
        variant_id: int,
        virulence: float,
        transmission: float,
        lethality: float,
        generation: int = 1,
        ancestor_id: Optional[str] = None,
        asymptomatic_chance: float = 0.2,
        incubation_days: float = 3.0,
    ) -> None:
        """Inicializa un patógeno con ID único global."""
        self.family = family
        self.variant_id = variant_id
        self.generation = generation
        self.ancestor_id = ancestor_id
        
        with Pathogen._counter_lock:
            self.unique_id = Pathogen._next_id
            Pathogen._next_id += 1
        
        self.pathogen_id = f"{family}_{self.unique_id:06d}"
        
        self.virulence = virulence
        self.transmission = transmission
        self.lethality = lethality
        self.asymptomatic_chance = asymptomatic_chance
        self.incubation_days = incubation_days

    def mutate(self) -> 'Pathogen':
        """Genera una nueva variante mediante deriva genética estocástica."""
        return Pathogen(
            family=self.family,
            variant_id=self.variant_id + 1,
            virulence=max(0.1, self.virulence * random.uniform(0.85, 1.15)),
            transmission=max(0.01, self.transmission * random.uniform(0.85, 1.15)),
            lethality=max(0.0, min(1.0, self.lethality * random.uniform(0.85, 1.15))),
            generation=self.generation + 1,
            ancestor_id=self.pathogen_id,
            asymptomatic_chance=max(0.0, min(1.0, self.asymptomatic_chance * random.uniform(0.85, 1.15))),
            incubation_days=max(1.0, self.incubation_days * random.uniform(0.85, 1.15)),
        )

    def __repr__(self) -> str:
        """Representación string del patógeno para debugging."""
        return (
            f"Pathogen(id={self.pathogen_id}, family={self.family}, "
            f"gen={self.generation}, vir={self.virulence:.2f}, "
            f"trans={self.transmission:.2f}, let={self.lethality:.2f}, "
            f"asym={self.asymptomatic_chance:.2f}, inc={self.incubation_days:.1f}d)"
        )

    @classmethod
    def create_random_variant(cls, family: str) -> 'Pathogen':
        """Crea una variante inicial con propiedades aleatorias."""
        return cls(
            family=family,
            variant_id=1,
            virulence=random.uniform(0.3, 1.5),
            transmission=random.uniform(0.05, 0.5),
            lethality=random.uniform(0.01, 0.5),
            generation=1,
            ancestor_id=None,
            asymptomatic_chance=random.uniform(0.1, 0.4),
            incubation_days=random.uniform(2.0, 7.0),
        )

    @classmethod
    def get_family_similarity(cls, family1: str, family2: str) -> float:
        """Obtiene el grado de similitud entre dos familias de patógenos.
        
        Args:
            family1: Primera familia.
            family2: Segunda familia.
            
        Returns:
            Grado de similitud [0.0, 1.0].
        """
        if family1 == family2:
            return 1.0
        
        # Buscar en la tabla de relaciones
        if family1 in cls._family_relations:
            return cls._family_relations[family1].get(family2, 0.0)
        
        # Si no está definida, asumir sin relación
        return 0.0

    @classmethod
    def get_related_families(cls, family: str, min_similarity: float = 0.1) -> Set[str]:
        """Obtiene todas las familias relacionadas con una familia dada.
        
        Args:
            family: Familia de referencia.
            min_similarity: Similitud mínima para considerar relacionada.
            
        Returns:
            Conjunto de familias relacionadas.
        """
        related = set()
        if family in cls._family_relations:
            for other_family, similarity in cls._family_relations[family].items():
                if similarity >= min_similarity and other_family != family:
                    related.add(other_family)
        return related


class InfectionState:
    """Estado de progresión de una infección específica en un huésped."""

    def __init__(self, pathogen: Pathogen) -> None:
        """Inicializa el estado de infección."""
        self.pathogen = pathogen
        self.phase = InfectionPhase.EXPOSED
        self.days_in_phase = 0.0
        self.total_days = 0.0
        
        self.is_asymptomatic = random.random() < pathogen.asymptomatic_chance
        
        self.exposed_duration = 0.5
        self.incubation_duration = pathogen.incubation_days
        self.contagious_duration = 5.0 + (pathogen.virulence * 3.0)
        self.recovering_duration = 3.0

    def advance(self, delta_days: float) -> None:
        """Avanza el estado de la infección en el tiempo."""
        self.days_in_phase += delta_days
        self.total_days += delta_days
        
        if self.phase == InfectionPhase.EXPOSED:
            if self.days_in_phase >= self.exposed_duration:
                self.phase = InfectionPhase.INCUBATING
                self.days_in_phase = 0.0
                
        elif self.phase == InfectionPhase.INCUBATING:
            if self.days_in_phase >= self.incubation_duration:
                if self.is_asymptomatic:
                    self.phase = InfectionPhase.CONTAGIOUS
                else:
                    self.phase = InfectionPhase.SYMPTOMATIC
                self.days_in_phase = 0.0
                
        elif self.phase == InfectionPhase.CONTAGIOUS:
            if self.days_in_phase >= self.contagious_duration:
                self.phase = InfectionPhase.RECOVERING
                self.days_in_phase = 0.0
                
        elif self.phase == InfectionPhase.SYMPTOMATIC:
            if self.days_in_phase >= self.contagious_duration:
                self.phase = InfectionPhase.RECOVERING
                self.days_in_phase = 0.0

    def is_contagious(self) -> bool:
        """Determina si la infección puede transmitirse en este momento."""
        return self.phase in (InfectionPhase.CONTAGIOUS, InfectionPhase.SYMPTOMATIC)

    def get_transmission_multiplier(self) -> float:
        """Obtiene el multiplicador de transmisión según la fase."""
        if self.phase == InfectionPhase.EXPOSED:
            return 0.0
        elif self.phase == InfectionPhase.INCUBATING:
            return 0.0
        elif self.phase == InfectionPhase.CONTAGIOUS:
            return 1.0
        elif self.phase == InfectionPhase.SYMPTOMATIC:
            return 1.2
        elif self.phase == InfectionPhase.RECOVERING:
            return 0.3
        return 0.0

    def __repr__(self) -> str:
        """Representación string del estado de infección."""
        return (
            f"InfectionState(pathogen={self.pathogen.pathogen_id}, "
            f"phase={self.phase.value}, days_in_phase={self.days_in_phase:.1f}, "
            f"total={self.total_days:.1f}, asymptomatic={self.is_asymptomatic})"
        )