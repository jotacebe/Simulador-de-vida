"""Módulo responsable del cálculo de desplazamientos en la cuadrícula espacial."""

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
        """Inicializa el sistema vinculándolo a la configuración central y dependencias.
        
        Args:
            config (SimulationConfig): Configuración maestra.
            density_system (Any): Sistema para consultas de densidad.
            relationship_system (Any): Sistema para obtener anclajes sociales (parejas).
        """
        self.config = config
        self.density_system = density_system
        self.relationship_system = relationship_system
        self.logger = logging.getLogger("MovementSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Calcula el desplazamiento acumulado para el periodo delta_days.
        
        Cumple estrictamente con las reglas físicas del motor:
        1. No mueve muertos.
        2. Respeta límites del mapa (clamping).
        3. Limita el desplazamiento a la velocidad máxima.
        """
        
        move_cfg = self.config.movement
        
        # Distancia total máxima que el agente puede recorrer en este tick
        distance_capacity = move_cfg.base_speed * delta_days
        
        # Pre-calculamos los límites físicos del mapa para la restricción (0 a width-1)
        # Asumiendo que state.width y state.height están definidos en WorldState
        max_x = state.width - 1
        max_y = state.height - 1
        
        for person in state.get_all_persons():
            # ==========================================
            # 1. NUNCA MUEVE INDIVIDUOS MUERTOS
            # ==========================================
            # Filtro de integridad: no procesamos entidades fallecidas en este tick.
            # (Las muertas en ticks anteriores ya no están en state.get_all_persons).
            if person.entity_id in pending.deaths:
                continue

            # ==========================================
            # 2. SELECCIÓN DE OBJETIVO (SOCIAL)
            # ==========================================
            target = self.relationship_system.get_social_anchor(person, state)
            
            # Si no tiene anclaje social, o el anclaje acaba de morir, se queda quieto
            if target is None or target.entity_id in pending.deaths:
                continue

            # Vector direccional hacia el objetivo
            dx = target.x - person.x
            dy = target.y - person.y
            dist = math.sqrt(dx**2 + dy**2)

            # Optimización: Umbral de tolerancia de proximidad para evitar oscilaciones (jitter)
            if dist < move_cfg.proximity_threshold:
                continue

            # ==========================================
            # 3. RESPETO A LA VELOCIDAD
            # ==========================================
            # Normalizamos el vector y aplicamos la magnitud estricta permitida
            move_amount = min(dist, distance_capacity)
            ratio = move_amount / dist
            
            new_x = person.x + (dx * ratio)
            new_y = person.y + (dy * ratio)

            # Redondeo algebraico a la cuadrícula discreta
            grid_x = round(new_x)
            grid_y = round(new_y)

            # ==========================================
            # 4. LÍMITES DEL MAPA (CLAMPING)
            # ==========================================
            # Garantiza matemáticamente que las coordenadas jamás saldrán de los bordes
            final_x = max(0, min(grid_x, max_x))
            final_y = max(0, min(grid_y, max_y))

            # Registramos el movimiento validado
            pending.register_movement(person.entity_id, final_x, final_y)