"""Módulo responsable de gestionar las migraciones masivas a larga distancia.

Identifica factores de expulsión (push factors: hambre, epidemias, clima hostil,
superpoblación) y factores de atracción (pull factors: oportunidades de recursos).
Asigna vectores de migración que anulan el comportamiento sedentario normal.

Integra con:
- Sistema de memoria cognitiva para registrar recuerdos de migraciones
- Sistema de motivaciones continuas para comportamiento emergente
- Cooldown de migración interno para evitar comportamiento nómada
- NUEVO: Registro del motivo de cada migración en el log
"""

import math
import random
import logging
from typing import Any, Dict, List, Tuple, Optional

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig


class MigrationSystem:
    """Sistema que evalúa la necesidad de emigrar y calcula rutas de escape lejanas."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el gestor de migraciones."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.arrival_threshold: float = 5.0
        
        # Registro interno (no depende del sistema transaccional)
        self._cooldowns: Dict[int, float] = {}
        self._active_targets: Dict[int, Tuple[float, float]] = {}

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Evalúa las condiciones locales de cada agente y asigna destinos de migración."""
        max_x = state.width - 1
        max_y = state.height - 1

        current_day = getattr(state, 'world_days_elapsed', 0.0)
        
        fw_cfg = self.config.free_will
        migration_cooldown = getattr(fw_cfg, 'migration_cooldown_days', 90.0)

        for person in state.get_all_persons():
            eid = person.entity_id
            
            # 1. INTEGRIDAD DE ESTADO
            if eid in pending.deaths:
                self._cooldowns.pop(eid, None)
                self._active_targets.pop(eid, None)
                continue

            # 2. VERIFICAR COOLDOWN
            last_migration = self._cooldowns.get(eid, 0.0)
            if (current_day - last_migration) < migration_cooldown:
                continue

            # 3. SEGUIMIENTO DE MIGRACIÓN ACTIVA
            target = self._active_targets.get(eid)
            if target is not None:
                tx, ty = target
                dist = math.hypot(person.x - tx, person.y - ty)
                
                if dist <= self.arrival_threshold:
                    mem = person.memory if isinstance(getattr(person, 'memory', None), dict) else {}
                    
                    distance_traveled = dist
                    if distance_traveled < 50:
                        intensity = 0.3
                    elif distance_traveled < 150:
                        intensity = 0.6
                    else:
                        intensity = 0.9
                    
                    target_id = f"{int(tx)}_{int(ty)}"
                    
                    CognitiveMemorySystem.add_memory(
                        person=person,
                        mem_type=CognitiveMemorySystem.TYPE_MIGRATION,
                        target_id=target_id,
                        intensity=intensity,
                        valence=1,
                        context="migracion_exitosa",
                        current_day=current_day,
                        pending=pending,
                    )
                    
                    if hasattr(person, 'get_motivation'):
                        pending.register_motivation_update(
                            eid, "migration", fw_cfg.success_reinforcement_rate
                        )
                    
                    self._active_targets.pop(eid, None)
                    
                    self.logger.debug(
                        "🏁 Agente %s completó migración a (%d, %d)",
                        eid, int(tx), int(ty),
                    )
                
                continue

            # 4. EVALUACIÓN DE DETONANTES (Push Factors)
            mem = person.memory if isinstance(getattr(person, 'memory', None), dict) else {}
            needs_to_migrate = False
            migration_reasons: List[Tuple[str, float]] = []  # NUEVO: (motivo, intensidad)
            
            # A. Superpoblación
            local_pressure = context.get_local_pressure(int(person.x), int(person.y))
            if local_pressure > 1.8:
                needs_to_migrate = True
                migration_reasons.append(("superpoblación", local_pressure))
            
            # B. Hambre
            energy = getattr(person, 'emotions', {}).get("energy", 1.0)
            local_resources = getattr(context, 'get_resources_at', lambda x, y: 0.5)(int(person.x), int(person.y))
            if energy < 0.3 and local_resources < 0.2:
                needs_to_migrate = True
                # Intensidad combinada: mayor hambre + menos recursos = más urgente
                hunger_intensity = (1.0 - energy) + (1.0 - local_resources)
                migration_reasons.append(("hambre", hunger_intensity))

            # C. Epidemias
            trauma_sickness = mem.get("trauma_sickness", 0.0)
            viral_load = self._safely_get_viral_load(state, person.x, person.y)
            if trauma_sickness > 0.7 or viral_load > 2.0:
                needs_to_migrate = True
                epidemic_intensity = max(trauma_sickness, viral_load / 5.0)
                migration_reasons.append(("epidemia", epidemic_intensity))

            # D. Clima y Entorno Hostil
            env_system = getattr(state, 'environment_system', None)
            if env_system and hasattr(env_system, 'get_danger_level'):
                danger = env_system.get_danger_level(int(person.x), int(person.y))
                if danger > 0.5:
                    needs_to_migrate = True
                    migration_reasons.append(("clima_hostil", danger))

            # E. Determinación Psicológica
            if getattr(person, 'current_goal', None) == "EMIGRATE":
                needs_to_migrate = True
                migration_reasons.append(("objetivo_psicologico", 1.0))
            
            # F. MOTIVACIÓN INTERNA 'migration'
            if hasattr(person, 'get_motivation'):
                migration_motivation = person.get_motivation("migration")
                migration_threshold = getattr(fw_cfg, 'migration_action_threshold', 0.85)
                
                if migration_motivation >= migration_threshold:
                    needs_to_migrate = True
                    migration_reasons.append(("impulso_interno", migration_motivation))

            # 5. BÚSQUEDA DE OPORTUNIDADES (Pull Factors)
            if needs_to_migrate:
                best_target = self._find_opportunity(
                    current_x=person.x, current_y=person.y,
                    max_x=max_x, max_y=max_y,
                    context=context, env_system=env_system
                )
                if best_target:
                    self._active_targets[eid] = best_target
                    self._cooldowns[eid] = current_day
                    
                    # NUEVO: Determinar motivo principal
                    reason = self._determine_migration_reason(migration_reasons)
                    
                    self.logger.debug(
                        "🚶 Agente %s inicia migración hacia (%.1f, %.1f) [motivo: %s, cooldown: %d días]",
                        eid, best_target[0], best_target[1], reason, int(migration_cooldown),
                    )

    def _determine_migration_reason(self, reasons: List[Tuple[str, float]]) -> str:
        """Determina el motivo principal de la migración.
        
        Args:
            reasons: Lista de tuplas (motivo, intensidad) con todos los factores detectados.
            
        Returns:
            Nombre del motivo con mayor intensidad, o "desconocido" si no hay factores.
        """
        if not reasons:
            return "desconocido"
        
        # Ordenar por intensidad descendente y devolver el principal
        reasons_sorted = sorted(reasons, key=lambda x: x[1], reverse=True)
        return reasons_sorted[0][0]

    def _find_opportunity(
        self,
        current_x: float,
        current_y: float,
        max_x: int,
        max_y: int,
        context: EnvironmentContext,
        env_system: Any,
    ) -> Optional[Tuple[float, float]]:
        """Muestrea el mapa global para encontrar un sector prometedor."""
        best_score = -float('inf')
        best_coord = None
        
        for _ in range(5):
            tx = random.uniform(0, max_x)
            ty = random.uniform(0, max_y)
            
            if math.hypot(current_x - tx, current_y - ty) < 25.0:
                continue

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