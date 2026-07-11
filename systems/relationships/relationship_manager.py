"""Gestor de transiciones relacionales y ciclo de vida.

Maneja la evolución de estados relacionales (progresiva y recesiva),
decaimiento por inactividad, y permite impulsos de libre albedrío
para saltos de estado no convencionales.

Este es el sistema central que reemplaza a MarriageSystem y
RelationshipSystem en la gestión de vínculos entre agentes.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Dict, List, Optional, Set

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext
from systems.relationships.compatibility_engine import CompatibilityEngine
from systems.relationships.relationship_model import (
    Relationship,
    RelationshipStatus,
    RelationshipType,
    is_orientation_compatible,
)


class RelationshipManager:
    """Orquesta la evolución y transición de relaciones entre agentes."""

    def __init__(
        self,
        config: SimulationConfig,
        compatibility_engine: CompatibilityEngine,
    ) -> None:
        self.config = config
        self.rel_cfg = config.relationships
        self.compatibility = compatibility_engine
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Evalúa y actualiza relaciones de todos los agentes vivos."""
        current_day = getattr(state, 'world_days_elapsed', 0.0)
        
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue
            
            # 1. Decaimiento por inactividad
            self._decay_inactive_relationships(person, current_day, delta_days)
            
            # 2. Evaluar transiciones (progresivas y recesivas)
            self._evaluate_transitions(person, state, current_day, pending)
            
            # 3. Detectar nuevas relaciones potenciales
            self._detect_new_relationships(person, state, current_day, pending, context)

    def _decay_inactive_relationships(
        self,
        person: Any,
        current_day: float,
        delta_days: float,
    ) -> None:
        """Decae relaciones por falta de interacción."""
        for rel in person.relationships:
            # ACQUAINTANCE, UNKNOWN y EX_PARTNER no pueden decaer
            if rel.status in (
                RelationshipStatus.UNKNOWN,
                RelationshipStatus.EX_PARTNER,
                RelationshipStatus.ACQUAINTANCE,
            ):
                continue
            
            days_inactive = rel.days_since_interaction(current_day)
            
            # Decaimiento gradual según estado
            if rel.status == RelationshipStatus.CONSOLIDATED:
                threshold = self.rel_cfg.max_days_unknown * 3.0
            elif rel.status == RelationshipStatus.COHABITATION:
                threshold = self.rel_cfg.max_days_unknown * 2.0
            elif rel.status == RelationshipStatus.DATING:
                threshold = self.rel_cfg.max_days_unknown
            else:
                threshold = self.rel_cfg.max_days_unknown * 0.5
            
            if days_inactive > threshold:
                new_status = self._get_recessive_status(rel.status)
                if new_status != rel.status:
                    rel.status = new_status
                    rel.add_event(current_day, f"decay:{new_status.value}")
                    self.logger.debug(
                        "🕳️ Agente %s: relación con %s decae a %s (inactividad: %.0f días)",
                        person.entity_id,
                        rel.partner_id,
                        new_status.value,
                        days_inactive,
                    )

    def _evaluate_transitions(
        self,
        person: Any,
        state: WorldState,
        current_day: float,
        pending: PendingChanges,
    ) -> None:
        """Evalúa transiciones de estado basadas en afinidad y tiempo."""
        for rel in person.relationships:
            if rel.status == RelationshipStatus.EX_PARTNER:
                continue
            
            partner = state.get_person_by_id(rel.partner_id)
            if not partner or partner.entity_id in pending.deaths:
                continue
            
            # Calcular afinidad actual
            current_affinity = self.compatibility.calculate_compatibility(person, partner)
            rel.affinity = current_affinity
            
            # TRANSICIÓN HACIA ATRÁS (Recesiva)
            if self._try_recess_transition(person, rel, current_day):
                continue
            
            # TRANSICIÓN HACIA ADELANTE (Progresiva)
            self._try_progress_transition(person, rel, partner, current_day)

    def _try_progress_transition(
        self,
        p1: Any,
        rel: Relationship,
        p2: Any,
        current_day: float,
    ) -> bool:
        """Intenta avanzar un estado relacional."""
        cfg = self.rel_cfg
        affinity = rel.affinity
        days_active = rel.days_active(current_day)
        
        # Probabilidad base de transición
        transition_chance = affinity * 0.08
        
        # UNKNOWN → ACQUAINTANCE
        if rel.status == RelationshipStatus.UNKNOWN:
            distance = abs(p1.x - p2.x) + abs(p1.y - p2.y)
            if distance < 20 and random.random() < 0.15:
                rel.status = RelationshipStatus.ACQUAINTANCE
                rel.add_event(current_day, "met")
                # CORRECCIÓN: Loguear solo una vez por par (ID menor)
                if p1.entity_id < p2.entity_id:
                    self.logger.info(
                        "🤝 Agente %s y %s se conocen (distancia: %d)",
                        p1.entity_id, p2.entity_id, distance
                    )
                return True
        
        # ACQUAINTANCE → FRIENDSHIP
        elif rel.status == RelationshipStatus.ACQUAINTANCE:
            if affinity > 0.45 and random.random() < transition_chance:
                rel.status = RelationshipStatus.FRIENDSHIP
                rel.add_event(current_day, "became_friends")
                if p1.entity_id < p2.entity_id:
                    self.logger.info(
                        "👥 Agente %s y %s se hacen amigos (afinidad: %.2f)",
                        p1.entity_id, p2.entity_id, affinity
                    )
                return True
        
        # FRIENDSHIP → ROMANTIC_INTEREST
        elif rel.status == RelationshipStatus.FRIENDSHIP:
            if affinity > cfg.min_affinity_for_dating and random.random() < transition_chance * 0.7:
                rel.status = RelationshipStatus.ROMANTIC_INTEREST
                rel.add_event(current_day, "romantic_interest")
                if p1.entity_id < p2.entity_id:
                    self.logger.info(
                        "💕 Agente %s y %s tienen interés romántico (afinidad: %.2f)",
                        p1.entity_id, p2.entity_id, affinity
                    )
                return True
        
        # ROMANTIC_INTEREST → DATING
        elif rel.status == RelationshipStatus.ROMANTIC_INTEREST:
            if affinity > cfg.min_affinity_for_dating and random.random() < transition_chance:
                rel.status = RelationshipStatus.DATING
                rel.add_event(current_day, "started_dating")
                if p1.entity_id < p2.entity_id:
                    self.logger.info(
                        "❤️ Agente %s y %s comienzan a salir (afinidad: %.2f)",
                        p1.entity_id, p2.entity_id, affinity
                    )
                return True
        
        # DATING → COHABITATION
        elif rel.status == RelationshipStatus.DATING:
            if (affinity > cfg.min_affinity_for_cohabitation and
                days_active > cfg.min_days_for_cohabitation and
                random.random() < transition_chance * 0.4):
                rel.status = RelationshipStatus.COHABITATION
                rel.add_event(current_day, "moved_in_together")
                if p1.entity_id < p2.entity_id:
                    self.logger.info(
                        "🏠 Agente %s y %s conviven (afinidad: %.2f, días: %.0f)",
                        p1.entity_id, p2.entity_id, affinity, days_active
                    )
                return True
        
        # COHABITATION → CONSOLIDATED
        elif rel.status == RelationshipStatus.COHABITATION:
            if (affinity > cfg.min_affinity_for_consolidated and
                days_active > cfg.min_days_for_consolidated and
                random.random() < transition_chance * 0.3):
                rel.status = RelationshipStatus.CONSOLIDATED
                rel.add_event(current_day, "consolidated_relationship")
                if p1.entity_id < p2.entity_id:
                    self.logger.info(
                        "💍 Agente %s y %s consolidan relación (afinidad: %.2f, días: %.0f)",
                        p1.entity_id, p2.entity_id, affinity, days_active
                    )
                return True
        
        return False

    def _try_recess_transition(
        self,
        p1: Any,
        rel: Relationship,
        current_day: float,
    ) -> bool:
        """Maneja degradación o ruptura de relaciones."""
        cfg = self.rel_cfg
        affinity = rel.affinity
        
        # Protección de "luna de miel"
        if rel.status == RelationshipStatus.CONSOLIDATED:
            days_active = rel.days_active(current_day)
            if days_active < 365.0:
                return False
        
        # Ruptura formal: afinidad muy baja
        if affinity < cfg.breakup_affinity_threshold:
            if rel.status not in (
                RelationshipStatus.EX_PARTNER,
                RelationshipStatus.UNKNOWN,
                RelationshipStatus.ACQUAINTANCE,
            ):
                old_status = rel.status
                rel.status = RelationshipStatus.EX_PARTNER
                rel.add_event(current_day, f"breakup_from:{old_status.value}")
                # CORRECCIÓN: Loguear solo una vez por par
                if p1.entity_id < rel.partner_id:
                    self.logger.info(
                        "💔 Ruptura: %s y %s (afinidad: %.2f, estado previo: %s)",
                        p1.entity_id,
                        rel.partner_id,
                        affinity,
                        old_status.value,
                    )
                return True
        
        # Degradación: COHABITATION/CONSOLIDATED → DATING
        if affinity < cfg.casual_affinity_threshold:
            if rel.status in (RelationshipStatus.COHABITATION, RelationshipStatus.CONSOLIDATED):
                rel.status = RelationshipStatus.DATING
                rel.add_event(current_day, "degrade:dating")
                return True
        
        # Degradación: DATING/ROMANTIC_INTEREST → FRIENDSHIP
        if affinity < cfg.friendship_recovery_threshold:
            if rel.status in (RelationshipStatus.DATING, RelationshipStatus.ROMANTIC_INTEREST):
                rel.status = RelationshipStatus.FRIENDSHIP
                rel.add_event(current_day, "degrade:friendship")
                return True
        
        return False

    def _detect_new_relationships(
        self,
        person: Any,
        state: WorldState,
        current_day: float,
        pending: PendingChanges,
        context: EnvironmentContext,
    ) -> None:
        """Detecta agentes cercanos para iniciar relaciones UNKNOWN."""
        detection_radius = 35.0
        
        # Obtener amigos de persona para calcular triángulos sociales
        friends_of_person: Set[int] = set()
        for rel in person.relationships:
            if rel.status in (
                RelationshipStatus.FRIENDSHIP,
                RelationshipStatus.ROMANTIC_INTEREST,
                RelationshipStatus.DATING,
                RelationshipStatus.COHABITATION,
                RelationshipStatus.CONSOLIDATED,
            ):
                friends_of_person.add(rel.partner_id)
        
        for other in state.get_all_persons():
            if other.entity_id == person.entity_id:
                continue
            if other.entity_id in pending.deaths:
                continue
            
            # CORRECCIÓN CRÍTICA: Solo procesar cada par una vez (ID menor procesa)
            if person.entity_id >= other.entity_id:
                continue
            
            # Verificación de seguridad adicional
            if person.get_relationship_with(other.entity_id):
                continue
            if other.get_relationship_with(person.entity_id):
                continue
            
            # Verificar proximidad física
            distance = math.hypot(person.x - other.x, person.y - other.y)
            if distance > detection_radius:
                continue
            
            # Verificar compatibilidad de orientación
            orientation_score = is_orientation_compatible(
                person.sexual_orientation,
                other.sexual_orientation,
                tolerance=self.rel_cfg.orientation_tolerance,
            )
            if orientation_score <= 0.0:
                continue
            
            # Calcular probabilidad base
            base_chance = 0.02 * (1.0 - distance / detection_radius)
            
            # Efecto de triángulos sociales
            triangle_bonus = 0.0
            common_friends = 0
            
            for friend_id in friends_of_person:
                friend = state.get_person_by_id(friend_id)
                if friend:
                    friend_rel = friend.get_relationship_with(other.entity_id)
                    if friend_rel and friend_rel.status in (
                        RelationshipStatus.FRIENDSHIP,
                        RelationshipStatus.ROMANTIC_INTEREST,
                        RelationshipStatus.DATING,
                        RelationshipStatus.COHABITATION,
                        RelationshipStatus.CONSOLIDATED,
                    ):
                        common_friends += 1
            
            if common_friends > 0:
                triangle_bonus = base_chance * (common_friends * 0.5)
            
            meet_chance = base_chance + triangle_bonus
            
            if random.random() < meet_chance:
                # Crear relación bidireccional
                affinity = self.compatibility.calculate_compatibility(person, other)
                
                person.add_relationship(
                    partner_id=other.entity_id,
                    status=RelationshipStatus.UNKNOWN,
                    current_day=current_day,
                    affinity=affinity,
                )
                
                other.add_relationship(
                    partner_id=person.entity_id,
                    status=RelationshipStatus.UNKNOWN,
                    current_day=current_day,
                    affinity=affinity,
                )
                
                self.logger.debug(
                    "👋 Día %.0f: Agente %s conoce a %s (distancia: %.1f, afinidad: %.2f)",
                    current_day, person.entity_id, other.entity_id, distance, affinity
                )

    def _get_recessive_status(self, current: RelationshipStatus) -> RelationshipStatus:
        """Obtiene el estado recesivo siguiente."""
        hierarchy = [
            RelationshipStatus.CONSOLIDATED,
            RelationshipStatus.COHABITATION,
            RelationshipStatus.DATING,
            RelationshipStatus.ROMANTIC_INTEREST,
            RelationshipStatus.CASUAL,
            RelationshipStatus.FRIENDSHIP,
            RelationshipStatus.ACQUAINTANCE,
            RelationshipStatus.UNKNOWN,
        ]
        
        try:
            idx = hierarchy.index(current)
            if idx < len(hierarchy) - 1:
                return hierarchy[idx + 1]
        except ValueError:
            pass
        
        return RelationshipStatus.UNKNOWN