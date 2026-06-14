"""Módulo responsable de arbitrar colisiones espaciales antes del commit global."""

import random
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class MovementResolver:
    """Resuelve cuellos de botella espaciales de forma determinista.
    
    Asegura que dos entidades no ocupen la misma celda si el motor no lo permite,
    operando como un sistema estándar dentro del ciclo de la simulación.
    """

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el resolutor cumpliendo el contrato de la arquitectura."""
        self.config = config
        self.logger = logging.getLogger("MovementResolver")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Analiza las intenciones de movimiento y evita solapamientos."""
        
        # Aborto temprano si no hay movimientos solicitados
        if not getattr(pending, 'movements', None):
            return 

        # 1. Identificar casillas bloqueadas (ocupadas por gente estática)
        casillas_bloqueadas = set()
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue 
                
            if person.entity_id not in pending.movements:
                casillas_bloqueadas.add((person.x, person.y))

        # 2. Agrupar peticiones por celda destino
        peticiones_por_celda = {} 
        for entity_id, (target_x, target_y) in pending.movements.items():
            # Clamping estricto de seguridad espacial
            final_x = max(0, min(int(target_x), state.width - 1))
            final_y = max(0, min(int(target_y), state.height - 1))
            destino = (final_x, final_y)
            
            if destino not in peticiones_por_celda:
                peticiones_por_celda[destino] = []
            peticiones_por_celda[destino].append(entity_id)

        # 3. Arbitrar conflictos
        movimientos_validados = {}
        for destino, candidatos in peticiones_por_celda.items():
            # REGLA A: Destino bloqueado por entidad estática
            if destino in casillas_bloqueadas:
                continue

            # REGLA B: Celda libre o disputa
            if len(candidatos) == 1:
                ganador = candidatos[0]
                movimientos_validados[ganador] = destino
            else:
                # CONFLICTO: Varios quieren la misma celda. Elegimos uno al azar.
                ganador = random.choice(candidatos)
                movimientos_validados[ganador] = destino

        # 4. REEMPLAZO ATÓMICO: Sobrescribimos el búfer con los supervivientes
        pending.movements = movimientos_validados