"""Módulo de Libre Albedrío implementado como un Sistema de Desviación Estocástica.

Modifica el comportamiento basal de los habitantes inyectando impulsos anómalos
y decisiones rebeldes que rompen las restricciones normativas de la simulación.
"""

import random
import logging
from typing import Any, Dict
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class FreeWillSystem:
    """Sistema que gestiona impulsos rebeldes y desviaciones normativas de los agentes."""

    # Identificadores de impulsos anómalos
    FLAG_TABOO_RELATION = "allow_taboo_relation"   
    FLAG_EARLY_LEAVE = "runaway_impulse"           
    FLAG_OUT_OF_WEDLOCK = "ignore_marriage_norm"   
    FLAG_SINGLE_PARENT = "monoparental_drive"       
    FLAG_UNEXPECTED_MIGRATION = "erratic_explorer"  

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_anomaly_chance = 0.015

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue

            # ==========================================================
            # BLINDAJE: USAMOS EL DICCIONARIO NATIVO 'MEMORY'
            # ==========================================================
            # Usamos person.memory, que sabemos 100% que existe y es un dict
            memory_dict = person.memory
            
            flags = memory_dict.get("free_will_flags")
            
            # Inicializamos dentro de memory si no existe
            if not isinstance(flags, dict):
                flags = {
                    self.FLAG_TABOO_RELATION: False,
                    self.FLAG_EARLY_LEAVE: False,
                    self.FLAG_OUT_OF_WEDLOCK: False,
                    self.FLAG_SINGLE_PARENT: False,
                    self.FLAG_UNEXPECTED_MIGRATION: False
                }
                memory_dict["free_will_flags"] = flags

            # Asegurar claves requeridas
            for default_flag in [self.FLAG_TABOO_RELATION, self.FLAG_EARLY_LEAVE, 
                                 self.FLAG_OUT_OF_WEDLOCK, self.FLAG_SINGLE_PARENT, 
                                 self.FLAG_UNEXPECTED_MIGRATION]:
                if default_flag not in flags:
                    flags[default_flag] = False

            # ==========================================================
            # PRIORIZACIÓN DINÁMICA DE ANOMALÍAS
            # ==========================================================
            energy = person.emotions.get("energy", 1.0) if hasattr(person, 'emotions') else 1.0
            trauma = person.memory.get("trauma_overcrowding", 0.0)
            local_pressure = context.get_local_pressure(person.x, person.y)
            
            stress_multiplier = 1.0 + ((1.0 - energy) * 2.0) + (trauma * 3.0) + (local_pressure - 1.0)
            dynamic_chance = self.base_anomaly_chance * max(1.0, stress_multiplier)

            # ==========================================================
            # TIRADA DE DADOS ESTOCÁSTICA (ESCRITURA SEGURA)
            # ==========================================================
            
            if random.random() < (dynamic_chance * 0.5):
                flags[self.FLAG_TABOO_RELATION] = True
            
            age = getattr(person, 'age', 0)
            if 10 <= age < 18:
                home_stress = dynamic_chance * (2.0 if trauma > 0.5 else 1.0)
                if random.random() < home_stress:
                    flags[self.FLAG_EARLY_LEAVE] = True

            if random.random() < dynamic_chance:
                flags[self.FLAG_OUT_OF_WEDLOCK] = True

            if random.random() < (dynamic_chance * 1.2):
                flags[self.FLAG_SINGLE_PARENT] = True

            if random.random() < (dynamic_chance * 0.8):
                flags[self.FLAG_UNEXPECTED_MIGRATION] = True

    @staticmethod
    def has_impulse(person: Any, flag_name: str) -> bool:
        """Método utilitario estático para consultar el libre albedrío."""
        if not hasattr(person, 'memory') or not isinstance(person.memory, dict):
            return False
        flags = person.memory.get("free_will_flags")
        if not isinstance(flags, dict):
            return False
        return flags.get(flag_name, False)

    @staticmethod
    def consume_impulse(person: Any, flag_name: str) -> None:
        """Apaga el impulso una vez ejecutado para que no se repita en bucle."""
        if hasattr(person, 'memory') and isinstance(person.memory, dict):
            flags = person.memory.get("free_will_flags")
            if isinstance(flags, dict) and flag_name in flags:
                flags[flag_name] = False