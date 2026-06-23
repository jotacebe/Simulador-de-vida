"""Módulo responsable de gestionar las migraciones masivas a larga distancia.

Identifica factores de expulsión (push factors: hambre, epidemias, clima hostil,
superpoblación) y factores de atracción (pull factors: oportunidades de recursos).
Asigna vectores de migración que anulan el comportamiento sedentario normal.
"""

import math
import random
import logging
from typing import Any, Tuple, Optional

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class MigrationSystem:
    """Sistema que evalúa la necesidad de emigrar y calcula rutas de escape lejanas."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el gestor de migraciones."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        # Distancia en celdas a la que consideramos que una migración ha finalizado
        self.arrival_threshold = 5.0

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Evalúa las condiciones locales de cada agente y asigna destinos de migración."""
        
        max_x = state.width - 1
        max_y = state.height - 1

        for person in state.get_all_persons():
            # 1. INTEGRIDAD DE ESTADO
            if person.entity_id in pending.deaths:
                continue

            mem = person.memory if isinstance(getattr(person, 'memory', None), dict) else {}

            # 2. SEGUIMIENTO DE MIGRACIÓN ACTIVA
            target = mem.get("migration_target")
            if target is not None:
                tx, ty = target
                dist = math.hypot(person.x - tx, person.y - ty)
                if dist <= self.arrival_threshold:
                    # ¡Ha llegado a su destino! 
                    # Simplemente limpiamos la memoria. El GoalSystem dictará qué hacer ahora.
                    mem["migration_target"] = None
                continue  

            # 3. EVALUACIÓN DE DETONANTES (Push Factors)
            needs_to_migrate = False
            
            # A. Superpoblación (Presión espacial)
            # Usamos int() para evitar errores si person.x / person.y son floats
            local_pressure = context.get_local_pressure(int(person.x), int(person.y))
            if local_pressure > 1.8:  
                needs_to_migrate = True
            
            # B. Hambre 
            energy = getattr(person, 'emotions', {}).get("energy", 1.0)
            local_resources = getattr(context, 'get_resources_at', lambda x, y: 0.5)(int(person.x), int(person.y))
            if energy < 0.3 and local_resources < 0.2:
                needs_to_migrate = True

            # C. Epidemias
            trauma_sickness = mem.get("trauma_sickness", 0.0)
            viral_load = self._safely_get_viral_load(state, person.x, person.y)
            if trauma_sickness > 0.7 or viral_load > 2.0:
                needs_to_migrate = True

            # D. Clima y Entorno Hostil
            env_system = getattr(state, 'environment_system', None)
            if env_system and hasattr(env_system, 'get_danger_level'):
                if env_system.get_danger_level(int(person.x), int(person.y)) > 0.5:
                    needs_to_migrate = True

            # E. Determinación Psicológica
            if getattr(person, 'current_goal', None) == "EMIGRATE":
                needs_to_migrate = True

            # 4. BÚSQUEDA DE OPORTUNIDADES (Pull Factors)
            if needs_to_migrate:
                best_target = self._find_opportunity(
                    current_x=person.x, current_y=person.y, 
                    max_x=max_x, max_y=max_y, 
                    context=context, env_system=env_system
                )
                if best_target:
                    mem["migration_target"] = best_target
                    self.logger.debug(f"Agente {person.entity_id} inicia migración hacia {best_target}")

    def _find_opportunity(self, current_x: float, current_y: float, 
                          max_x: int, max_y: int, 
                          context: EnvironmentContext, env_system: Any) -> Optional[Tuple[float, float]]:
        """Muestrea el mapa global para encontrar un sector prometedor."""
        best_score = -float('inf')
        best_coord = None
        
        for _ in range(5):
            tx = random.uniform(0, max_x)
            ty = random.uniform(0, max_y)
            
            if math.hypot(current_x - tx, current_y - ty) < 25.0:
                continue

            # CORRECCIÓN DE TIPO: Forzamos la conversión a int() en todas las consultas al grid
            coord_x = int(tx)
            coord_y = int(ty)

            resources = getattr(context, 'get_resources_at', lambda x, y: 0.5)(coord_x, coord_y)
            pressure = context.get_local_pressure(coord_x, coord_y)
            
            danger = 0.0
            if env_system and hasattr(env_system, 'get_danger_level'):
                danger = env_system.get_danger_level(coord_x, coord_y)

            score = (resources * 15.0) - (pressure * 8.0) - (danger * 25.0)
            
            if score > best_score:
                best_score = score
                best_coord = (tx, ty)
                
        return best_coord

    def _safely_get_viral_load(self, state: WorldState, x: float, y: float) -> float:
        """Extrae la carga viral de una celda de forma blindada."""
        ep_map = getattr(state, 'epidemiological_map', None)
        if not ep_map:
            return 0.0
            
        try:
            raw_val = None
            if hasattr(ep_map, 'get_load_at'):
                raw_val = ep_map.get_load_at(x, y)
            elif hasattr(ep_map, '_cells') and isinstance(ep_map._cells, dict):
                raw_val = ep_map._cells.get((int(x), int(y)), 0)
                
            if isinstance(raw_val, (int, float)):
                return float(raw_val)
                
        except Exception:
            pass
            
        return 0.0