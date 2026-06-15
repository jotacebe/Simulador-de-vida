"""Módulo responsable de la evolución a largo plazo de las relaciones interpersonales."""

import random
import math  
import logging
from typing import Any, List, Optional
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class RelationshipSystem:
    """Gestiona la maduración de relaciones aplicando selección sexual y social."""

    def __init__(self, config: SimulationConfig, ancestry_queries: Any = None) -> None:
        """Inicializa el sistema vinculándolo a la configuración."""
        self.config = config
        self.ancestry_queries = ancestry_queries
        self.logger = logging.getLogger("RelationshipSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa las transiciones relacionales dictadas por la presión social."""
        persons = state.get_all_persons()
        self._try_form_relationships(persons, pending, state, delta_days, context)
        self._try_marry_couples(persons, pending, state, delta_days, context)

    def get_social_anchor(self, person: Any, state: WorldState) -> Optional[Any]:
        """Devuelve el objetivo social (pareja) hacia el cual un agente debe gravitar."""
        partner_id = getattr(person, 'partner_id', None)
        if partner_id:
            return state.get_person_by_id(partner_id)
        return None

    def _try_form_relationships(self, persons: List[Any], pending: PendingChanges, 
                                state: WorldState, delta_days: float, 
                                context: EnvironmentContext) -> None:
        """Lógica de emparejamiento preliminar (noviazgo)."""
        pass 

    def _try_marry_couples(self, persons: List[Any], pending: PendingChanges, 
                           state: WorldState, delta_days: float, 
                           context: EnvironmentContext) -> None:
        """Convierte relaciones ya establecidas en matrimonios formales."""
        rel_cfg = self.config.relationships
        processed = set()
        
        for p1 in persons:
            if p1.entity_id in pending.deaths:
                continue

            partner_id = getattr(p1, 'partner_id', None)
            if partner_id and getattr(p1, 'marital_status', 'soltero') == "soltero":
                
                couple_key = tuple(sorted([p1.entity_id, partner_id]))
                if couple_key in processed: 
                    continue
                processed.add(couple_key)

                p2 = state.get_person_by_id(partner_id)
                if not p2 or getattr(p2, 'marital_status', '') == "casado" or p2.entity_id in pending.deaths: 
                    continue

                stability_score = max(0.1, 1.0 - ((p1.genome.temperament + p2.genome.temperament) / 2.0))
                
                # 2. PRESIÓN DEMOGRÁFICA (Edad) centralizada
                avg_age_days = (p1.age + p2.age) / 2.0
                age_pressure = max(0.0, (avg_age_days - rel_cfg.ideal_marriage_age_days) / 365.0)
                
                social_trait_pressure = (p1.genome.sociability + p2.genome.sociability) / 2.0
                pressure = context.get_local_pressure(p1.x, p1.y)
                
                total_social_pressure = (age_pressure * 0.4) + (social_trait_pressure * 0.3) + (min(2.0, pressure) * 0.3)

                # Probabilidad centralizada
                final_daily_rate = rel_cfg.daily_marriage_rate * stability_score * (1.0 + total_social_pressure)
                marriage_chance = 1.0 - math.exp(-final_daily_rate * delta_days)
                
                if random.random() < marriage_chance:
                    pending.register_marriage(p1.entity_id, p2.entity_id)