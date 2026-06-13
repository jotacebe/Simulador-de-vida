"""Módulo responsable del comportamiento autónomo y decisiones estocásticas de los agentes."""

import random
import math
import logging
from typing import Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class FreeWillSystem:
    """Motor de decisiones probabilísticas modelado en tiempo continuo.
    
    Permite a las entidades transgredir las reglas sociales estándar (migraciones 
    forzadas, divorcios espontáneos o rebelión reproductiva) basándose en 
    sus mapas genéticos y sus experiencias cognitivas pasadas.
    """

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config
        self.logger = logging.getLogger("FreeWillSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Evalúa las intenciones autónomas de la población activa."""
        fw_cfg = self.config.free_will

        for person in state.get_all_persons():
            # Filtro de contingencia
            if person.entity_id in pending.deaths: 
                continue

            # INTEGRACIÓN COGNITIVA: Respetamos el periodo refractario mental.
            # Evita que un agente tome múltiples decisiones extremas consecutivas.
            memory = getattr(person, 'memory', {})
            if memory.get("rebellion_cooldown", 0.0) > 0:
                continue

            temperament = person.genome.temperament
            sociability = person.genome.sociability
            
            # Tasa base diaria individual:
            # Agentes impulsivos (alto temperamento) y asociales (baja sociabilidad) 
            # son más propensos a tomar decisiones de ruptura con su entorno.
            daily_rate = fw_cfg.base_daily_chance * (1.0 + (temperament * 0.6) - (sociability * 0.3))
            daily_rate = max(0.0001, min(1.0, daily_rate))

            # ACCIÓN 1: Divorcio Espontáneo
            if person.partner_id is not None and temperament > fw_cfg.divorce_temperament_threshold:
                # Utilizamos la fórmula de Poisson para probabilidades continuas
                divorce_rate = daily_rate * fw_cfg.divorce_chance_multiplier
                total_divorce_chance = 1.0 - math.exp(-divorce_rate * delta_days)
                
                if random.random() < total_divorce_chance:
                    pending.register_divorce(person.entity_id, person.partner_id)
                    self._apply_cognitive_cooldown(person)
                    continue

            # ACCIÓN 2: Migración
            density = context.get_local_pressure(person.x, person.y)
            is_overcrowded = density > fw_cfg.migration_density_threshold
            
            # La migración por hacinamiento es una huida inmediata por estrés.
            # La migración social (baja sociabilidad) obedece a un deseo acumulado.
            if is_overcrowded:
                self._execute_migration(person, state, pending, fw_cfg.migration_radius, context)
                self._apply_cognitive_cooldown(person)
                continue
            elif sociability < fw_cfg.migration_sociability_threshold:
                migration_rate = daily_rate * fw_cfg.migration_chance_multiplier
                total_migration_chance = 1.0 - math.exp(-migration_rate * delta_days)
                
                if random.random() < total_migration_chance:
                    self._execute_migration(person, state, pending, fw_cfg.migration_radius, context)
                    self._apply_cognitive_cooldown(person)
                    continue

            # ACCIÓN 3: Rebelión Reproductiva
            # Una decisión biológica espontánea de rechazar el límite normativo de natalidad
            if getattr(person, 'children_count', 0) >= fw_cfg.fertility_rebellion_children_threshold and temperament > fw_cfg.fertility_rebellion_temperament_threshold:
                total_rebellion_chance = 1.0 - math.exp(-daily_rate * delta_days)
                
                if random.random() < total_rebellion_chance:
                    # TODO (Arquitectura): Idealmente esta mutación interna debería ser 
                    # interceptada a través del PendingChanges.register_trait_mutation()
                    person.is_free_will_fertile = True
                    self._apply_cognitive_cooldown(person)

    def _apply_cognitive_cooldown(self, person: Any) -> None:
        """Aplica un estado de shock/satisfacción bloqueando nuevas decisiones un tiempo."""
        if hasattr(person, 'memory'):
            # El agente descansa de decisiones radicales durante 1 año biológico
            person.memory["rebellion_cooldown"] = 365.0

    def _execute_migration(self, person: Any, state: WorldState, 
                           pending: PendingChanges, radius: int, 
                           context: EnvironmentContext) -> None:
        """Calcula y registra un movimiento de migración topológicamente válido."""
        memory = getattr(person, 'memory', {})
        preferred = memory.get("preferred_sector")
        
        # Integración de Libre Albedrío + Memoria Cognitiva
        # Si el agente fue próspero en otro sector, intentará volver a él
        if preferred is not None:
            # Apunta al centro aproximado del sector preferido
            target_x = (preferred[0] * context.sector_size) + (context.sector_size // 2)
            target_y = (preferred[1] * context.sector_size) + (context.sector_size // 2)
        else:
            # Migración a ciegas
            target_x = person.x + random.randint(-radius, radius)
            target_y = person.y + random.randint(-radius, radius)
            
        # Clamping para no salirse del mapa
        new_x = max(0, min(state.width - 1, target_x))
        new_y = max(0, min(state.height - 1, target_y))
        
        pending.register_movement(person.entity_id, new_x, new_y)