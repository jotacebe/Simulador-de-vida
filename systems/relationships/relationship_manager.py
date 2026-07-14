"""Gestor de evolución relacional basado en variables emocionales.

Este sistema reemplaza el modelo de máquina de estados finitos por un
modelo continuo donde:
- Las variables emocionales (trust, attraction, etc.) cambian cada tick
- El estado relacional es una consecuencia de las variables
- Un clasificador determina el estado actual

Esto permite comportamientos emergentes más naturales:
- Saltos de estado (de amigo a novio sin pasar por interés romántico)
- Múltiples estados simultáneos
- Relaciones que evolucionan orgánicamente
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
    RelationshipClassifier,
    RelationshipStatus,
    RelationshipType,
    is_orientation_compatible,
)


class RelationshipManager:
    """Orquesta la evolución continua de relaciones entre agentes."""

    def __init__(
        self,
        config: SimulationConfig,
        compatibility_engine: CompatibilityEngine,
    ) -> None:
        self.config = config
        self.rel_cfg = config.relationships
        self.compatibility = compatibility_engine
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Tracking de relaciones creadas este tick para evitar duplicados
        self._relationships_created_this_tick: Set[tuple] = set()

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Evalúa y actualiza relaciones de todos los agentes vivos."""
        current_day = getattr(state, 'world_days_elapsed', 0.0)
        
        # Limpiar tracking al inicio de cada tick
        self._relationships_created_this_tick.clear()
        
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue
            
            # 1. Actualizar variables emocionales de relaciones existentes
            self._update_emotional_variables(person, state, pending, current_day, delta_days)
            
            # 2. Detectar nuevas relaciones potenciales
            self._detect_new_relationships(person, state, current_day, pending, context)

    def _update_emotional_variables(
        self,
        person: Any,
        state: WorldState,
        pending: PendingChanges,
        current_day: float,
        delta_days: float,
    ) -> None:
        """Actualiza las variables emocionales de todas las relaciones del agente."""
        for rel in person.relationships:
            if rel.status == RelationshipStatus.EX_PARTNER:
                continue
            
            partner = state.get_person_by_id(rel.partner_id)
            if not partner or partner.entity_id in pending.deaths:
                continue
            
            # Guardar estado anterior para detectar cambios
            old_status = RelationshipClassifier.classify(rel)
            
            # Calcular calidad de interacción basada en proximidad y afinidad
            distance = math.hypot(person.x - partner.x, person.y - partner.y)
            proximity = max(0.0, 1.0 - (distance / 50.0))
            
            # NUEVO: Interacción virtual para relaciones existentes
            # Si ya tienen una relación establecida, pueden interactuar incluso a distancia
            relationship_strength = (rel.trust + rel.attachment + rel.familiarity) / 300.0
            virtual_interaction_bonus = relationship_strength * 0.3
            
            # Calidad de interacción: combina proximidad con bonus de relación existente
            # Si están cerca, la interacción es positiva
            # Si están lejos pero tienen relación fuerte, hay interacción virtual
            if proximity > 0.3:
                interaction_quality = proximity * 0.5 + virtual_interaction_bonus
            elif rel.familiarity > 30:  # Si ya se conocen bien
                interaction_quality = virtual_interaction_bonus
            else:
                interaction_quality = 0.0
            
            # Actualizar variables emocionales
            rel.update_emotional_variables(delta_days, interaction_quality, proximity)
            
            # Recalcular estado usando el clasificador
            new_status = RelationshipClassifier.classify(rel)
            
            # Loguear si el estado cambió
            if new_status != old_status and person.entity_id < partner.entity_id:
                self._log_status_change(person, partner, old_status, new_status, rel)

    def _log_status_change(
        self,
        p1: Any,
        p2: Any,
        old_status: RelationshipStatus,
        new_status: RelationshipStatus,
        rel: Relationship,
    ) -> None:
        """Registra el cambio de estado en el log."""
        # Solo loguear transiciones significativas
        significant_transitions = {
            (RelationshipStatus.UNKNOWN, RelationshipStatus.ACQUAINTANCE): "🤝",
            (RelationshipStatus.ACQUAINTANCE, RelationshipStatus.FRIENDSHIP): "👥",
            (RelationshipStatus.FRIENDSHIP, RelationshipStatus.ROMANTIC_INTEREST): "💕",
            (RelationshipStatus.ROMANTIC_INTEREST, RelationshipStatus.DATING): "❤️",
            (RelationshipStatus.DATING, RelationshipStatus.COHABITATION): "🏠",
            (RelationshipStatus.COHABITATION, RelationshipStatus.CONSOLIDATED): "💍",
        }
        
        transition_key = (old_status, new_status)
        if transition_key in significant_transitions:
            emoji = significant_transitions[transition_key]
            self.logger.info(
                "%s Agente %s y %s: %s → %s (trust: %.1f, attraction: %.1f, commitment: %.1f)",
                emoji,
                p1.entity_id,
                p2.entity_id,
                old_status.value,
                new_status.value,
                rel.trust,
                rel.attraction,
                rel.commitment,
            )
        elif new_status == RelationshipStatus.EX_PARTNER:
            self.logger.info(
                "💔 Ruptura: Agente %s y %s (trust: %.1f, conflict: %.1f, commitment: %.1f, attachment: %.1f)",
                p1.entity_id,
                p2.entity_id,
                rel.trust,
                rel.conflict,
                rel.commitment,
                rel.attachment,
            )

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
            classified_status = RelationshipClassifier.classify(rel)
            if classified_status in (
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
            
            # Solo el agente con menor ID procesa para evitar duplicados
            if person.entity_id >= other.entity_id:
                continue
            
            # Verificar que no exista la relación
            if person.get_relationship_with(other.entity_id):
                continue
            
            # Verificar tracking
            relationship_key = tuple(sorted([person.entity_id, other.entity_id]))
            if relationship_key in self._relationships_created_this_tick:
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
                    if friend_rel:
                        friend_status = RelationshipClassifier.classify(friend_rel)
                        if friend_status in (
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
                # Crear relación bidireccional con variables emocionales iniciales
                affinity = self.compatibility.calculate_compatibility(person, other)
                
                # Inicializar con familiaridad baja (acaban de conocerse)
                new_rel = Relationship(
                    partner_id=other.entity_id,
                    status=RelationshipStatus.UNKNOWN,
                    start_date=current_day,
                    last_interaction=current_day,
                    affinity=affinity,
                    relationship_type=RelationshipType.EXCLUSIVE,
                )
                # Familiaridad inicial baja
                new_rel.familiarity = 10.0
                # Respeto básico
                new_rel.respect = 30.0
                
                person._relationships.append(new_rel)
                
                # Crear relación inversa
                reverse_rel = Relationship(
                    partner_id=person.entity_id,
                    status=RelationshipStatus.UNKNOWN,
                    start_date=current_day,
                    last_interaction=current_day,
                    affinity=affinity,
                    relationship_type=RelationshipType.EXCLUSIVE,
                )
                reverse_rel.familiarity = 10.0
                reverse_rel.respect = 30.0
                
                other._relationships.append(reverse_rel)
                
                # Marcar como creada este tick
                self._relationships_created_this_tick.add(relationship_key)
                
                self.logger.debug(
                    "👋 Día %.0f: Agente %s conoce a %s (distancia: %.1f, afinidad: %.2f)",
                    current_day, person.entity_id, other.entity_id, distance, affinity
                )