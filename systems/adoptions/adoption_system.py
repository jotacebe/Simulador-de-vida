"""
Ruta: systems/adoptions/adoption_system.py
Responsabilidad: Identificar huérfanos y asignar familias mediante un proceso 
                 transaccional operando estrictamente en días de vida.
"""
import logging
from typing import List, Set
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from entities.person.person import Person
from systems.environment.environment_context import EnvironmentContext

class AdoptionSystem:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("AdoptionSystem")
        
        # Umbrales biológicos definidos directamente en días
        self.fallback_max_orphan_age_days = 6205.0   # 17 años
        self.fallback_min_adoptive_age_days = 9125.0 # 25 años

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        cfg = getattr(state.config, 'adoptions', getattr(state.config, 'adoption', {}))
        
        # Extracción segura de configuración temporal en días
        if isinstance(cfg, dict):
            max_orphan_age_days = cfg.get("max_orphan_age_days", self.fallback_max_orphan_age_days)
            min_adoptive_age_days = cfg.get("min_adoptive_age_days", self.fallback_min_adoptive_age_days)
        else:
            max_orphan_age_days = getattr(cfg, "max_orphan_age_days", self.fallback_max_orphan_age_days)
            min_adoptive_age_days = getattr(cfg, "min_adoptive_age_days", self.fallback_min_adoptive_age_days)

        all_persons = state.get_all_persons()

        # 1. DETECTAR HUÉRFANOS
        orphans: List[Person] = []
        for person in all_persons:
            if person.entity_id in pending.deaths:
                continue
            
            # Comparación puramente cronológica
            if person.age <= max_orphan_age_days:
                father_alive = person.father_id is not None and state.get_person_by_id(person.father_id) is not None
                mother_alive = person.mother_id is not None and state.get_person_by_id(person.mother_id) is not None
                
                if (person.father_id or person.mother_id) and not father_alive and not mother_alive:
                    orphans.append(person)

        if not orphans:
            return

        # 2. DETECTAR FAMILIAS ELEGIBLES
        eligible_parents: List[Person] = []
        seen_couples: Set[int] = set() 

        for person in all_persons:
            if person.entity_id in pending.deaths or person.entity_id in seen_couples: 
                continue
            
            # Validación de edad mínima requerida en días
            if person.age >= min_adoptive_age_days and person.marital_status == "casado" and person.partner_id is not None:
                if person.children_count < 3:
                    eligible_parents.append(person)
                    seen_couples.add(person.partner_id)

        if not eligible_parents:
            return

        # Ordenar familias por idoneidad social (usando el genoma)
        eligible_parents.sort(key=lambda p: p.genome.sociability, reverse=True)

        # 3. PROCESO DE ADOPCIÓN TRANSACCIONAL
        for orphan in orphans:
            if not eligible_parents:
                break 
            
            new_parent = eligible_parents[0]
            new_partner = state.get_person_by_id(new_parent.partner_id) if new_parent.partner_id else None

            # Registro en el búfer
            pending.register_adoption(
                child_id=orphan.entity_id,
                parent_a=new_parent.entity_id,
                parent_b=new_partner.entity_id if new_partner else None
            )

            # Registro de movimiento al hogar de los padres
            pending.register_movement(orphan.entity_id, new_parent.x, new_parent.y)
            eligible_parents.pop(0)

            self.logger.info(f"Adopción registrada: Menor {orphan.entity_id} asignado a {new_parent.entity_id}")