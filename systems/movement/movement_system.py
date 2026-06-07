"""
Ruta: systems/movement/movement_system.py
Responsabilidad: Calcular el desplazamiento hacia anclajes sociales normalizado por tiempo continuo en días.
"""
import math
import logging
from typing import Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext

class MovementSystem:
    def __init__(self, config, density_system: Any, relationship_system: Any):
        self.config = config
        self.density_system = density_system
        self.relationship_system = relationship_system
        self.logger = logging.getLogger("MovementSystem")
        
        # Extracción segura de la configuración (espera una categoría 'movement')
        move_cfg = getattr(config, 'movement', {})
        if isinstance(move_cfg, dict):
            self.base_speed = move_cfg.get("movement_speed", 0.5) 
        else:
            self.base_speed = getattr(move_cfg, "movement_speed", 0.5)

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        """
        Calcula el desplazamiento acumulado para el periodo 'delta_days' utilizando matemática continua.
        """
        # Distancia total máxima que el agente puede recorrer de golpe en este tick
        distance_capacity = self.base_speed * delta_days
        
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue

            target = self.relationship_system.get_social_anchor(person, state)
            if target is None:
                continue

            # Vector hacia el objetivo
            dx = target.x - person.x
            dy = target.y - person.y
            dist = math.sqrt(dx**2 + dy**2)

            # Si ya estamos en la misma posición (o muy cerca), no mover
            if dist < 0.1:
                continue

            # Normalizar vector y multiplicar por la capacidad de movimiento en días
            move_amount = min(dist, distance_capacity)
            ratio = move_amount / dist
            
            new_x = person.x + (dx * ratio)
            new_y = person.y + (dy * ratio)

            # Registrar como redondeado para mantener el grid y la compatibilidad con PendingChanges
            pending.register_movement(person.entity_id, round(new_x), round(new_y))