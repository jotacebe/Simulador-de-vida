"""
Ruta: systems/free_will/free_will_system.py
Responsabilidad: Decisiones autónomas probabilísticas normalizadas por tiempo continuo,
                 eliminando asimetrías temporales en sub-acciones.
"""
import random
import logging
from typing import Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

class FreeWillSystem:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("FreeWillSystem")
        self.base_daily_chance = 0.005 

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context) -> None:
        cfg = getattr(state.config, 'free_will', {})
        chance_modifier = cfg.get("base_chance", self.base_daily_chance) if isinstance(cfg, dict) else getattr(cfg, "base_chance", self.base_daily_chance)

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths: 
                continue

            temperament = person.genome.temperament
            sociability = person.genome.sociability
            
            # Modificador base diario individual
            individual_daily_chance = chance_modifier * (1.0 + (temperament * 0.6) - (sociability * 0.3))
            individual_daily_chance = max(0.0, min(1.0, individual_daily_chance))

            # ACCIÓN 1: Divorcio (Evaluado de manera continua si está casado y es impulsivo)
            if person.partner_id is not None and temperament > 0.75:
                # Tu balance original equivalía a un 10% de la probabilidad base de decisión
                daily_divorce_chance = individual_daily_chance * 0.1
                total_divorce_chance = 1.0 - ((1.0 - daily_divorce_chance) ** delta_days)
                
                if random.random() < total_divorce_chance:
                    pending.register_divorce(person.entity_id, person.partner_id)
                    continue  # Consume su acción de libre albedrío en este ciclo

            # ACCIÓN 2: Migración
            density = context.get_local_pressure(person.x, person.y)
            is_overcrowded = density > 1.6
            
            # Si hay hacinamiento, la migración es inmediata/determinista por estrés ambiental en el tick.
            # Si es por insatisfacción social, calculamos la probabilidad acumulada continua.
            if is_overcrowded:
                self._execute_migration(person, state, pending)
                continue
            elif sociability < 0.3:
                daily_migration_chance = individual_daily_chance * 0.2
                total_migration_chance = 1.0 - ((1.0 - daily_migration_chance) ** delta_days)
                
                if random.random() < total_migration_chance:
                    self._execute_migration(person, state, pending)
                    continue

            # ACCIÓN 3: Incumplimiento reproductivo (Decisión hormonal/ideológica espontánea)
            if person.children_count >= 3 and temperament > 0.7:
                total_fertility_toggle_chance = 1.0 - ((1.0 - individual_daily_chance) ** delta_days)
                if random.random() < total_fertility_toggle_chance:
                    person.is_free_will_fertile = True

    def _execute_migration(self, person: Any, state: WorldState, pending: PendingChanges) -> None:
        """Calcula y registra un movimiento de migración aleatorio dentro de los límites."""
        new_x = max(0, min(state.width - 1, person.x + random.randint(-12, 12)))
        new_y = max(0, min(state.height - 1, person.y + random.randint(-12, 12)))
        pending.register_movement(person.entity_id, new_x, new_y)