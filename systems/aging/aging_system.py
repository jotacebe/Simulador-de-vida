"""Módulo responsable de la progresión temporal y envejecimiento biológico de los agentes."""

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class AgingSystem:
    """Incrementa la edad biológica de las entidades de forma continua.
    
    Aplica el paso del tiempo transcurrido (delta temporal) a todos los individuos
    activos en el ecosistema, operando estrictamente en unidades de días.
    """

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Añade el tiempo transcurrido a la edad biológica de los agentes vivos."""
        
        for person in state.get_all_persons():
            # Filtro de integridad referencial
            if person.entity_id in pending.deaths:
                continue
            
            # Al estar la arquitectura unificada en días, el incremento temporal
            # es una asignación directa del avance del reloj del motor.
            increment = delta_days
            
            # Registramos la mutación de estado de forma segura
            pending.register_age_increment(person.entity_id, increment)