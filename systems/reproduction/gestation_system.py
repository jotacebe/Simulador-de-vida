"""Módulo responsable del avance de la gestación y la recombinación genética."""

import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig
from typing import Any

class GestationSystem:
    """Gestiona el tiempo de gestación y la ejecución del nacimiento."""

    def __init__(self, config: SimulationConfig, evolution_engine=None) -> None:
        self.config = config
        self.evolution_engine = evolution_engine
        self.logger = logging.getLogger("GestationSystem")
        
    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Avanza los embarazos y dispara el nacimiento al alcanzar el umbral."""
        
        rep_cfg = self.config.reproduction
        
        for person in state.get_all_persons():
            # Filtro: debe estar embarazada y viva
            if person.entity_id in pending.deaths or not getattr(person, 'is_pregnant', False):
                continue

            # Avance temporal del estado de gestación
            current_days = getattr(person, 'pregnancy_days', 0.0)
            new_days = current_days + delta_days
            
            if new_days >= rep_cfg.pregnancy_duration_days:
                self._execute_birth(person, state, pending)
            else:
                # El embarazo continúa: registramos el progreso en el búfer
                pending.register_pregnancy_update(
                    person.entity_id, 
                    is_pregnant=True, 
                    pregnancy_days=new_days
                )

    def _execute_birth(self, mother: Any, state: WorldState, pending: PendingChanges) -> None:
        """Culmina el ciclo de gestación y registra el nacimiento."""
        
        partner = state.get_person_by_id(mother.partner_id) if mother.partner_id else None
        
        # Lógica de recombinación delegada al motor de evolución
        # Esto evita que el sistema de gestación tenga que conocer la estructura del genoma
        father_genome = partner.genome if partner else None
        baby_genome = mother.genome.combine(father_genome) if self.evolution_engine is None \
                      else self.evolution_engine.recombine(mother.genome, father_genome)
        
        # Disparo del evento de nacimiento
        pending.register_birth(
            mother_id=mother.entity_id,
            father_id=mother.partner_id,
            genome=baby_genome,
            x=mother.x,
            y=mother.y
        )
        
        # Reinicio del estado biológico de la madre
        pending.register_pregnancy_update(mother.entity_id, is_pregnant=False, pregnancy_days=0.0)
        self.logger.info(f"Nacimiento completado: Madre {mother.entity_id}")