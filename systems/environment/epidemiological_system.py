"""Módulo responsable de la interacción entre los agentes y los patógenos del entorno."""

import random
import math
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class EpidemiologicalSystem:
    """Gestiona el rastro viral dejado por enfermos y el contagio por fómites."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config
        self.logger = logging.getLogger("EpidemiologicalSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa la retroalimentación virus-entorno-agente."""
        
        env_cfg = self.config.environment
        dis_cfg = self.config.diseases
        
        ep_map = state.epidemiological_map
        all_persons = state.get_all_persons()

        # 1. PROPAGACIÓN: Los agentes enfermos contaminan el entorno
        for person in all_persons:
            if person.entity_id in pending.deaths: 
                continue
            
            if getattr(person, 'is_sick', False):
                # La cantidad exhalada es proporcional al tiempo transcurrido en el tick
                ep_map.add_viral_load(person.x, person.y, amount=(0.5 * delta_days))

        # 2. CONTAGIO: El entorno infecta a los agentes sanos
        # Tasa diaria base de infección ambiental
        daily_transmission_rate = dis_cfg.environmental_transmission_rate / 30.0

        for person in all_persons:
            if person.entity_id in pending.deaths or getattr(person, 'is_sick', False): 
                continue 

            viral_load = ep_map.get_viral_load(person.x, person.y)
            
            if viral_load > 0.1:
                # El riesgo escala con la carga viral local
                daily_risk = viral_load * daily_transmission_rate
                
                # Integración temporal del riesgo (probabilidad exponencial acumulada)
                total_risk = 1.0 - math.exp(-daily_risk * delta_days)
                
                if random.random() < total_risk:
                    pending.register_infection(person.entity_id)
                    self.logger.debug(f"Agente {person.entity_id} contagiado por rastro ambiental.")

        # 3. DECAIMIENTO: El virus se disipa en el ambiente
        # Aplicamos el factor de decaimiento ajustado por los días transcurridos
        decay = env_cfg.viral_decay_factor ** delta_days
        ep_map.decay_viral_load(factor=decay)