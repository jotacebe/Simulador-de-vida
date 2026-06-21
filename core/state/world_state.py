"""Módulo de Estado Global Determinista de la Simulación.

Responsabilidad: 
Mantener la fuente de verdad de las entidades físicas. Extrae los datos del 
búfer transaccional ('pending') y los consolida alterando los objetos en memoria 
una vez por ciclo. Dispara eventos para la interfaz o métricas.
"""

import logging
from typing import Any, Optional, List, Dict

from entities.person.person import Person
from core.config.simulation_config import SimulationConfig
from systems.environment.epidemiological_map import EpidemiologicalMap
from core.state.world_grid import WorldGrid

# Asumiendo que estos eventos existen en tu directorio de 'events'
from events.population.person_born import PersonBornEvent
from events.population.person_died import PersonDiedEvent
from events.population.marriage_created import MarriageCreatedEvent
from events.population.divorce_occurred import DivorceOccurredEvent
from events.population.adoption_completed import AdoptionCompletedEvent

class WorldState:
    """Contenedor de la realidad simulada. Garantiza aislamiento en la lectura."""

    def __init__(self, config: SimulationConfig, width: int, height: int) -> None:
        self.logger = logging.getLogger("WorldState")
        self.config = config
        self.width = width
        self.height = height
        
        self.persons: Dict[int, Person] = {}      
        self._last_entity_id: int = 0 
        
        self.world_grid = WorldGrid(width, height)
        self.epidemiological_map = EpidemiologicalMap(config.environment.max_viral_load)
        self.world_days_elapsed: float = 0.0
        
    def get_next_entity_id(self) -> int:
        """Genera de forma segura e incremental el ID único para nuevos agentes."""
        self._last_entity_id += 1
        return self._last_entity_id

    def add_person(self, person: Person) -> None:
        """Registra una nueva entidad en el plano físico del mundo."""
        self.persons[person.entity_id] = person
        if person.entity_id > self._last_entity_id:
            self._last_entity_id = person.entity_id

    def get_person(self, entity_id: int) -> Optional[Person]:
        """Devuelve una persona por su ID con máxima eficiencia de acceso O(1)."""
        return self.persons.get(entity_id)
        
    def get_person_by_id(self, entity_id: int) -> Optional[Person]:
        """Alias de compatibilidad para evitar roturas de código heredado."""
        return self.get_person(entity_id)

    def get_all_persons(self) -> List[Person]:
        """Retorna un volcado instantáneo de todos los agentes vivos."""
        return list(self.persons.values())

    def apply_commit(self, pending: Any, event_bus: Any = None, current_tick: int = 0) -> None:
        """Aplica los cambios del búfer de forma atómica (Fase de Consolidación).
        
        Orden de ejecución crítico para prevenir corrupción:
        1. Muertes (Liberación de memoria y referencias).
        2. Envejecimiento (Desgaste celular).
        3. Salud Médica (Infecciones virales y recuperación).
        4. Fisiología Reproductiva (Nacimientos y Embarazos).
        5. Reestructuración legal (Adopciones, Rupturas, Matrimonios).
        6. Físicas Espaciales (Desplazamientos).
        """
        
        # 1. MUERTES: Eliminamos la referencia física primero para liberar memoria
        for entity_id, reason in pending.deaths.items():
            if entity_id in self.persons:
                p = self.persons.pop(entity_id)
                if event_bus:
                    # 'reason' ahora incluye el diagnóstico forense detallado del MortalitySystem
                    event_bus.publish(PersonDiedEvent(entity_id, int(p.age), reason, current_tick))

        # 2. ENVEJECIMIENTO FÍSICO
        for entity_id, days in pending.age_increments.items():
            person = self.get_person(entity_id)
            if person:
                person.add_age(days)

        # 3. SALUD MÉDICA AVANZADA (Contagios con Pathogens y Recuperaciones)
        for entity_id, pathogen in pending.infections:
            p = self.get_person(entity_id)
            if p:
                p.infect(pathogen)
                
        for entity_id, pathogen_id in pending.recoveries:
            p = self.get_person(entity_id)
            if p:
                p.recover(pathogen_id)

        # 4. EMBARAZOS Y NACIMIENTOS
        for entity_id, data in pending.pregnancy_updates.items():
            madre = self.get_person(entity_id)
            if madre:
                madre.update_pregnancy(
                    data["is_pregnant"], 
                    data.get("pregnancy_days", 0.0),
                    data.get("litter_size", 1)
                )
                # Gestión de abortos por estrés
                if data.get("failed_increment", 0) > 0:
                    for _ in range(data["failed_increment"]):  
                        madre.add_failed_pregnancy()

        for data in pending.births:
            new_id = self.get_next_entity_id()
            baby_genome = data.get("genome")
            
            # Instanciación con inyección multiespecie extraída del genoma
            newborn = Person(
                config=self.config,
                entity_id=new_id, 
                x=data["x"], 
                y=data["y"], 
                age=0.0, 
                genome=baby_genome,
                species=getattr(baby_genome, 'species_baseline', 'human')
            )
            
            mother_id = data["mother_id"]
            father_id = data["father_id"]
            newborn.set_parents(mother_id, father_id)
            self.add_person(newborn)
                            
            madre = self.get_person(mother_id)
            padre = self.get_person(father_id) if father_id else None
            
            if madre: madre.add_child()
            if padre: padre.add_child()
            
            if event_bus:
                gender = getattr(newborn, 'gender', 'indefinido')
                event_bus.publish(PersonBornEvent(new_id, mother_id, father_id, data["x"], data["y"], gender, current_tick))

        # 5. ADOPCIONES LEGALES
        for adoption in pending.adoptions:
            child = self.get_person(adoption["child_id"])
            parent_a = self.get_person(adoption["parent_a"])
            parent_b = self.get_person(adoption["parent_b"]) if adoption["parent_b"] else None

            if child and parent_a:
                parent_a.add_child()
                if parent_b: parent_b.add_child()
                child.set_parents(parent_a.entity_id, parent_b.entity_id if parent_b else None)
                if event_bus:
                    event_bus.publish(AdoptionCompletedEvent(child.entity_id, parent_a.entity_id, getattr(parent_b, 'entity_id', None), current_tick))
        
        # 6. RELACIONES Y MOVIMIENTOS ESPACIALES
        for entity_id, (new_x, new_y) in pending.movements.items():
            p = self.get_person(entity_id)
            if p:
                p.set_position(new_x, new_y)

        # Resolución simétrica de Divorcios y Viudedad
        for p_a_id, p_b_id in pending.divorces:
            pa = self.get_person(p_a_id)
            pb = self.get_person(p_b_id)
            
            if pa and pa.partner_id == p_b_id: pa.register_divorce()
            if pb and pb.partner_id == p_a_id: pb.register_divorce()
            
            if event_bus: 
                event_bus.publish(DivorceOccurredEvent(p_a_id, p_b_id, "separacion_natural", current_tick))

        # Resolución simétrica de Matrimonios (Garantiza integridad del grafo bidireccional)
        for p_a_id, p_b_id in pending.marriages.items():
            pa = self.get_person(p_a_id)
            pb = self.get_person(p_b_id)
            
            if pa and pb:
                pa.register_marriage(p_b_id)
                pb.register_marriage(p_a_id)
                
                if event_bus and p_a_id < p_b_id:
                    event_bus.publish(MarriageCreatedEvent(p_a_id, p_b_id, current_tick))