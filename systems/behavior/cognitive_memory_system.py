"""Módulo responsable de la memoria a corto/largo plazo y preferencias cognitivas."""

import math
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class CognitiveMemorySystem:
    """Procesa la impronta cognitiva y el desgaste psicológico de los agentes.

    Permite que los individuos recuerden traumas (hacinamiento, enfermedades) y 
    desarrollen preferencias geográficas o sociales. Estos recuerdos alteran
    las utilidades de sus acciones, evitando la estasis conductual.
    """

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema cognitivo vinculándolo a la configuración central.
        
        Args:
            config (SimulationConfig): Configuración central de la simulación.
        """
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

            # 1. ACCESO ESTRUCTURADO A LA MEMORIA
            # En lugar de asignar dinámicamente el diccionario, obtenemos
            # la referencia al diccionario interno y formalizado de la persona.
            mem = person.memory

            # 2. PROCESAMIENTO DEL DECAIMIENTO EXPONENCIAL
            temperament = person.genome.temperament
            adjusted_lambda = cog_cfg.base_forgetting_rate * (temperament + cog_cfg.temperament_modifier)
            decay_factor = math.exp(-adjusted_lambda * delta_days)

            # 3. REGISTRO DE NUEVAS EXPERIENCIAS (Impronta del Tick)
            local_pressure = context.get_local_pressure(person.x, person.y)
            
            trauma_overcrowding = mem["trauma_overcrowding"] * decay_factor
            if local_pressure > cog_cfg.overcrowding_threshold:
                trauma_overcrowding += (cog_cfg.overcrowding_impact * delta_days)

            trauma_sickness = mem["trauma_sickness"] * decay_factor
            if getattr(person, 'is_sick', False):
                trauma_sickness += (cog_cfg.sickness_impact * delta_days)

            # 4. FIJACIÓN DE PREFERENCIAS GEOGRÁFICAS
            preferred_sector = mem["preferred_sector"]
            
            is_adult = getattr(person, 'is_adult', False)
            is_sick = getattr(person, 'is_sick', False)
            has_children = getattr(person, 'children_count', 0) > 0
            
            if is_adult and not is_sick and has_children:
                preferred_sector = (person.x // context.sector_size, person.y // context.sector_size)

            # 5. APLICACIÓN DE CAMBIOS (Límites controlados por configuración)
            mem["trauma_overcrowding"] = min(cog_cfg.max_trauma_cap, trauma_overcrowding)
            mem["trauma_sickness"] = min(cog_cfg.max_trauma_cap, trauma_sickness)
            
            # Decremento matemático del tiempo de enfriamiento de rebeldía
            mem["rebellion_cooldown"] = max(0.0, mem["rebellion_cooldown"] - delta_days)
            mem["preferred_sector"] = preferred_sector