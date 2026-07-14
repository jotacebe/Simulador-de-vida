"""Módulo responsable de la gestión epidemiológica y evolución de patógenos.

Implementa un modelo de propagación espacial con fases de infección:
- Expuesto → Incubando → Contagioso → Sintomático → Recuperándose

NUEVO: Integración con el RelationshipExperienceEngine para que las 
enfermedades y recuperaciones afecten las relaciones (cuidado, duelo, etc.).
"""

import random
import math
import logging
from collections import defaultdict
from typing import Dict, Set, Optional, Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig
from systems.diseases.pathogen import Pathogen, InfectionPhase

# NUEVO: Importaciones para el sistema de relaciones
from systems.relationships.relationship_model import (
    RelationshipEvent,
    RelationshipEventType,
    RelationshipStatus,
)
from systems.relationships.relationship_experience_engine import RelationshipExperienceEngine


class DiseaseSystem:
    """Motor epidemiológico espacial (Variantes, Inmunidad y Contagio focal)."""

    def __init__(
        self, 
        config: SimulationConfig,
        relationship_engine: Optional[RelationshipExperienceEngine] = None,
    ) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config
        self.relationship_engine = relationship_engine  # NUEVO: Inyección de dependencia
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Procesa la propagación epidemiológica y recuperación de enfermedades."""
        dis_cfg = self.config.diseases
        sector_size = self.config.environment.sector_size
        
        current_day = getattr(state, 'world_days_elapsed', 0.0)
        
        # Mapeo espacial de la carga viral en el tick actual
        pathogen_map = defaultdict(list)

        # =================================================================
        # FASE 0: DECAIMIENTO DE INMUNIDAD
        # =================================================================
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue
            
            if hasattr(person, 'decay_immunity'):
                person.decay_immunity(delta_days, decay_rate=0.0003)

        # =================================================================
        # FASE 1: PROGRESIÓN DE INFECCIONES Y RECUPERACIÓN
        # =================================================================
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue
            
            # Avanzar todas las infecciones activas
            if hasattr(person, 'advance_infections'):
                person.advance_infections(delta_days)
            
            # Procesar cada infección activa
            for path_id, infection_state in list(person.active_infections.items()):
                pathogen = infection_state.pathogen
                
                # Aplicar letalidad durante fase sintomática
                if infection_state.phase == InfectionPhase.SYMPTOMATIC:
                    lethality_risk = pathogen.lethality * 0.01 * delta_days
                    total_immunity = person.get_specific_immunity(pathogen)
                    lethality_risk = lethality_risk / max(0.1, total_immunity)
                    
                    if random.random() < lethality_risk:
                        pending.register_death(
                            person.entity_id,
                            f"Sepsis / Fallo multiorgánico por {pathogen.pathogen_id}"
                        )
                        
                        # NUEVO: Notificar a las relaciones cercanas sobre la muerte
                        self._notify_partner_death(person, state, pending, current_day)
                        
                        self.logger.debug(
                            "💀 Agente %s falleció por %s (letalidad: %.2f, inmunidad: %.2f)",
                            person.entity_id,
                            pathogen.pathogen_id,
                            pathogen.lethality,
                            total_immunity,
                        )
                        continue
                
                # Solo intentar recuperación si está en fase de recuperación o sintomática
                if infection_state.phase in (InfectionPhase.RECOVERING, InfectionPhase.SYMPTOMATIC):
                    total_immunity = person.get_specific_immunity(pathogen)
                    
                    daily_recovery_rate = (dis_cfg.base_recovery_chance * 3.0 * total_immunity) / max(0.1, pathogen.virulence)
                    recovery_chance = 1.0 - math.exp(-daily_recovery_rate * delta_days)
                    
                    if random.random() < recovery_chance:
                        # RECUPERACIÓN EXITOSA
                        pending.register_recovery(person.entity_id, path_id)
                        
                        # NUEVO: Notificar a las relaciones cercanas sobre el cuidado/recuperación
                        self._notify_recovery_care(person, state, pending, current_day, pathogen)
                        
                        # Registrar recuerdo de enfermedad superada
                        intensity = min(1.0, 0.3 + (pathogen.virulence * 0.6))
                        
                        CognitiveMemorySystem.add_memory(
                            person=person,
                            mem_type=CognitiveMemorySystem.TYPE_DISEASE,
                            target_id=pathogen.pathogen_id,
                            intensity=intensity,
                            valence=-1,
                            context="recuperacion",
                            current_day=current_day,
                            pending=pending,
                        )
                        
                        self.logger.debug(
                            "🛡️ Agente %s superó enfermedad %s (fase: %s, asintomático: %s)",
                            person.entity_id,
                            pathogen.pathogen_id,
                            infection_state.phase.value,
                            infection_state.is_asymptomatic,
                        )
                        continue
                
                # Si está en fase contagiosa o sintomática, contribuir a la carga viral del sector
                if infection_state.is_contagious():
                    sector = (person.x // sector_size, person.y // sector_size)
                    effective_transmission = pathogen.transmission * infection_state.get_transmission_multiplier()
                    pathogen_map[sector].append((pathogen, effective_transmission))
                
                # Riesgo de Mutación (solo si está en fase sintomática o contagiosa)
                if infection_state.phase in (InfectionPhase.CONTAGIOUS, InfectionPhase.SYMPTOMATIC):
                    mutation_chance = 0.005 * delta_days
                    if random.random() < mutation_chance:
                        new_variant = pathogen.mutate()
                        
                        # REEMPLAZAR CEPA ANTERIOR
                        for old_path_id in list(person.active_infections.keys()):
                            if old_path_id.startswith(f"{pathogen.family}_"):
                                pending.register_recovery(person.entity_id, old_path_id)
                        
                        # Infectar con la nueva variante
                        pending.register_infection(person.entity_id, new_variant)
                        
                        self.logger.debug(
                            "🦠 Mutación: %s reemplaza a %s en Agente %s",
                            new_variant.pathogen_id,
                            pathogen.pathogen_id,
                            person.entity_id,
                        )

        # =================================================================
        # FASE 2: CONTAGIOS LOCALES Y BROTES ESPONTÁNEOS
        # =================================================================
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue
            
            sector = (person.x // sector_size, person.y // sector_size)
            local_pathogens = pathogen_map.get(sector, [])
            
            agent_infections_this_tick: Set[str] = set()
            
            family_counts = defaultdict(int)
            for pid in person.active_infections.keys():
                family = pid.split('_')[0]
                family_counts[family] += 1
            
            # Contagio cruzado
            for pathogen, _ in local_pathogens:
                if pathogen.pathogen_id in person.active_infections:
                    continue
                
                if pathogen.pathogen_id in agent_infections_this_tick:
                    continue
                
                if family_counts[pathogen.family] >= 2:
                    continue
                
                total_immunity = person.get_specific_immunity(pathogen)
                
                if total_immunity > 1.5:
                    continue
                
                crowding_pressure = context.get_local_pressure(person.x, person.y)
                
                immunity_factor = min(1.0, total_immunity / 2.0)
                base_rate = (pathogen.transmission * max(1.0, crowding_pressure)) / max(0.5, total_immunity)
                daily_transmission_rate = base_rate * (1.0 - immunity_factor * 0.8)
                infection_chance = 1.0 - math.exp(-daily_transmission_rate * delta_days)
                
                if random.random() < infection_chance:
                    pending.register_infection(person.entity_id, pathogen)
                    agent_infections_this_tick.add(pathogen.pathogen_id)
                    family_counts[pathogen.family] += 1
            
            # Brote espontáneo
            outbreak_chance = 1.0 - math.exp(-(dis_cfg.base_outbreak_chance / 100.0) * delta_days)
            if random.random() < outbreak_chance:
                familia_random = random.choice(["Influenza", "Coronavirus", "Poxvirus", "Bacteriofago_X"])
                patient_zero_virus = Pathogen.create_random_variant(familia_random)
                
                if patient_zero_virus.pathogen_id not in person.active_infections:
                    if patient_zero_virus.pathogen_id not in agent_infections_this_tick:
                        pending.register_infection(person.entity_id, patient_zero_virus)
                        agent_infections_this_tick.add(patient_zero_virus.pathogen_id)
                        self.logger.info(
                            "🚨 Brote: %s en Agente %s (vir: %.2f, trans: %.2f, let: %.2f, inc: %.1fd, asym: %.2f)",
                            patient_zero_virus.pathogen_id,
                            person.entity_id,
                            patient_zero_virus.virulence,
                            patient_zero_virus.transmission,
                            patient_zero_virus.lethality,
                            patient_zero_virus.incubation_days,
                            patient_zero_virus.asymptomatic_chance,
                        )

    # =========================================================================
    # NUEVOS MÉTODOS: Integración con RelationshipExperienceEngine
    # =========================================================================

    def _notify_recovery_care(self, patient: Any, state: WorldState, pending: PendingChanges, current_day: float, pathogen: Any) -> None:
        """Notifica al motor de relaciones que un agente se recuperó, generando eventos de cuidado."""
        if not self.relationship_engine:
            return

        # Buscar parejas o familiares cercanos que puedan haberlo "cuidado"
        for rel in getattr(patient, 'relationships', []):
            if rel.status in (RelationshipStatus.DATING, RelationshipStatus.COHABITATION, RelationshipStatus.CONSOLIDATED):
                partner = state.get_person_by_id(rel.partner_id)
                # CORRECCIÓN: Usar pending.deaths en lugar de state.pending_deaths
                if partner and partner.entity_id not in pending.deaths:
                    
                    # Calcular distancia para ver si estaban realmente "cuidando"
                    distance = math.hypot(patient.x - partner.x, patient.y - partner.y)
                    
                    # Si están cerca (ej. < 15 unidades), asumimos que hubo cuidado
                    if distance < 15.0:
                        intensity = min(1.0, 0.4 + (pathogen.virulence * 0.5))
                        
                        # Evento: Partner cuidó al paciente
                        event_care = RelationshipEvent(
                            event_type=RelationshipEventType.CARE,
                            agent_a_id=partner.entity_id,
                            agent_b_id=patient.entity_id,
                            intensity=intensity,
                            context=f"recuperacion_de_{pathogen.pathogen_id}",
                            day=current_day,
                        )
                        self.relationship_engine.process_event(event_care, partner, patient, current_day)

    def _notify_partner_death(self, deceased: Any, state: WorldState, pending: PendingChanges, current_day: float) -> None:
        """Notifica a las relaciones cercanas sobre la muerte de un agente."""
        if not self.relationship_engine:
            return

        for rel in getattr(deceased, 'relationships', []):
            # Cualquier relación activa se ve afectada por la muerte
            if rel.status != RelationshipStatus.EX_PARTNER:
                survivor = state.get_person_by_id(rel.partner_id)
                # CORRECCIÓN: Usar pending.deaths
                if survivor and survivor.entity_id not in pending.deaths:
                    
                    # Por simplicidad, usamos PARTNER_DEATH para cualquier relación cercana que pierde a su pareja
                    event_type = RelationshipEventType.PARTNER_DEATH
                    
                    # La intensidad del duelo depende del apego
                    intensity = min(1.0, 0.5 + (rel.attachment / 100.0) * 0.5)
                    
                    event_death = RelationshipEvent(
                        event_type=event_type,
                        agent_a_id=deceased.entity_id,
                        agent_b_id=survivor.entity_id,
                        intensity=intensity,
                        context="fallecimiento",
                        day=current_day,
                    )
                    # Procesamos el evento desde la perspectiva del superviviente
                    self.relationship_engine.process_event(event_death, survivor, deceased, current_day)