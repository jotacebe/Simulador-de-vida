"""
Ruta: systems/aging/aging_system.py
Responsabilidad: Incrementar la edad biológica de los agentes de forma continua 
                 basándose en el tiempo transcurrido (delta_days).
"""
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext

class AgingSystem:
    def __init__(self, config):
        self.config = config

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        """
        Incrementa la edad de cada agente vivo de forma proporcional al delta_days.
        """
        for person in state.get_all_persons():
            # Si el agente está muerto, no se le hace envejecer
            if person.entity_id in pending.deaths:
                continue
            
            # Cálculo del incremento: 
            # Si un año son 365 días, envejecer 1 día significa sumar 1/365 años.
            # O, si tu edad se cuenta en días (que es lo que unificamos), simplemente sumamos delta_days.
            
            increment = delta_days
            
            # Registramos la intención de incremento en el buffer transaccional
            pending.register_age_increment(person.entity_id, increment)