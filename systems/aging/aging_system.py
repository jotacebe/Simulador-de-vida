"""Módulo responsable de la progresión temporal y desgaste biológico.

Implementa desgaste acumulativo: la inversión biológica excesiva en
reproducción o tamaño de camada acelera el reloj celular.
"""

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class AgingSystem:
    """Incrementa la edad de las entidades calculando el peso metabólico."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Aplica el desgaste biológico basado en las decisiones de la entidad."""
        
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue
            
            # TRADE-OFF EMERGENTE (Desgaste por Fertilidad Exitosa)
            # Cada hijo nacido (children_count) impone un "impuesto" metabólico acumulativo
            # a la estructura celular de la gestante/padre. 
            # Una entidad con 10 hijos envejecerá un 15% más rápido.
            reproductive_wear = 1.0 + (getattr(person, 'children_count', 0) * 0.015)
            
            # El embarazo activo también duplica el consumo temporal durante los 9 meses.
            pregnancy_burden = 1.2 if getattr(person, 'is_pregnant', False) else 1.0
            
            # Cálculo final de la edad celular añadida en este tick
            biological_increment = delta_days * reproductive_wear * pregnancy_burden
            
            # Registramos la mutación de estado temporal
            pending.register_age_increment(person.entity_id, biological_increment)