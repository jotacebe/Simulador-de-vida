"""
Ruta: systems/relationships/relationship_system.py
Responsabilidad: Gestión de cortejo y matrimonios normalizada por tiempo real (días).
                 Aplica Selección Sexual basada en Sociabilidad y Temperamento.
"""
import random
import math  
from typing import Any, List
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from entities.person.person import Person
from systems.environment.environment_context import EnvironmentContext

class RelationshipSystem:
    def __init__(self, config, ancestry_queries: Any = None):
        self.config = config
        self.ancestry_queries = ancestry_queries
        
        # Extracción de la tasa base diaria
        repro_cfg = getattr(config, 'relationships', {})
        if isinstance(repro_cfg, dict):
            self.daily_base_rate = repro_cfg.get("daily_marriage_rate", 0.00137)
        else:
            self.daily_base_rate = getattr(repro_cfg, "daily_marriage_rate", 0.00137)

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        persons = state.get_all_persons()
        # El flujo natural de las relaciones
        self._try_form_relationships(persons, pending, state, delta_days, context)
        self._try_marry_couples(persons, pending, state, delta_days, context)

    def _try_form_relationships(self, persons: List[Person], pending: PendingChanges, state: WorldState, delta_days: float, context: EnvironmentContext) -> None:
        """
        SELECCIÓN SEXUAL (Evolución): Aquí es donde el gen 'sociability' brilla.
        Si un agente tiene baja sociabilidad, le cuesta encontrar pareja. 
        Sin pareja, no hay reproducción. El gen se extingue.
        """
        # Cuando insertes tu lógica de cortejo aquí, asegúrate de aplicar la presión genética.
        # Ejemplo matemático de evolución:
        # base_chance = 0.05
        # courtship_chance = 1.0 - math.exp(-(base_chance * person.genome.sociability) * delta_days)
        pass 

    def _try_marry_couples(self, persons: List[Person], pending: PendingChanges, state: WorldState, delta_days: float, context: EnvironmentContext) -> None:
        processed = set()
        
        # Parámetros operativos en días 
        dias_ideal_matrimonio = 8395.0 # ~23 años
        dias_normalizacion = 365.0 

        for p1 in persons:
            # Filtramos solo a los que están "saliendo" pero no casados
            if p1.partner_id and p1.marital_status == "soltero":
                couple_key = tuple(sorted([p1.entity_id, p1.partner_id]))
                if couple_key in processed: continue
                processed.add(couple_key)

                p2 = state.get_person_by_id(p1.partner_id)
                if not p2 or p2.marital_status == "casado": continue

                # 1. SELECCIÓN DE ESTABILIDAD (Temperamento)
                # Agentes con mal temperamento (< 1.0) reducen la estabilidad de la pareja, 
                # retrasando el matrimonio.
                stability_score = max(0.1, 1.0 - ((p1.genome.temperament + p2.genome.temperament) / 2.0))
                
                # Todo operando sobre la variable `age` purificada (días)
                avg_age_days = (p1.age + p2.age) / 2.0
                age_pressure = max(0.0, (avg_age_days - dias_ideal_matrimonio) / dias_normalizacion)
                
                # 2. SELECCIÓN SEXUAL (Sociabilidad)
                # Agentes altamente sociables se casan más rápido, accediendo antes a la reproducción.
                social_trait_pressure = (p1.genome.sociability + p2.genome.sociability) / 2.0
                
                pressure = 0.0
                if hasattr(context, 'get_local_pressure'):
                    pressure = context.get_local_pressure(p1.x, p1.y)
                
                total_social_pressure = (age_pressure * 0.4) + (social_trait_pressure * 0.3) + (min(2.0, pressure) * 0.3)

                # Cálculo temporal puro con presión evolutiva integrada
                final_daily_rate = self.daily_base_rate * stability_score * (1.0 + total_social_pressure)
                
                # Probabilidad exacta acumulada en el periodo delta_days
                marriage_chance = 1.0 - math.exp(-final_daily_rate * delta_days)
                
                if random.random() < marriage_chance:
                    pending.register_marriage(p1.entity_id, p2.entity_id)