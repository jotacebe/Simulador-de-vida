"""Módulo responsable del avance de la gestación y partos múltiples."""

import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig
from typing import Any

class GestationSystem:
    """Gestiona el tiempo de gestación y la ejecución de partos."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _get_species_traits(self, species: str) -> dict:
        """Copia de seguridad local del perfil reproductivo."""
        profiles = {
            "human": {"gestation_days": self.config.reproduction.pregnancy_duration_days},
            "elf": {"gestation_days": 730.0},
            "goblin": {"gestation_days": 120.0},
            "dragon": {"gestation_days": 1200.0}
        }
        return profiles.get(species, profiles["human"])

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Avanza los embarazos y dispara nacimientos múltiples (camadas)."""
        
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths or not getattr(person, 'is_pregnant', False):
                continue

            traits = self._get_species_traits(person.species)
            current_days = getattr(person, 'pregnancy_days', 0.0)
            new_days = current_days + delta_days
            
            if new_days >= traits["gestation_days"]:
                # Recuperamos el tamaño de la camada guardada en la concepción
                litter_size = getattr(person, 'litter_size_gestating', 1)
                
                # Bucle de nacimientos simultáneos
                for _ in range(litter_size):
                    self._execute_birth(person, state, pending)
                
                # Saneamiento del estado biológico de la gestante
                pending.register_pregnancy_update(
                    person.entity_id, is_pregnant=False, pregnancy_days=0.0, failed_increment=0, litter_size=1
                )
            else:
                pending.register_pregnancy_update(
                    person.entity_id, True, new_days, failed_increment=0, litter_size=person.litter_size_gestating
                )

    def _execute_birth(self, mother: Any, state: WorldState, pending: PendingChanges) -> None:
        """Culmina la meiosis individual de una sola cría de la camada."""
        
        partner = state.get_person_by_id(mother.partner_id) if mother.partner_id else None
        
        # Si no hay partner, Genome.combine() aplicará Partenogénesis automáticamente
        father_genome = partner.genome if partner else None
        baby_genome = mother.genome.combine(father_genome)
        
        pending.register_birth(
            mother_id=mother.entity_id,
            father_id=mother.partner_id, # Puede ser None (Legalmente es correcto)
            genome=baby_genome,
            x=mother.x,
            y=mother.y
        )
        self.logger.info(f"Cría nacida: Madre {mother.entity_id} (Especie: {mother.species})")