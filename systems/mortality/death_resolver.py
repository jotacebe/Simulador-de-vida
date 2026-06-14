"""Módulo responsable de la integridad transaccional tras eventos de mortalidad."""

import logging
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class DeathResolver:
    """Filtro de contingencia para purgar intenciones de entidades fallecidas.
    
    Asegura la coherencia del búfer transaccional eliminando cualquier
    acción de agentes que han muerto en este tick temporal, operando como
    un sistema estándar de la simulación.
    """

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el resolutor cumpliendo el contrato de la arquitectura."""
        self.config = config
        self.logger = logging.getLogger("DeathResolver")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Ejecuta la purga de acciones en cascada sobre el búfer transaccional."""
        
        # Aborto temprano por eficiencia si no ha muerto nadie
        if not pending.deaths:
            return

        muertos_set = set(pending.deaths)

        # 1. Cancelar desplazamientos espaciales
        pending.movements = {
            e_id: coords for e_id, coords in pending.movements.items() 
            if e_id not in muertos_set
        }

        # 2. Cancelar envejecimiento
        pending.age_increments = {
            e_id: inc for e_id, inc in pending.age_increments.items() 
            if e_id not in muertos_set
        }

        # 3. Cancelar infecciones recientes
        pending.infections = [
            e_id for e_id in pending.infections 
            if e_id not in muertos_set
        ]

        # 4. Cancelar trámites de nupcias
        pending.marriages = {
            p_a: p_b for p_a, p_b in pending.marriages.items()
            if p_a not in muertos_set and p_b not in muertos_set
        }

        # 5. Cancelar trámites de divorcio
        pending.divorces = [
            (pa, pb) for pa, pb in pending.divorces 
            if pa not in muertos_set and pb not in muertos_set
        ]
        
        # 6. Cancelar procesos de adopción (NUEVO: Protección de Integridad)
        if hasattr(pending, 'adoptions'):
            pending.adoptions = [
                adop for adop in pending.adoptions
                if adop.get('child_id') not in muertos_set
                and adop.get('parent_a') not in muertos_set
                and adop.get('parent_b') not in muertos_set
            ]