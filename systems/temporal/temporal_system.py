"""
Ruta: systems/temporal/temporal_system.py
Responsabilidad: Gestión del flujo temporal estrictamente en días.
"""
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

class TemporalSystem:
    def __init__(self, config):
        self.logger = logging.getLogger("TemporalSystem")
        
        # Extraemos los hitos en días desde la fuente de verdad (config)
        # Si config.time no los tiene, usamos los valores en días por defecto
        time_cfg = getattr(config, 'time', None)
        self.hitos_dias = {
            "mayoria_edad": getattr(time_cfg, 'adult_age_days', 6570),  # 18 * 365
            "tercera_edad": getattr(time_cfg, 'senior_age_days', 21900) # 60 * 365
        }

    def process(self, state: WorldState, pending: PendingChanges, delta_days: int) -> None:
        # 1. ACTUALIZACIÓN DEL TIEMPO GLOBAL
        state.world_days_elapsed = getattr(state, 'world_days_elapsed', 0) + delta_days
        
        muertos = set(pending.deaths)
        
        # 2. ENVEJECIMIENTO ESTRICTO EN DÍAS
        for person in state.get_all_persons():
            if person.entity_id in muertos:
                continue

            current_age_days = person.age
            new_age_days = current_age_days + delta_days
            
            # Evaluación de hitos cruzando umbrales exactos de días
            if current_age_days < self.hitos_dias["mayoria_edad"] <= new_age_days:
                self.logger.debug(f"[Temporal] Agente {person.entity_id} llega a la mayoría de edad ({new_age_days} días).")
            elif current_age_days < self.hitos_dias["tercera_edad"] <= new_age_days:
                self.logger.debug(f"[Temporal] Agente {person.entity_id} entra en la tercera edad ({new_age_days} días).")

            pending.register_age_increment(person.entity_id, delta_days)