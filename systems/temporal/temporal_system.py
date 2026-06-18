"""Módulo responsable del avance del reloj global y ritmos circadianos/energéticos.

Aplica el trade-off pasivo (Inmunidad/Resistencia vs Consumo Energético).
"""

import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class TemporalSystem:
    """Gestiona la línea de tiempo y la termodinámica interna del agente."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el reloj global vinculándolo a la configuración."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Actualiza el mundo y simula el coste de mantenimiento biológico."""
        time_cfg = self.config.time

        # 1. AVANCE DEL RELOJ GLOBAL
        current_world_time = getattr(state, 'world_days_elapsed', 0.0)
        state.world_days_elapsed = current_world_time + delta_days

        # 2. EVALUACIÓN Y COSTE METABÓLICO
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue

            # TRADE-OFF EMERGENTE (Inmunidad Alta = Consumo Energético)
            # Mantener un sistema inmunológico hiperactivo (> 1.0) quema energía a diario.
            # Si el agente no duerme/come (simplificado en la recarga pasiva), se agotará.
            base_recovery = 0.05 * delta_days 
            immune_cost = max(0.0, (person.genome.immunity - 1.0)) * 0.03 * delta_days
            temperament_cost = max(0.0, (person.genome.temperament - 1.0)) * 0.01 * delta_days

            net_energy_change = base_recovery - immune_cost - temperament_cost
            
            # Si el balance es negativo, restamos energía desde el atributo emocional volátil
            if net_energy_change < 0 and hasattr(person, 'update_emotion'):
                person.update_emotion("energy", net_energy_change)
            elif net_energy_change > 0 and hasattr(person, 'update_emotion'):
                # Solo se recupera si está completamente sano (simulación de homeostasis)
                if not getattr(person, 'is_sick', False):
                    person.update_emotion("energy", net_energy_change)

            # 3. CONTROL DE HITOS BIOLÓGICOS (EDAD CRONOLÓGICA)
            current_age = person.age
            new_age = current_age + delta_days
            
            if current_age < time_cfg.adult_age_days <= new_age:
                self.logger.debug(f"[Temporal] Agente {person.entity_id} alcanza la madurez.")
            elif current_age < time_cfg.senior_age_days <= new_age:
                self.logger.debug(f"[Temporal] Agente {person.entity_id} entra en senectud.")