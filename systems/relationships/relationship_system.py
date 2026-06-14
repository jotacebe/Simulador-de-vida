"""Módulo responsable de la evolución a largo plazo de las relaciones interpersonales."""

import random
import math  
import logging
from typing import Any, List
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

    def _try_form_relationships(self, persons: List[Any], pending: PendingChanges, 
                                state: WorldState, delta_days: float, 
                                context: EnvironmentContext) -> None:
        """Lógica de emparejamiento preliminar (noviazgo).
        
        Nota de Arquitectura: Si MarriageSystem maneja el emparejamiento inicial, 
        este bloque puede quedar como hook futuro para dinámicas de amistad pura.
        """
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

            # Identificamos a los que tienen pareja (noviazgo) pero no están casados
            partner_id = getattr(p1, 'partner_id', None)
            if partner_id and getattr(p1, 'marital_status', 'soltero') == "soltero":
                
                couple_key = tuple(sorted([p1.entity_id, partner_id]))
                if couple_key in processed: 
                    continue
                processed.add(couple_key)

                p2 = state.get_person_by_id(partner_id)
                if not p2 or getattr(p2, 'marital_status', '') == "casado" or p2.entity_id in pending.deaths: 
                    continue

                # 1. SELECCIÓN DE ESTABILIDAD (Temperamento)
                # Temperamentos bajos reducen la estabilidad y retrasan la formalización.
                stability_score = max(0.1, 1.0 - ((p1.genome.temperament + p2.genome.temperament) / 2.0))
                
                # 2. PRESIÓN DEMOGRÁFICA (Edad)
                avg_age_days = (p1.age + p2.age) / 2.0
                age_pressure = max(0.0, (avg_age_days - rel_cfg.ideal_marriage_age_days) / 365.0)
                
                # 3. SELECCIÓN SEXUAL (Sociabilidad)
                social_trait_pressure = (p1.genome.sociability + p2.genome.sociability) / 2.0
                
                # 4. PRESIÓN DEL ENTORNO LOCAL
                pressure = context.get_local_pressure(p1.x, p1.y)
                
                # Fórmula de estrés relacional
                total_social_pressure = (age_pressure * 0.4) + (social_trait_pressure * 0.3) + (min(2.0, pressure) * 0.3)

                # Cálculo temporal de la tasa diaria
                final_daily_rate = rel_cfg.daily_marriage_rate * stability_score * (1.0 + total_social_pressure)
                
                # Probabilidad exacta acumulada
                marriage_chance = 1.0 - math.exp(-final_daily_rate * delta_days)
                
                if random.random() < marriage_chance:
                    pending.register_marriage(p1.entity_id, p2.entity_id)