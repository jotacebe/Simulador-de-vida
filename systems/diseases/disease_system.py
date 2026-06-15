"""Módulo responsable de la gestión epidemiológica y propagación de patógenos."""

import random
import math
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class DiseaseSystem:
    """Gestiona contagios y recuperaciones probabilísticas basándose en inmunidad."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema epidemiológico con la configuración centralizada."""
        self.config = config
        self.logger = logging.getLogger("DiseaseSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa las transiciones de estado de salud del censo poblacional.
        
        Calcula las probabilidades de infección y cura utilizando tasas diarias
        continuas y aplicando presión selectiva según el gen de inmunidad.
        """
        dis_cfg = self.config.diseases
        time_cfg = self.config.time
        
        # Transformación de las probabilidades base a tasas diarias usando config
        base_transmission_rate = dis_cfg.base_transmission_chance / time_cfg.days_per_month
        base_recovery_rate = dis_cfg.base_recovery_chance / time_cfg.days_per_month

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue

            immunity = person.genome.immunity

            if getattr(person, 'is_sick', False):
                # 1. SELECCIÓN NATURAL (Recuperación)
                daily_recovery_rate = base_recovery_rate * immunity
                total_recovery_chance = 1.0 - math.exp(-daily_recovery_rate * delta_days)

                if random.random() < total_recovery_chance:
                    pending.register_recovery(person.entity_id)
            
            else:
                # 2. SELECCIÓN NATURAL (Contagio)
                # Aplicamos el clamping dinámico desde la configuración
                daily_contagion_rate = base_transmission_rate / max(dis_cfg.immunity_clamping, immunity)
                total_contagion_chance = 1.0 - math.exp(-daily_contagion_rate * delta_days)
                
                if random.random() < total_contagion_chance:
                    pending.register_infection(person.entity_id)