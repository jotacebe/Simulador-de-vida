"""Módulo responsable del cálculo de desplazamientos hacia anclajes sociales."""

import math
import logging
from typing import Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class MovementSystem:
    """Calcula vectores de movimiento aplicando matemáticas de tiempo continuo."""

    def __init__(self, config: SimulationConfig, density_system: Any, relationship_system: Any) -> None:
        """Inicializa el sistema vinculándolo a la configuración central y dependencias."""
        self.config = config
        self.density_system = density_system
        self.relationship_system = relationship_system
        self.logger = logging.getLogger("MovementSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Calcula el desplazamiento acumulado para el periodo delta_days."""
        
        move_cfg = self.config.movement
        
        # Distancia total máxima que el agente puede recorrer en este tick continuo
        distance_capacity = move_cfg.base_speed * delta_days
        
        for person in state.get_all_persons():
            # Filtro de integridad
            if person.entity_id in pending.deaths:
                continue

            # Buscamos el anclaje dictaminado por la red social
            target = self.relationship_system.get_social_anchor(person, state)
            if target is None:
                continue

            # Vector direccional hacia el objetivo
            dx = target.x - person.x
            dy = target.y - person.y
            dist = math.sqrt(dx**2 + dy**2)

            # Optimización: Umbral de tolerancia de proximidad
            if dist < 0.1:
                continue

            # Normalizamos el vector y aplicamos la magnitud de desplazamiento
            move_amount = min(dist, distance_capacity)
            ratio = move_amount / dist
            
            new_x = person.x + (dx * ratio)
            new_y = person.y + (dy * ratio)

            # Registramos el desplazamiento redondeado para asegurar alineación a la cuadrícula
            pending.register_movement(person.entity_id, round(new_x), round(new_y))