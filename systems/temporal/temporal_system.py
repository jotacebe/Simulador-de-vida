"""Módulo responsable del avance del reloj global y control de hitos generacionales."""

import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class TemporalSystem:
    """Gestiona el flujo temporal macroscópico del ecosistema.
    
    Avanza la línea de tiempo global y detecta cuándo los agentes cruzan
    umbrales biológicos clave (mayoría de edad, senectud), delegando el 
    incremento real de la edad física al AgingSystem para evitar duplicidades.
    """

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el reloj global vinculándolo a la configuración."""
        self.config = config
        self.logger = logging.getLogger("TemporalSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Actualiza la línea de tiempo global y evalúa hitos biológicos."""
        
        time_cfg = self.config.time

        # 1. AVANCE DEL RELOJ GLOBAL
        # Este es el único sistema del motor autorizado para mutar el tiempo del mundo
        current_world_time = getattr(state, 'world_days_elapsed', 0.0)
        state.world_days_elapsed = current_world_time + delta_days

        # 2. EVALUACIÓN DE HITOS BIOLÓGICOS
        # Omitimos llamar a pending.register_age_increment() aquí para no pisarnos 
        # con el AgingSystem. Solo comprobamos fronteras cruzadas en este tick.
        for person in state.get_all_persons():
            # Filtro de integridad: omitimos fallecidos
            if person.entity_id in pending.deaths:
                continue

            current_age = person.age
            new_age = current_age + delta_days
            
            # Evaluación de hitos cruzando umbrales exactos
            if current_age < time_cfg.adult_age_days <= new_age:
                # TODO (Arquitectura): En el futuro, aquí se podría registrar en pending 
                # un cambio de estado civil (ej: pending.register_adult_transition())
                self.logger.debug(f"[Temporal] Agente {person.entity_id} alcanza la madurez ({new_age:.1f} días).")
                
            elif current_age < time_cfg.senior_age_days <= new_age:
                self.logger.debug(f"[Temporal] Agente {person.entity_id} entra en senectud ({new_age:.1f} días).")