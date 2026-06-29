"""Módulo responsable de la reasignación familiar de menores sin tutores vivos.

Identifica menores huérfanos y los asigna a las familias más idóneas del ecosistema
utilizando un algoritmo de utilidad (Utility AI) que evalúa selección de parentesco (Kin Selection),
factores genéticos, emocionales, de salud y proximidad espacial, garantizando
una diferencia de edad mínima coherente y límites de bienestar (Hard Limits).
"""

from __future__ import annotations

import logging
import math
from typing import Any, List, Set

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from entities.person.person import Person
from systems.environment.environment_context import EnvironmentContext


class AdoptionSystem:
    """Identifica huérfanos y asigna familias mediante procesos de filtrado estricto."""

    def __init__(self, config: SimulationConfig, ancestry_queries: Any = None) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada.

        Args:
            config: Configuración maestra de la simulación.
            ancestry_queries: Fachada de consultas genealógicas para detectar familiares.
        """
        self.config = config
        self.ancestry_queries = ancestry_queries
        self.logger = logging.getLogger("AdoptionSystem")

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Ejecuta el ciclo de adopciones con filtrado de idoneidad estricto."""
        adoptions_cfg = self.config.adoptions
        all_persons = state.get_all_persons()

        # 1. DETECCIÓN DE HUÉRFANOS
        orphans: List[Person] = []
        for person in all_persons:
            if self._is_eligible_orphan(person, state, pending, adoptions_cfg):
                orphans.append(person)

        if not orphans:
            return

        # 2. FILTRADO DE FAMILIAS ELEGIBLES (Hard Limits)
        eligible_parents: List[Person] = []
        seen_couples: Set[int] = set()

        for person in all_persons:
            # Evitar procesar muertos o cónyuges de familias ya validadas
            if person.entity_id in pending.deaths or person.entity_id in seen_couples:
                continue

            # FILTRO A: Condiciones base (Matrimonio y edad mínima)
            is_old_enough = person.age >= adoptions_cfg.min_adoptive_age_days
            is_married = person.marital_status == "casado" and person.partner_id is not None
            if not (is_old_enough and is_married):
                continue

            # FILTRO B: Límite de carga familiar configurada
            if person.children_count >= adoptions_cfg.max_children_for_adoption:
                continue

            # FILTRO C: Salud y Bienestar Clínico (Hard Limits reales)
            if person.is_sick:
                continue

            # Si el estrés fisiológico es crítico, se rechaza como candidato
            if person.emotions.get("stress", 0.0) > 0.7:
                continue

            # FILTRO D: Entorno saturado (usando la densidad local para evitar hacinamiento)
            local_pressure = context.get_local_pressure(person.x, person.y)
            if local_pressure > 0.8:  
                continue

            # Si supera todos los filtros, es una familia estructuralmente apta
            eligible_parents.append(person)
            if person.partner_id is not None:
                seen_couples.add(person.partner_id)

        if not eligible_parents:
            return

        # 3. ORDENACIÓN DINÁMICA Y ASIGNACIÓN TRANSACCIONAL
        # Leemos la diferencia de edad mínima, por defecto 15 años (5475 días)
        min_age_diff = getattr(adoptions_cfg, 'min_age_difference_days', 5475.0)

        for orphan in orphans:
            if not eligible_parents:
                break  # Se agotaron las familias aptas en el mundo

            # Descartamos candidatos cuya diferencia de edad con ESTE menor no sea viable
            valid_candidates = [
                p for p in eligible_parents
                if (p.age - orphan.age) >= min_age_diff
            ]

            if not valid_candidates:
                continue

            # Ordenamos a los candidatos aptos mediante el algoritmo de Utility AI
            valid_candidates.sort(
                key=lambda p: self._calculate_suitability(p, orphan, self.ancestry_queries, context),
                reverse=True
            )

            new_parent = valid_candidates[0]
            
            # Lo retiramos de la bolsa global para que no acapare múltiples adopciones en el mismo tick
            eligible_parents.remove(new_parent)
            
            new_partner = state.get_person_by_id(new_parent.partner_id) if new_parent.partner_id else None

            # Registramos las mutaciones en el búfer transaccional
            pending.register_adoption(
                child_id=orphan.entity_id,
                parent_a=new_parent.entity_id,
                parent_b=new_partner.entity_id if new_partner else None
            )
            pending.register_movement(orphan.entity_id, new_parent.x, new_parent.y)

            # =================================================================
            # SHOCK EMOCIONAL INICIAL (Adaptación psicológica del menor)
            # =================================================================
            if not hasattr(orphan, 'memory') or orphan.memory is None:
                orphan.memory = {}
            
            # Impronta de trauma en memoria (será disipada por el CognitiveMemorySystem)
            orphan.memory["trauma_adoption"] = 1.0

            # Impacto directo a los sistemas fisiológicos usando el setter seguro
            orphan.update_emotion("stress", 0.6)
            orphan.update_emotion("happiness", -0.5)

            self.logger.info(
                "Adopción registrada: Menor %s asignado a familia %s (Dif. Edad: %.1f días, Score: %.2f)",
                orphan.entity_id,
                new_parent.entity_id,
                (new_parent.age - orphan.age),
                self._calculate_suitability(new_parent, orphan, self.ancestry_queries, context)
            )

    def _is_eligible_orphan(self, person: Person, state: WorldState, pending: PendingChanges, cfg: Any) -> bool:
        """Valida si un individuo cumple todos los requisitos legales para ser adoptable."""
        # Filtro 1: No procesar entidades que están muriendo
        if person.entity_id in pending.deaths:
            return False
            
        # Filtro 2: Comprobación de que no ha sido adoptado previamente
        if len(person.adoptive_parents) > 0:
            return False
            
        # Filtro 3: Es menor de edad según configuración
        if person.age > cfg.max_orphan_age_days:
            return False

        # Filtro 4: No le queda ningún progenitor biológico vivo
        father_alive = person.father_id is not None and state.get_person_by_id(person.father_id) is not None
        mother_alive = person.mother_id is not None and state.get_person_by_id(person.mother_id) is not None

        # Debe haber tenido algún padre registrado y estar ambos muertos
        return (person.father_id is not None or person.mother_id is not None) and not father_alive and not mother_alive

    def _calculate_suitability(
        self, 
        parent: Person, 
        orphan: Person, 
        ancestry: Any, 
        context: EnvironmentContext
    ) -> float:
        """Calcula el índice de idoneidad de un adoptante usando Múltiples Criterios (Utility AI)."""
        score = 0.0

        # A. SELECCIÓN DE PARENTESCO (Kin Selection)
        if ancestry is not None:
            kinship_degree = ancestry.get_kinship_degree(parent.entity_id, orphan.entity_id)
            if kinship_degree > 0:
                # Tremenda bonificación por consanguinidad (Supera los obstáculos espaciales)
                score += (100.0 / kinship_degree)

        # B. COMPATIBILIDAD ESPACIAL (Distancia y Presión Ambiental)
        distance = math.sqrt((parent.x - orphan.x)**2 + (parent.y - orphan.y)**2)
        score -= (distance * 0.2)  # A más distancia física, menos puntos
        
        # Penalización fuerte si la familia vive en zona con presión alta (por debajo del Hard Limit)
        local_pressure = context.get_local_pressure(parent.x, parent.y)
        score -= (local_pressure * 50.0)

        # C. FACTORES FENOTÍPICOS Y DE SALUD
        score += parent.effective_sociability * 10.0

        stress = parent.emotions.get("stress", 0.0)
        happiness = parent.emotions.get("happiness", 0.5)
        
        score -= (stress * 30.0)      # Penalizamos fuertemente el estrés residual
        score += (happiness * 20.0)   # Premiamos un entorno familiar feliz

        score -= (parent.children_count * 5.0)  # Premiamos a familias con menos hijos actualmente

        # D. ESTABILIDAD MATRIMONIAL Y VITAL
        stability_years = parent.relationship_days / 365.0
        score += min(15.0, stability_years * 1.5)

        if parent.is_senior:
            score -= 10.0  # Penalización leve a ancianos para asegurar maximizar los años de cuidado futuro

        return score