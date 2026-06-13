"""Módulo responsable de la memoria a corto/largo plazo y preferencias cognitivas."""

import math
import logging
from typing import Tuple
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from entities.person.person import Person
from core.config.simulation_config import SimulationConfig

class CognitiveMemorySystem:
    """Procesa la impronta cognitiva y el desgaste psicológico de los agentes.
    
    Permite que los individuos recuerden traumas (hacinamiento, enfermedades) y 
    desarrollen preferencias geográficas o sociales. Estos recuerdos alteran
    las utilidades de sus acciones, evitando la estasis conductual.
    """

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema cognitivo vinculándolo a la configuración central."""
        self.config = config
        self.logger = logging.getLogger("CognitiveMemorySystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Actualiza el estado mental de todos los agentes vivos.
        
        Aplica decaimiento exponencial a las memorias pasadas y registra
        nuevos eventos estresantes o positivos del entorno actual.
        """
        cog_cfg = self.config.cognition

        for person in state.get_all_persons():
            # Filtro de integridad referencial: omitimos a los fallecidos
            if person.entity_id in pending.deaths:
                continue

            # 1. INICIALIZACIÓN DE LA ESTRUCTURA COGNITIVA
            # TODO (Arquitectura): En el futuro, esta inicialización debería 
            # ocurrir dentro del __init__ de la clase Person, no aquí.
            if getattr(person, 'memory', None) is None:
                person.memory = {
                    "trauma_overcrowding": 0.0,
                    "trauma_sickness": 0.0,
                    "preferred_sector": None,
                    "rebellion_cooldown": 0.0
                }

            # 2. PROCESAMIENTO DEL DECAIMIENTO EXPONENCIAL
            # Vinculamos la velocidad de olvido al gen de temperamento del agente.
            # A mayor temperamento, más rápido disipan los traumas y el estrés.
            temperament = person.genome.temperament
            adjusted_lambda = cog_cfg.base_forgetting_rate * (temperament + 0.5)
            decay_factor = math.exp(-adjusted_lambda * delta_days)

            # 3. REGISTRO DE NUEVAS EXPERIENCIAS (Impronta del Tick)
            # Evaluamos la presión local del entorno a través del contexto
            local_pressure = context.get_local_pressure(person.x, person.y)
            
            trauma_overcrowding = person.memory["trauma_overcrowding"] * decay_factor
            if local_pressure > cog_cfg.overcrowding_threshold:
                trauma_overcrowding += (cog_cfg.overcrowding_impact * delta_days)

            trauma_sickness = person.memory["trauma_sickness"] * decay_factor
            if getattr(person, 'is_sick', False):
                trauma_sickness += (cog_cfg.sickness_impact * delta_days)

            # 4. FIJACIÓN DE PREFERENCIAS GEOGRÁFICAS
            # Si un agente próspera (adulto, sano y con descendencia), ancla su sector actual
            preferred_sector = person.memory.get("preferred_sector")
            if getattr(person, 'is_adult', False) and not getattr(person, 'is_sick', False) and getattr(person, 'children_count', 0) > 0:
                preferred_sector = (person.x // context.sector_size, person.y // context.sector_size)

            # 5. APLICACIÓN DE CAMBIOS
            # Aplicamos clamping (límite máximo de 1.0) para evitar desbordamientos
            person.memory["trauma_overcrowding"] = min(1.0, trauma_overcrowding)
            person.memory["trauma_sickness"] = min(1.0, trauma_sickness)
            person.memory["rebellion_cooldown"] = max(0.0, person.memory["rebellion_cooldown"] - delta_days)
            person.memory["preferred_sector"] = preferred_sector