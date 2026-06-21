"""Módulo responsable de la navegación espacial basada en Utilidad (Utility AI).

Sustituye el movimiento lineal o aleatorio por un sistema de Campos de Potencial.
Las entidades evalúan su vecindad espacial ponderando la atracción hacia los 
recursos y vínculos sociales, y la repulsión hacia enfermedades y hacinamiento.
"""

import math
import random
import logging
from typing import Any

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class MovementSystem:
    """Motor de navegación espacial que evalúa múltiples campos de potencial."""

    def __init__(self, config: SimulationConfig, density_system: Any, relationship_system: Any) -> None:
        """Inicializa el motor de movimiento inteligente.
        
        Args:
            config: Configuración maestra de la simulación.
            density_system: (Deprecado/Opcional) Sistema heredado de densidad.
            relationship_system: Sistema para obtener los anclajes sociales.
        """
        self.config = config
        self.density_system = density_system
        self.relationship_system = relationship_system
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Calcula el vector de movimiento óptimo para cada agente vivo.
        
        Evalúa el entorno inmediato y selecciona la celda con mayor score
        de supervivencia y afinidad social.
        """
        move_cfg = self.config.movement
        
        # Radio de evaluación dinámico basado en la capacidad de movimiento
        distance_capacity = move_cfg.base_speed * delta_days
        eval_radius = max(1, int(math.ceil(distance_capacity)))
        
        max_x = state.width - 1
        max_y = state.height - 1

        for person in state.get_all_persons():
            # 1. INTEGRIDAD DE ESTADO (No mover fallecidos)
            if person.entity_id in pending.deaths:
                continue

            # 2. DEFINICIÓN DEL OBJETIVO SOCIAL
            social_target = self.relationship_system.get_social_anchor(person, state)
            if social_target and social_target.entity_id in pending.deaths:
                social_target = None

            best_score = -float('inf')
            best_x, best_y = person.x, person.y

            # 3. ESCANEO DEL CAMPO DE POTENCIAL (Utility AI)
            for dx in range(-eval_radius, eval_radius + 1):
                for dy in range(-eval_radius, eval_radius + 1):
                    dist_to_cell = math.sqrt(dx**2 + dy**2)
                    if dist_to_cell > distance_capacity and dist_to_cell != 0:
                        continue

                    nx, ny = person.x + dx, person.y + dy
                    
                    # Respetar bordes del mapa
                    if not (0 <= nx <= max_x and 0 <= ny <= max_y):
                        continue

                    # Obtener la puntuación de utilidad de la celda objetivo
                    score = self._evaluate_cell_utility(
                        person=person, x=nx, y=ny, 
                        state=state, context=context, 
                        social_target=social_target
                    )

                    # Ruido estocástico controlado para evitar bucles de empate deterministas
                    score += random.uniform(-0.01, 0.01)

                    if score > best_score:
                        best_score = score
                        best_x, best_y = nx, ny

            # 4. REGISTRO TRANSACCIONAL
            if best_x != person.x or best_y != person.y:
                pending.register_movement(person.entity_id, best_x, best_y)

    def _evaluate_cell_utility(self, person: Any, x: int, y: int, 
                               state: WorldState, context: EnvironmentContext, 
                               social_target: Any) -> float:
        """Calcula matemáticamente la deseabilidad de una coordenada espacial."""
        score = 0.0
        
        # A. RECURSOS Y ENERGÍA (Fuerza de Atracción)
        energy_deficit = 1.0 - person.emotions.get("energy", 1.0)
        resources = getattr(context, 'get_resources_at', lambda x, y: 0.5)(x, y)
        score += (resources * energy_deficit * 10.0)

        # B. EPIDEMIOLOGÍA: BLINDAJE ABSOLUTO CON AISLAMIENTO DE EXCEPCIONES
        viral_load = 0.0
        ep_map = getattr(state, 'epidemiological_map', None)
        
        if ep_map is not None:
            try:
                raw_result = None
                method_executed = False
                
                # Intentamos buscar y ejecutar el método dinámicamente
                for method_name in ['get_load_at', 'get_viral_load', 'get_load', 'get_density_at']:
                    method = getattr(ep_map, method_name, None)
                    if callable(method):
                        try:
                            raw_result = method(x, y)
                            method_executed = True
                            break
                        except Exception:
                            try:
                                # Intento alternativo si la firma pide una tupla de coordenadas
                                raw_result = method((x, y))
                                method_executed = True
                                break
                            except Exception:
                                continue
                
                # Si los métodos fallaron o no existen, intentamos inspeccionar diccionarios comunes
                if not method_executed:
                    matrix = getattr(ep_map, 'matrix', getattr(ep_map, '_cells', None))
                    if isinstance(matrix, dict):
                        raw_result = matrix.get((x, y), 0.0)
                
                # Evaluación estricta del resultado: Solo aceptamos tipos numéricos puros.
                # Si es un objeto complejo, una lista o None, pasamos olímpicamente de él (viral_load = 0.0)
                if isinstance(raw_result, (int, float)):
                    viral_load = float(raw_result)
                    
            except Exception:
                # Ante CUALQUIER error no previsto en la llamada o el parseo, la carga se evalúa neutral (0.0)
                viral_load = 0.0

        score -= (viral_load * 15.0)

        # C. PRESIÓN AMBIENTAL Y SOBREPOBLACIÓN (Fuerza de Repulsión)
        density = state.world_grid.get_density_at(x, y)
        trauma_crowding = person.memory.get("trauma_overcrowding", 0.0)
        crowding_penalty = 1.0 + (trauma_crowding * 5.0)
        score -= (density * crowding_penalty)

        # D. ANCLAJE SOCIAL (Fuerza de Atracción hacia la Pareja/Familia)
        if social_target:
            dist_to_target = math.sqrt((social_target.x - x)**2 + (social_target.y - y)**2)
            score -= (dist_to_target * 2.0)
            
        return score