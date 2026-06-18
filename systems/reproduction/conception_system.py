"""Módulo responsable de la transición de estado hacia la gestación biológica.

Soporta estrategias reproductivas avanzadas: Partenogénesis, camadas (litters)
y selección de rasgos por especie.
"""

import random
import math
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class ConceptionSystem:
    """Gestiona la iniciación de la gestación multiespecie."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_species_traits(self, species: str) -> dict:
        """Provee los perfiles reproductivos (A migrar a SimulationConfig futuro)."""
        profiles = {
            "human": {
                "parthenogenesis_chance": 0.0, 
                "litter_size_min": 1, 
                "litter_size_max": 1, 
                "gestation_days": self.config.reproduction.pregnancy_duration_days
            },
            "elf": {"parthenogenesis_chance": 0.0, "litter_size_min": 1, "litter_size_max": 1, "gestation_days": 730.0},
            "goblin": {"parthenogenesis_chance": 0.05, "litter_size_min": 3, "litter_size_max": 6, "gestation_days": 120.0},
            "dragon": {"parthenogenesis_chance": 0.1, "litter_size_min": 1, "litter_size_max": 3, "gestation_days": 1200.0}
        }
        return profiles.get(species, profiles["human"])

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        
        rep_cfg = self.config.reproduction
        time_cfg = self.config.time
        
        daily_rate = rep_cfg.base_conception_chance / time_cfg.days_per_year
        base_prob_period = 1.0 - math.exp(-daily_rate * delta_days)

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths or getattr(person, 'is_pregnant', False):
                continue

            if not person.can_reproduce():
                continue

            traits = self._get_species_traits(person.species)
            partner_id = person.partner_id

            # 1. REPRODUCCIÓN ASEXUAL (Partenogénesis)
            if partner_id is None:
                if traits["parthenogenesis_chance"] > 0 and random.random() < traits["parthenogenesis_chance"]:
                    litter_size = random.randint(traits["litter_size_min"], traits["litter_size_max"])
                    pending.register_pregnancy_update(
                        person.entity_id, True, 0.0, failed_increment=0, litter_size=litter_size
                    )
                    self.logger.debug(f"Concepción asexual iniciada: Agente {person.entity_id} (Camada: {litter_size})")
                continue

            # 2. REPRODUCCIÓN SEXUAL
            partner = state.get_person_by_id(partner_id)
            if partner and partner.entity_id not in pending.deaths and partner.can_reproduce():
                
                fertility_modifier = (person.genome.fertility + partner.genome.fertility) / 2.0
                k_strategy_penalty = (person.genome.longevity + partner.genome.longevity) / 2.0
                energy_multiplier = min(person.emotions["energy"], partner.emotions["energy"])

                final_chance = (base_prob_period * fertility_modifier * energy_multiplier) / k_strategy_penalty
                
                if random.random() < final_chance:
                    litter_size = random.randint(traits["litter_size_min"], traits["litter_size_max"])
                    pending.register_pregnancy_update(
                        person.entity_id, True, 0.0, failed_increment=0, litter_size=litter_size
                    )
                    self.logger.debug(f"Concepción sexual iniciada: Agente {person.entity_id} (Camada: {litter_size})")