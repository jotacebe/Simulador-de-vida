"""Módulo responsable de la gestión epidemiológica y evolución de patógenos.

Implementa un modelo de propagación espacial con fases de infección:
- Expuesto → Incubando → Contagioso → Sintomático → Recuperándose

Mejoras implementadas:
- Periodo de incubación (no contagia inmediatamente)
- Infecciones asintomáticas (contagian pero no muestran síntomas)
- Mutación reemplaza cepa anterior (no acumula)
- Límite de cepas simultáneas por familia
- Carga viral del sector basada en emisores contagiosos
- Brotes espontáneos con propiedades aleatorias
- Decaimiento de inmunidad con el tiempo
- Integración con sistema de memoria para recordar enfermedades superadas
- Prevención de reinfecciones múltiples en el mismo tick
- Tasa de recuperación aumentada
- Aplicación de letalidad durante fase sintomática
- CORRECCIÓN: Tracking local de infecciones por agente para evitar duplicados
"""

import random
import math
import logging
from collections import defaultdict
from typing import Dict, Set
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig
from systems.diseases.pathogen import Pathogen, InfectionPhase


class DiseaseSystem:
    """Motor epidemiológico espacial (Variantes, Inmunidad y Contagio focal)."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config
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
                person.decay_immunity(delta_days, decay_rate=0.0003)  # 3x más lento

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
                    lethality_risk = pathogen.lethality * 0.01 * delta_days  # 1% diario × letalidad
                    # Reducir por inmunidad
                    total_immunity = person.get_specific_immunity(pathogen)
                    lethality_risk = lethality_risk / max(0.1, total_immunity)
                    
                    if random.random() < lethality_risk:
                        pending.register_death(
                            person.entity_id,
                            f"Sepsis / Fallo multiorgánico por {pathogen.pathogen_id}"
                        )
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
                    # Intento de Recuperación mediado por Inmunidad Adquirida
                    total_immunity = person.get_specific_immunity(pathogen)
                    
                    # Tasa de recuperación aumentada (3x más alta)
                    daily_recovery_rate = (dis_cfg.base_recovery_chance * 3.0 * total_immunity) / max(0.1, pathogen.virulence)
                    recovery_chance = 1.0 - math.exp(-daily_recovery_rate * delta_days)
                    
                    if random.random() < recovery_chance:
                        # RECUPERACIÓN EXITOSA
                        pending.register_recovery(person.entity_id, path_id)
                        
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
            
            # CORRECCIÓN: Tracking local de infecciones por agente en este tick
            agent_infections_this_tick: Set[str] = set()
            
            # Contar cepas por familia ANTES de iterar
            family_counts = defaultdict(int)
            for pid in person.active_infections.keys():
                family = pid.split('_')[0]
                family_counts[family] += 1
            
            # Contagio cruzado
            for pathogen, _ in local_pathogens:
                # Si ya tiene esta cepa exacta, no reinfectar
                if pathogen.pathogen_id in person.active_infections:
                    continue
                
                # CORRECCIÓN: Si ya fue infectado en este tick, no reinfectar
                if pathogen.pathogen_id in agent_infections_this_tick:
                    continue
                
                # Limitar cepas por familia (máximo 2)
                if family_counts[pathogen.family] >= 2:
                    continue
                
                # Pasar patógeno completo para inmunidad específica por cepa
                total_immunity = person.get_specific_immunity(pathogen)
                
                # Si la inmunidad es muy alta, bloquear infección
                if total_immunity > 1.5:
                    continue
                
                crowding_pressure = context.get_local_pressure(person.x, person.y)
                
                # Fórmula mejorada con umbral de inmunidad
                immunity_factor = min(1.0, total_immunity / 2.0)
                base_rate = (pathogen.transmission * max(1.0, crowding_pressure)) / max(0.5, total_immunity)
                daily_transmission_rate = base_rate * (1.0 - immunity_factor * 0.8)
                infection_chance = 1.0 - math.exp(-daily_transmission_rate * delta_days)
                
                if random.random() < infection_chance:
                    pending.register_infection(person.entity_id, pathogen)
                    # CORRECCIÓN: Registrar en el tracking local
                    agent_infections_this_tick.add(pathogen.pathogen_id)
                    family_counts[pathogen.family] += 1
            
            # Brote espontáneo
            outbreak_chance = 1.0 - math.exp(-(dis_cfg.base_outbreak_chance / 100.0) * delta_days)
            if random.random() < outbreak_chance:
                familia_random = random.choice(["Influenza", "Coronavirus", "Poxvirus", "Bacteriofago_X"])
                patient_zero_virus = Pathogen.create_random_variant(familia_random)
                
                # Verificar que no tenga ya esta infección
                if patient_zero_virus.pathogen_id not in person.active_infections:
                    # CORRECCIÓN: Verificar también el tracking local
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