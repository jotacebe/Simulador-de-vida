"""Módulo de la entidad biológica y social principal.

Responsabilidad:
Definir a la entidad autónoma con estados fisiológicos y psicológicos dinámicos.
Maneja de forma independiente el linaje biológico (inmutable) y la filiación 
legal/adoptiva (dinámica), permitiendo un rastreo preciso del fitness evolutivo.

Incluye:
- Sistema inmunológico avanzado con memoria adquirida por cepa
- Inmunidad genética específica por familia de patógenos (heredable)
- Inmunidad cruzada entre familias relacionadas
- Inmunidad adaptativa: se reduce según distancia genealógica del patógeno
- Sistema de enfermedades con fases de progresión
- Soporte para infecciones asintomáticas
- Sistema de motivaciones continuas para comportamiento emergente
- Sistema de relaciones sociales con espectro Kinsey y estados recesivos
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from core.config.simulation_config import SimulationConfig
from entities.person.genome import Genome
from systems.diseases.pathogen import Pathogen, InfectionState, InfectionPhase
from systems.relationships.relationship_model import (
    Relationship,
    RelationshipStatus,
    RelationshipType,
    SexualOrientation,
)


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
        """Inicializa una nueva entidad biológica en la simulación."""
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

        # =====================================================================
        # HISTORIAL INMUNOLÓGICO Y INFECCIONES
        # =====================================================================
        self._active_infections: Dict[str, InfectionState] = {}
        
        # Inmunidad por familia (genérica, legacy)
        self._immune_memory: Dict[str, float] = {}
        
        # NUEVO: Inmunidad específica por cepa
        self._strain_immunity: Dict[str, float] = {}
        
        # NUEVO: Metadata de cada cepa conocida (generación, propiedades)
        self._strain_metadata: Dict[str, dict] = {}

        # =====================================================================
        # RELACIONES Y REPRODUCCIÓN
        # =====================================================================
        self._is_pregnant = False
        self._pregnancy_days = 0.0
        self._failed_pregnancies = 0

        self._children_count = 0
        self._biological_children_count = 0
        self._litter_size_gestating = 1

        # Linaje Biológico
        self._mother_id: Optional[int] = None
        self._father_id: Optional[int] = None
        self._parents: List[int] = []

        # Filiación Legal / Social (Adoptiva)
        self._adoptive_parents: List[int] = []

        # =====================================================================
        # PSICOLOGÍA Y MEMORIA
        # =====================================================================
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

        # =====================================================================
        # SISTEMA DE MOTIVACIONES CONTINUAS
        # =====================================================================
        self._motivations: Dict[str, float] = {
            "independence": 0.3,
            "exploration": 0.3,
            "rebellion": 0.2,
            "partnership": 0.5,
            "protection": 0.4,
            "migration": 0.2,
            "cooperation": 0.5,
            "fertility_desire": 0.5,
        }

        # =====================================================================
        # SISTEMA DE RELACIONES SOCIALES
        # =====================================================================
        # Orientación sexual según espectro Kinsey
        self._sexual_orientation: SexualOrientation = self._generate_orientation()
        
        # Lista de relaciones (activas e históricas)
        self._relationships: List[Relationship] = []
        
        # Backwards compatibility: se derivan de _relationships
        self._partner_id: Optional[int] = None
        self._marital_status: str = "soltero"

        self._check_milestones()

    # ==========================================
    # GENERACIÓN DE ORIENTACIÓN SEXUAL
    # ==========================================
    def _generate_orientation(self) -> SexualOrientation:
        """Genera orientación sexual con distribución poblacional realista.
        
        Distribución aproximada (basada en estudios Kinsey):
        - 0 (exclusivamente heterosexual): ~65%
        - 1 (predominantemente heterosexual): ~15%
        - 2 (bisexual con preferencia heterosexual): ~5%
        - 3 (bisexual equilibrado): ~3%
        - 4 (bisexual con preferencia homosexual): ~2%
        - 5 (predominantemente homosexual): ~5%
        - 6 (exclusivamente homosexual): ~5%
        """
        roll = random.random()
        if roll < 0.65:
            return SexualOrientation.HETEROSEXUAL
        elif roll < 0.80:
            return SexualOrientation.MOSTLY_HETERO
        elif roll < 0.85:
            return SexualOrientation.BISEXUAL_HETERO
        elif roll < 0.88:
            return SexualOrientation.BISEXUAL
        elif roll < 0.90:
            return SexualOrientation.BISEXUAL_HOMO
        elif roll < 0.95:
            return SexualOrientation.MOSTLY_HOMO
        else:
            return SexualOrientation.HOMOSEXUAL

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
    def children_count(self) -> int:
        return self._children_count

    @property
    def biological_children_count(self) -> int:
        return self._biological_children_count

    @property
    def parents(self) -> List[int]:
        return self._parents

    @property
    def adoptive_parents(self) -> List[int]:
        return self._adoptive_parents

    @property
    def mother_id(self) -> Optional[int]:
        return self._mother_id

    @property
    def father_id(self) -> Optional[int]:
        return self._father_id

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
    def motivations(self) -> Dict[str, float]:
        """Devuelve el diccionario de motivaciones continuas."""
        return self._motivations

    @property
    def active_pathogens(self) -> Dict[str, Pathogen]:
        """Propiedad de compatibilidad que devuelve solo los Pathogen."""
        return {pid: state.pathogen for pid, state in self._active_infections.items()}

    @property
    def active_infections(self) -> Dict[str, InfectionState]:
        """Devuelve todas las infecciones activas con su estado completo."""
        return self._active_infections

    @property
    def is_sick(self) -> bool:
        """Indica si el agente padece actualmente alguna infección."""
        return len(self._active_infections) > 0

    @property
    def is_symptomatic(self) -> bool:
        """Indica si el agente muestra síntomas de alguna infección."""
        return any(
            state.phase == InfectionPhase.SYMPTOMATIC
            for state in self._active_infections.values()
        )

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
        trauma = min(1.0, self._memory.get("trauma_sickness", 0.0) + self._memory.get("trauma_overcrowding", 0.0))
        return max(0.1, min(2.0, base - (trauma * 0.5)))

    # ==========================================
    # PROPERTIES DE RELACIONES SOCIALES
    # ==========================================
    @property
    def sexual_orientation(self) -> SexualOrientation:
        """Orientación sexual del agente (espectro Kinsey 0-6)."""
        return self._sexual_orientation

    @property
    def relationships(self) -> List[Relationship]:
        """Lista de todas las relaciones (activas e históricas)."""
        return self._relationships

    @property
    def partner_id(self) -> Optional[int]:
        """DEPRECATED: Devuelve el ID de la relación más consolidada activa.
        
        Mantiene compatibilidad hacia atrás con sistemas legacy que usan
        partner_id directamente (ConceptionSystem, AdoptionSystem, etc.).
        """
        active = self._get_active_relationships()
        if not active:
            return self._partner_id
        
        priority = [
            RelationshipStatus.CONSOLIDATED,
            RelationshipStatus.COHABITATION,
            RelationshipStatus.DATING,
            RelationshipStatus.CASUAL,
            RelationshipStatus.ROMANTIC_INTEREST,
        ]
        for status in priority:
            for rel in active:
                if rel.status == status:
                    return rel.partner_id
        return active[0].partner_id if active else self._partner_id

    @property
    def marital_status(self) -> str:
        """DEPRECATED: Devuelve el estado civil derivado de las relaciones."""
        active = self._get_active_relationships()
        if not active:
            return self._marital_status
        
        priority = [
            RelationshipStatus.CONSOLIDATED,
            RelationshipStatus.COHABITATION,
            RelationshipStatus.DATING,
            RelationshipStatus.ROMANTIC_INTEREST,
        ]
        for status in priority:
            for rel in active:
                if rel.status == status:
                    return "casado"
        
        for rel in self._relationships:
            if rel.status == RelationshipStatus.EX_PARTNER:
                return "divorciado"
        
        return "soltero"

    @property
    def relationship_days(self) -> float:
        """DEPRECATED: Días en la relación más consolidada activa."""
        active = self._get_active_relationships()
        if not active:
            return 0.0
        
        priority = [
            RelationshipStatus.CONSOLIDATED,
            RelationshipStatus.COHABITATION,
            RelationshipStatus.DATING,
        ]
        for status in priority:
            for rel in active:
                if rel.status == status:
                    return rel.days_active(rel.last_interaction)
        return 0.0

    # ==========================================
    # MÉTODOS DE RELACIONES SOCIALES
    # ==========================================
    def _get_active_relationships(self) -> List[Relationship]:
        """Filtra relaciones que están activas (no UNKNOWN ni EX_PARTNER)."""
        return [
            r for r in self._relationships
            if r.status not in (RelationshipStatus.UNKNOWN, RelationshipStatus.EX_PARTNER)
        ]

    def get_relationship_with(self, partner_id: int) -> Optional[Relationship]:
        """Obtiene la relación con un agente específico (si existe)."""
        return next(
            (r for r in self._relationships if r.partner_id == partner_id),
            None
        )

    def add_relationship(
        self,
        partner_id: int,
        status: RelationshipStatus,
        current_day: float,
        affinity: float = 0.5,
        rel_type: RelationshipType = RelationshipType.EXCLUSIVE,
    ) -> Relationship:
        """Crea o actualiza un registro de relación con otro agente."""
        existing = self.get_relationship_with(partner_id)
        if existing:
            existing.status = status
            existing.affinity = affinity
            existing.relationship_type = rel_type
            existing.last_interaction = current_day
            existing.add_event(current_day, f"status_change:{status.value}")
            return existing
        
        new_rel = Relationship(
            partner_id=partner_id,
            status=status,
            start_date=current_day,
            last_interaction=current_day,
            affinity=affinity,
            relationship_type=rel_type,
        )
        self._relationships.append(new_rel)
        return new_rel

    def update_relationship_status(
        self,
        partner_id: int,
        new_status: RelationshipStatus,
        current_day: float,
    ) -> None:
        """Actualiza el estado de una relación existente."""
        rel = self.get_relationship_with(partner_id)
        if rel:
            old_status = rel.status
            rel.status = new_status
            rel.last_interaction = current_day
            rel.add_event(
                current_day,
                f"transition:{old_status.value}->{new_status.value}"
            )

    # ==========================================
    # SISTEMA INMUNOLÓGICO AVANZADO (POR CEPA)
    # ==========================================
    def get_specific_immunity(self, pathogen: Any) -> float:
        """Calcula la resistencia combinando múltiples fuentes de inmunidad.
        
        La inmunidad se reduce si el virus ha mutado mucho desde la última infección.
        Acepta tanto un objeto Pathogen como un string de familia (legacy).
        
        Args:
            pathogen: Objeto Pathogen o string de familia.
            
        Returns:
            Nivel de inmunidad total.
        """
        # Compatibilidad legacy: si se pasa un string, usar inmunidad por familia
        if isinstance(pathogen, str):
            family = pathogen
            base_innate = max(0.1, self._genome.immunity - ((1.0 - self._emotions["energy"]) * 0.2))
            genetic_specific = self._genome.get_family_specific_immunity(family)
            acquired_bonus = self._immune_memory.get(family, 0.0)
            
            cross_immunity = 0.0
            for other_family, immunity_level in self._immune_memory.items():
                if other_family != family:
                    similarity = Pathogen.get_family_similarity(family, other_family)
                    if similarity > 0.0:
                        cross_immunity += immunity_level * similarity * 0.3
            
            total = base_innate + genetic_specific + acquired_bonus + cross_immunity
            return min(5.0, total)
        
        # Nuevo sistema: inmunidad específica por cepa
        family = pathogen.family
        
        # 1. Inmunidad innata base
        base_innate = max(0.1, self._genome.immunity - ((1.0 - self._emotions["energy"]) * 0.2))
        
        # 2. Inmunidad específica por cepa (con ajuste por mutación)
        strain_immunity = 0.0
        if hasattr(pathogen, 'pathogen_id'):
            # Inmunidad directa contra esta cepa exacta
            direct_immunity = self._strain_immunity.get(pathogen.pathogen_id, 0.0)
            
            # Inmunidad contra cepas relacionadas (misma familia, ajustada por generación)
            related_immunity = self._calculate_related_strain_immunity(pathogen)
            
            # Usar la mayor de las dos
            strain_immunity = max(direct_immunity, related_immunity)
        
        # 3. Inmunidad genética por familia
        genetic_specific = self._genome.get_family_specific_immunity(family)
        
        # 4. Inmunidad adquirida por familia (fallback)
        acquired_bonus = self._immune_memory.get(family, 0.0)
        
        # 5. Inmunidad cruzada entre familias
        cross_immunity = 0.0
        for other_family, immunity_level in self._immune_memory.items():
            if other_family != family:
                similarity = Pathogen.get_family_similarity(family, other_family)
                if similarity > 0.0:
                    cross_immunity += immunity_level * similarity * 0.3
        
        # 6. Inmunidad cruzada genética
        for other_family in Pathogen.get_related_families(family, min_similarity=0.1):
            other_genetic = self._genome.get_family_specific_immunity(other_family)
            if other_genetic > 0.0:
                similarity = Pathogen.get_family_similarity(family, other_family)
                cross_immunity += other_genetic * similarity * 0.2
        
        total_immunity = base_innate + strain_immunity + genetic_specific + acquired_bonus + cross_immunity
        return min(5.0, total_immunity)

    def _calculate_related_strain_immunity(self, pathogen: Any) -> float:
        """Calcula inmunidad contra cepas relacionadas de la misma familia.
        
        La inmunidad se reduce según la distancia genealógica (generación).
        Cada generación de diferencia reduce la inmunidad un 15%.
        
        Args:
            pathogen: Objeto Pathogen a evaluar.
            
        Returns:
            Inmunidad ajustada por distancia genealógica.
        """
        if not hasattr(pathogen, 'pathogen_id') or not hasattr(pathogen, 'generation'):
            return 0.0
        
        max_related_immunity = 0.0
        
        for strain_id, immunity in self._strain_immunity.items():
            # Solo considerar cepas de la misma familia
            if not strain_id.startswith(f"{pathogen.family}_"):
                continue
            
            # Obtener metadata de la cepa conocida
            metadata = self._strain_metadata.get(strain_id, {})
            known_generation = metadata.get("generation", 1)
            
            # Calcular distancia genealógica
            generation_diff = abs(pathogen.generation - known_generation)
            
            # La inmunidad se reduce según la distancia
            # Cada generación de diferencia reduce la inmunidad un 15%
            similarity_factor = max(0.0, 1.0 - (generation_diff * 0.15))
            
            # Inmunidad ajustada
            adjusted_immunity = immunity * similarity_factor
            
            max_related_immunity = max(max_related_immunity, adjusted_immunity)
        
        return max_related_immunity

    def infect(self, pathogen: Pathogen) -> None:
        """Infecta al agente con una cepa específica."""
        infection_state = InfectionState(pathogen)
        self._active_infections[pathogen.pathogen_id] = infection_state

        if not infection_state.is_asymptomatic:
            self._health_state = "enfermo"
            self.update_emotion("stress", 0.3)
            self.update_emotion("energy", -0.4)

    def recover(self, pathogen_id: str) -> None:
        """Elimina el patógeno y genera anticuerpos específicos por cepa."""
        if pathogen_id in self._active_infections:
            infection_state = self._active_infections.pop(pathogen_id)
            pathogen = infection_state.pathogen
            
            # Inmunidad específica por cepa (alta)
            current_strain_immunity = self._strain_immunity.get(pathogen_id, 0.0)
            self._strain_immunity[pathogen_id] = min(2.0, current_strain_immunity + 0.8)
            
            # Guardar metadata de la cepa
            self._strain_metadata[pathogen_id] = {
                "family": pathogen.family,
                "generation": pathogen.generation,
                "virulence": pathogen.virulence,
                "transmission": pathogen.transmission,
                "lethality": pathogen.lethality,
            }
            
            # Inmunidad por familia (fallback, menor)
            family_immunity = self._immune_memory.get(pathogen.family, 0.0)
            self._immune_memory[pathogen.family] = min(1.5, family_immunity + 0.4)

        if not self._active_infections:
            self._health_state = "sano"
        elif not self.is_symptomatic:
            self._health_state = "sano"

    def advance_infections(self, delta_days: float) -> None:
        """Avanza el estado de todas las infecciones activas."""
        for infection_state in self._active_infections.values():
            old_phase = infection_state.phase
            infection_state.advance(delta_days)

            if old_phase != InfectionPhase.SYMPTOMATIC and infection_state.phase == InfectionPhase.SYMPTOMATIC:
                if not infection_state.is_asymptomatic:
                    self._health_state = "enfermo"
                    self.update_emotion("stress", 0.2)
                    self.update_emotion("energy", -0.3)

    def decay_immunity(self, delta_days: float, decay_rate: float = 0.001) -> None:
        """Reduce lentamente la memoria inmunológica con el tiempo.
        
        La inmunidad específica por cepa decae más lento que la genérica.
        """
        # Decaimiento de inmunidad por cepa específica (50% más lento)
        strain_decay_factor = math.exp(-decay_rate * 0.5 * delta_days)
        for strain_id in list(self._strain_immunity.keys()):
            self._strain_immunity[strain_id] *= strain_decay_factor
            if self._strain_immunity[strain_id] < 0.01:
                del self._strain_immunity[strain_id]
                self._strain_metadata.pop(strain_id, None)
        
        # Decaimiento de inmunidad por familia (normal)
        family_decay_factor = math.exp(-decay_rate * delta_days)
        for family in list(self._immune_memory.keys()):
            self._immune_memory[family] *= family_decay_factor
            if self._immune_memory[family] < 0.01:
                del self._immune_memory[family]

    def set_health_state(self, new_state: str) -> None:
        """Mantiene compatibilidad con subsistemas antiguos de salud."""
        if new_state == "sano":
            self._active_infections.clear()
            self._health_state = "sano"

    # ==========================================
    # SISTEMA DE MOTIVACIONES
    # ==========================================
    def get_motivation(self, motivation_name: str) -> float:
        """Obtiene el nivel actual de una motivación específica."""
        return self._motivations.get(motivation_name, 0.0)

    def update_motivation(self, motivation_name: str, amount: float) -> None:
        """Modifica de forma segura el nivel de una motivación [0.0, 1.0]."""
        if motivation_name in self._motivations:
            new_value = self._motivations[motivation_name] + amount
            self._motivations[motivation_name] = max(0.0, min(1.0, new_value))

    def get_dominant_motivation(self) -> Tuple[str, float]:
        """Obtiene la motivación más fuerte y su valor."""
        if not self._motivations:
            return ('none', 0.0)
        dominant = max(self._motivations.items(), key=lambda x: x[1])
        return dominant

    def decay_motivations(self, delta_days: float, decay_rate: float = 0.005) -> None:
        """Reduce lentamente todas las motivaciones con el tiempo."""
        if not self._motivations:
            return
        decay_factor = math.exp(-decay_rate * delta_days)
        for motivation_name in list(self._motivations.keys()):
            self._motivations[motivation_name] *= decay_factor
            if self._motivations[motivation_name] < 0.05:
                self._motivations[motivation_name] = 0.05

    # ==========================================
    # MÉTODOS DE COMPORTAMIENTO
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
        """Vincula al agente con su nueva pareja legal.
        
        NOTA: Este método legacy ahora crea una relación CONSOLIDATED
        en el nuevo sistema de relaciones.
        """
        self._partner_id = partner_id
        self._marital_status = "casado"
        
        self.add_relationship(
            partner_id=partner_id,
            status=RelationshipStatus.CONSOLIDATED,
            current_day=0.0,
            affinity=0.7,
            rel_type=RelationshipType.EXCLUSIVE,
        )
        
        self.update_emotion("happiness", 0.4)

    def register_divorce(self) -> None:
        """Rompe el vínculo conyugal y aplica penalizaciones psicológicas."""
        old_partner = self._partner_id
        self._partner_id = None
        self._marital_status = "divorciado"
        
        if old_partner:
            rel = self.get_relationship_with(old_partner)
            if rel:
                rel.status = RelationshipStatus.EX_PARTNER
                rel.add_event(0.0, "divorce")
        
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
        
        partner_id = self.partner_id
        if partner_id:
            rel = self.get_relationship_with(partner_id)
            if rel:
                rel.shared_children += 1

    def add_biological_child(self) -> None:
        """Registra un éxito evolutivo (hijo biológico) y asume su crianza inicial."""
        self._biological_children_count += 1
        self.add_child()

    def add_relationship_days(self, days: float) -> None:
        """Suma tiempo al contador de longevidad del matrimonio (legacy)."""
        pass

    def set_parents(self, mother_id: int, father_id: Optional[int] = None) -> None:
        """Asigna exclusivamente el linaje biológico en el momento de nacer."""
        self._mother_id = mother_id
        self._father_id = father_id
        self._parents = [mother_id]
        if father_id is not None:
            self._parents.append(father_id)

    def add_adoptive_parent(self, parent_id: int) -> None:
        """Registra un vínculo de filiación legal y social sin alterar la genética."""
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