"""Módulo responsable de la reasignación familiar de menores sin tutores vivos."""

import logging
from typing import List, Set
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from entities.person.person import Person
from systems.environment.environment_context import EnvironmentContext

class AdoptionSystem:
    """Identifica huérfanos y asigna familias mediante un proceso transaccional."""

    def __init__(self, config) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config
        self.logger = logging.getLogger("AdoptionSystem")
        # Se han eliminado los fallbacks internos; la fuente de verdad es self.config.adoptions

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Ejecuta el ciclo de adopciones operando estrictamente en días de vida."""
        
        # 1. ACCESO A CONFIGURACIÓN CENTRALIZADA
        # Extraemos directamente el objeto tipado, eliminando comprobaciones de diccionarios
        adoptions_cfg = self.config.adoptions
        all_persons = state.get_all_persons()

        # 2. DETECCIÓN DE HUÉRFANOS
        orphans: List[Person] = []
        for person in all_persons:
            # Filtro de integridad referencial: omitir entidades fallecidas
            if person.entity_id in pending.deaths:
                continue
            
            # Verificamos si cronológicamente es considerado menor de edad
            if person.age <= adoptions_cfg.max_orphan_age_days:
                # Comprobamos el estado vital actual de los progenitores biológicos
                father_alive = person.father_id is not None and state.get_person_by_id(person.father_id) is not None
                mother_alive = person.mother_id is not None and state.get_person_by_id(person.mother_id) is not None
                
                # Si la entidad tiene (o tuvo) padres, pero ninguno sigue con vida en el estado actual
                if (person.father_id or person.mother_id) and not father_alive and not mother_alive:
                    orphans.append(person)

        # Optimización: abortar ciclo temprano si no hay huérfanos en el ecosistema
        if not orphans:
            return

        # 3. DETECCIÓN DE FAMILIAS ELEGIBLES
        eligible_parents: List[Person] = []
        seen_couples: Set[int] = set() 

        for person in all_persons:
            # Omitimos fallecidos y cónyuges de familias ya procesadas (evita duplicar la candidatura de la pareja)
            if person.entity_id in pending.deaths or person.entity_id in seen_couples: 
                continue
            
            # Criterios de elegibilidad: edad mínima cumplida, matrimonio activo y capacidad familiar
            is_old_enough = person.age >= adoptions_cfg.min_adoptive_age_days
            is_married = person.marital_status == "casado" and person.partner_id is not None
            
            # Si cumplen los requisitos sociales y tienen menos de 3 hijos, entran en la bolsa
            if is_old_enough and is_married and person.children_count < 3:
                eligible_parents.append(person)
                seen_couples.add(person.partner_id)

        if not eligible_parents:
            return

        # 4. ORDENACIÓN POR IDONEIDAD SOCIAL (Genotipo Fenotípico)
        # Priorizamos a las familias con mayor expresión en el alelo de sociabilidad
        eligible_parents.sort(key=lambda p: p.genome.sociability, reverse=True)

        # 5. PROCESO DE ADOPCIÓN TRANSACCIONAL
        for orphan in orphans:
            # Si nos quedamos sin familias de acogida, detenemos las asignaciones de este tick
            if not eligible_parents:
                break 
            
            # Seleccionamos a la familia más idónea (la primera de la lista ordenada)
            new_parent = eligible_parents[0]
            new_partner = state.get_person_by_id(new_parent.partner_id) if new_parent.partner_id else None

            # Registramos la mutación social de forma segura en el búfer transaccional
            pending.register_adoption(
                child_id=orphan.entity_id,
                parent_a=new_parent.entity_id,
                parent_b=new_partner.entity_id if new_partner else None
            )

            # Movemos físicamente al menor a las coordenadas de su nuevo hogar
            pending.register_movement(orphan.entity_id, new_parent.x, new_parent.y)
            
            # Retiramos a la familia de la bolsa (límite de 1 adopción por familia por tick)
            eligible_parents.pop(0)

            self.logger.info(f"Adopción registrada: Menor {orphan.entity_id} asignado a familia {new_parent.entity_id}")