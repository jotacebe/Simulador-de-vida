"""
Ruta: systems/environment/environment_system.py
Responsabilidad: Gestionar el estrés ambiental por densidad de población 
                 de forma independiente a la duración del tick.
"""
import random
from systems.environment.environment_context import EnvironmentContext
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

class EnvironmentSystem:
    def __init__(self, config, sector_size: int = 10, max_agents_per_sector: int = 8):
        self.config = config
        self.sector_size = sector_size
        self.max_agents_per_sector = max_agents_per_sector
        # Factor base diario de mortalidad por hacinamiento
        self.lethal_stress_factor = 0.01 

    def process(self, state: WorldState, pending: PendingChanges, delta_days: int, context: EnvironmentContext) -> None:
        for sector_coords, agents_in_sector in context.sector_map.items():
            current_sector_pop = len(agents_in_sector)
            
            if current_sector_pop <= self.max_agents_per_sector:
                continue
            
            # Calculamos el ratio de exceso
            excess_ratio = (current_sector_pop - self.max_agents_per_sector) / self.max_agents_per_sector
            
            # Probabilidad diaria de morir por este sector específico
            daily_death_chance = self.lethal_stress_factor * excess_ratio
            
            # Probabilidad acumulada de morir durante el periodo 'delta_days'
            # P(morir) = 1 - P(sobrevivir_un_dia)^dias
            total_death_chance = 1 - ((1 - daily_death_chance) ** delta_days)

            for person in agents_in_sector:
                if person.entity_id not in pending.deaths:
                    if random.random() < total_death_chance:
                        pending.register_death(person.entity_id, reason="Hacinamiento")