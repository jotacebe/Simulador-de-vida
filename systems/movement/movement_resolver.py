"""Módulo responsable de arbitrar colisiones espaciales antes del commit global."""

import random
import logging
from typing import Dict, List, Tuple, Set
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
        """Inicializa el resolutor cumpliendo el contrato de la arquitectura.
        
        Args:
            config (SimulationConfig): Configuración maestra de la simulación.
        """
        self.config = config
        self.logger = logging.getLogger("MovementResolver")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Analiza las intenciones de movimiento y evita solapamientos espaciales.
        
        Args:
            state (WorldState): Estado centralizado del mundo.
            pending (PendingChanges): Búfer transaccional de mutaciones.
            delta_days (float): Paso de tiempo en días.
            context (EnvironmentContext): Contexto espacial y medioambiental.
        """
        
        # Aborto temprano si no hay movimientos solicitados en el búfer
        if not getattr(pending, 'movements', None):
            return 

        # 1. Identificar casillas bloqueadas (ocupadas por individuos estáticos)
        casillas_bloqueadas: Set[Tuple[int, int]] = set()
        for person in state.get_all_persons():
            # Regla de seguridad 1: Nunca considerar a los individuos muertos
            if person.entity_id in pending.deaths:
                continue 
                
            # Si la persona no se mueve en este tick, su casilla actual es un obstáculo duro
            if person.entity_id not in pending.movements:
                casillas_bloqueadas.add((person.x, person.y))

        # 2. Agrupar peticiones por celda destino y aplicar Fail-Safes
        peticiones_por_celda: Dict[Tuple[int, int], List[int]] = {} 
        
        for entity_id, (target_x, target_y) in pending.movements.items():
            # Regla de seguridad 1 (Doble validación): Garantizar que la entidad no ha fallecido
            if entity_id in pending.deaths:
                continue

            # Regla de seguridad 2: Nunca salir de los límites del mapa (Clamping estricto)
            final_x = max(0, min(int(target_x), state.width - 1))
            final_y = max(0, min(int(target_y), state.height - 1))
            destino = (final_x, final_y)
            
            if destino not in peticiones_por_celda:
                peticiones_por_celda[destino] = []
            peticiones_por_celda[destino].append(entity_id)

        # 3. Arbitrar conflictos y respetar ocupaciones (Regla de objetivos y velocidades)
        movimientos_validados: Dict[int, Tuple[int, int]] = {}
        
        for destino, candidatos in peticiones_por_celda.items():
            # REGLA A: Destino bloqueado por una entidad estática
            if destino in casillas_bloqueadas:
                # El movimiento se cancela; las entidades se quedan en su posición de origen
                continue

            # REGLA B: Celda libre o disputa entre varios agentes en movimiento
            if len(candidatos) == 1:
                ganador = candidatos[0]
                movimientos_validados[ganador] = destino
            else:
                # CONFLICTO: Varios agentes quieren la misma celda. Se resuelve al azar para evitar sesgos de ID.
                ganador = random.choice(candidatos)
                movimientos_validados[ganador] = destino

        # 4. REEMPLAZO ATÓMICO: Sobrescribimos el búfer solo con los movimientos validados y aprobados
        pending.movements = movimientos_validados