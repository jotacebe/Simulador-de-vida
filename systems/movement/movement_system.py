"""Módulo responsable de la navegación espacial basada en Utilidad (Utility AI).

Sustituye el movimiento lineal o aleatorio por un sistema de Campos de Potencial.
Las entidades evalúan su vecindad ponderando recursos, epidemias, hacinamiento y
vectores de migración a larga distancia.

Integra con el nuevo sistema de relaciones sociales:
- Usa partner_id (derivado de relationships[]) como ancla social
- Mantiene compatibilidad con MigrationSystem
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Optional

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext


class MovementSystem:
    """Motor de navegación espacial que evalúa múltiples campos de potencial."""

    def __init__(
        self,
        config: SimulationConfig,
        density_system: Any,
    ) -> None:
        """Inicializa el motor de movimiento inteligente.

        Args:
            config: Configuración maestra de la simulación.
            density_system: (Deprecado/Opcional) Sistema heredado de densidad.
        """
        self.config = config
        self.density_system = density_system
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Calcula el vector de movimiento óptimo para cada agente vivo."""
        move_cfg = self.config.movement

        distance_capacity = move_cfg.base_speed * delta_days
        eval_radius = max(1, int(math.ceil(distance_capacity)))

        max_x = state.width - 1
        max_y = state.height - 1

        for person in state.get_all_persons():
            # 1. INTEGRIDAD DE ESTADO
            if person.entity_id in pending.deaths:
                continue

            # 2. DEFINICIÓN DEL OBJETIVO SOCIAL (Nuevo sistema de relaciones)
            social_target = self._get_social_anchor(person, state, pending)

            best_score = -float("inf")
            best_x, best_y = person.x, person.y

            # 3. ESCANEO DEL CAMPO DE POTENCIAL (Utility AI)
            for dx in range(-eval_radius, eval_radius + 1):
                for dy in range(-eval_radius, eval_radius + 1):
                    dist_to_cell = math.sqrt(dx**2 + dy**2)
                    if dist_to_cell > distance_capacity and dist_to_cell != 0:
                        continue

                    nx, ny = person.x + dx, person.y + dy

                    if not (0 <= nx <= max_x and 0 <= ny <= max_y):
                        continue

                    score = self._evaluate_cell_utility(
                        person=person,
                        x=nx,
                        y=ny,
                        state=state,
                        context=context,
                        social_target=social_target,
                    )

                    score += random.uniform(-0.01, 0.01)

                    if score > best_score:
                        best_score = score
                        best_x, best_y = nx, ny

            # 4. REGISTRO TRANSACCIONAL
            if best_x != person.x or best_y != person.y:
                pending.register_movement(person.entity_id, best_x, best_y)

    def _get_social_anchor(
        self,
        person: Any,
        state: WorldState,
        pending: PendingChanges,
    ) -> Optional[Any]:
        """Obtiene el ancla social del agente (pareja más consolidada).
        
        Usa partner_id que ahora es una property derivada de relationships[].
        Prioriza relaciones CONSOLIDATED > COHABITATION > DATING.
        
        Args:
            person: Agente que busca su ancla social.
            state: Estado del mundo.
            pending: Búfer transaccional (para verificar muertes).
            
        Returns:
            La persona ancla si existe y está viva, None en caso contrario.
        """
        partner_id = getattr(person, "partner_id", None)
        if partner_id is None:
            return None
        
        # Verificar que la pareja no haya muerto en este tick
        if partner_id in pending.deaths:
            return None
        
        return state.get_person_by_id(partner_id)

    def _evaluate_cell_utility(
        self,
        person: Any,
        x: int,
        y: int,
        state: WorldState,
        context: EnvironmentContext,
        social_target: Any,
    ) -> float:
        """Calcula matemáticamente la deseabilidad de una coordenada espacial."""
        score = 0.0

        # A. RECURSOS Y ENERGÍA
        energy_deficit = 1.0 - getattr(person, "emotions", {}).get("energy", 1.0)
        
        # Uso seguro para la llamada al mapa de recursos
        get_resources = getattr(context, "get_resources_at", None)
        resources = get_resources(x, y) if callable(get_resources) else 0.5
        
        score += resources * energy_deficit * 10.0

        # B. EPIDEMIOLOGÍA BLINDADA AL 100%
        viral_load = 0.0
        ep_map = getattr(state, "epidemiological_map", None)

        if ep_map is not None:
            try:
                raw_result = None
                method_executed = False

                for method_name in [
                    "get_load_at",
                    "get_viral_load",
                    "get_load",
                    "get_density_at",
                ]:
                    method = getattr(ep_map, method_name, None)
                    if callable(method):
                        try:
                            raw_result = method(x, y)
                            method_executed = True
                            break
                        except Exception:
                            try:
                                raw_result = method((x, y))
                                method_executed = True
                                break
                            except Exception:
                                continue

                if not method_executed:
                    matrix = getattr(ep_map, "matrix", getattr(ep_map, "_cells", None))
                    if isinstance(matrix, dict):
                        raw_result = matrix.get((x, y), 0.0)

                if isinstance(raw_result, (int, float)):
                    viral_load = float(raw_result)
            except Exception:
                viral_load = 0.0

        score -= viral_load * 15.0

        # C. PRESIÓN AMBIENTAL Y SOBREPOBLACIÓN
        density = context.get_local_pressure(x, y)
        trauma_crowding = (
            getattr(person, "memory", {}).get("trauma_overcrowding", 0.0)
            if isinstance(getattr(person, "memory", None), dict)
            else 0.0
        )
        crowding_penalty = 1.0 + (trauma_crowding * 5.0)
        score -= density * crowding_penalty

        # D. ANCLAJE SOCIAL
        if social_target:
            dist_to_target = math.sqrt((social_target.x - x) ** 2 + (social_target.y - y) ** 2)
            score -= dist_to_target * 2.0

        # =================================================================
        # E. VECTOR DE MIGRACIÓN (Integrador de MigrationSystem)
        # =================================================================
        if isinstance(getattr(person, "memory", None), dict):
            migration_target = person.memory.get("migration_target")
            if migration_target is not None:
                tx, ty = migration_target
                dist_to_migration = math.sqrt((tx - x) ** 2 + (ty - y) ** 2)
                # Al restar la distancia, las celdas que acortan el camino ganan muchísimos puntos.
                # Se pondera x10 para que anule el comportamiento errático de exploración.
                score -= dist_to_migration * 10.0

        return score