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
        # Acceso directo al objeto de configuración tipado, eliminando diccionarios
        dis_cfg = self.config.diseases
        
        # Transformación de las probabilidades base (asumidas mensuales) a tasas diarias
        # Esto estandariza la unidad de medida temporal para el modelo exponencial
        base_transmission_rate = dis_cfg.base_transmission_chance / 30.0
        base_recovery_rate = dis_cfg.base_recovery_chance / 30.0

        for person in state.get_all_persons():
            # Filtro de contingencia: omitimos entidades ya marcadas como fallecidas
            if person.entity_id in pending.deaths:
                continue

            # Extracción del rasgo genético para aplicar presión selectiva
            immunity = person.genome.immunity

            if getattr(person, 'is_sick', False):
                # 1. SELECCIÓN NATURAL (Recuperación)
                # A mayor inmunidad genética, mayor es la tasa diaria de recuperación
                daily_recovery_rate = base_recovery_rate * immunity
                
                # Fórmula de Poisson/Exponencial para probabilidades acumuladas en tiempo continuo.
                # Protege al sistema de errores matemáticos en ticks parciales o variables.
                total_recovery_chance = 1.0 - math.exp(-daily_recovery_rate * delta_days)

                if random.random() < total_recovery_chance:
                    pending.register_recovery(person.entity_id)
            
            else:
                # 2. SELECCIÓN NATURAL (Contagio)
                # La tasa de contagio es inversamente proporcional a la inmunidad.
                # Se aplica un clamping inferior (0.1) para evitar la división por cero.
                daily_contagion_rate = base_transmission_rate / max(0.1, immunity)
                
                # Integración temporal del riesgo de exposición
                total_contagion_chance = 1.0 - math.exp(-daily_contagion_rate * delta_days)
                
                if random.random() < total_contagion_chance:
                    pending.register_infection(person.entity_id)