"""
Ruta: core/state/world_state.py
Responsabilidad: Mantener el estado determinista de la simulación.
Emite eventos oficiales únicamente tras aplicar los cambios confirmados.
"""
from entities.person.person import Person
from entities.person.genome import Genome  # IMPORTANTE: Importamos el nuevo Genome
from events.population.person_born import PersonBornEvent
from events.population.person_died import PersonDiedEvent
from events.population.marriage_created import MarriageCreatedEvent
from events.population.divorce_occurred import DivorceOccurredEvent
from events.population.adoption_completed import AdoptionCompletedEvent
from core.config.simulation_config import SimulationConfig
from systems.environment.epidemiological_map import EpidemiologicalMap 
from typing import Any, Optional
from core.state.world_grid import WorldGrid

class WorldState:
    def __init__(self, config: SimulationConfig, width: int, height: int):
        self.config = config
        self.width = width
        self.height = height
        self.persons = {}      
        self.deceased_archive = [] 
        self.historical_registry = {}
        self._last_entity_id = 0 
        self.world_grid = WorldGrid(width, height)
        self.genealogy_system: Any = None
        self.epidemiological_map = EpidemiologicalMap()
        self.world_days_elapsed = 0.0
        
    def add_person(self, person: Person) -> None:
        self.persons[person.entity_id] = person
        self.historical_registry[person.entity_id] = person
        if person.entity_id > self._last_entity_id:
            self._last_entity_id = person.entity_id

    def get_person(self, entity_id: int) -> Optional[Person]:
        return self.persons.get(entity_id)
        
    def get_historical_person(self, entity_id: int) -> Optional[Person]:
        return self.historical_registry.get(entity_id)

    def get_all_persons(self) -> list:
        return list(self.persons.values())
    
    def get_person_by_id(self, entity_id: int) -> Optional[Person]:
        """Devuelve una persona por su ID con máxima eficiencia O(1)."""
        return self.persons.get(entity_id)

    def apply_commit(self, pending, event_bus=None, current_tick: int = 0) -> None:
        """
        Aplica los cambios confirmados por los sistemas al estado del mundo 
        de forma atómica y ordenada.
        """
        
        # 1. MUERTES: Primero, para evitar que agentes fallecidos procesen lógica biológica.
        for entity_id in pending.deaths:
            if entity_id in self.persons:
                p = self.persons.pop(entity_id)
                self.deceased_archive.append(p)
                if event_bus:
                    cause = "enfermedad" if p.is_sick else "causas_naturales"
                    event_bus.publish(PersonDiedEvent(entity_id, p.age, cause, current_tick))

        # 2. INCREMENTOS DE EDAD: El tiempo avanza sobre la población viva.
        # Los agentes recalculan sus flags (is_adult, is_senior) internamente.
        for entity_id, days in pending.age_increments.items():
            person = self.get_person_by_id(entity_id)
            if person:
                person.add_age(days)

        # 3. SALUD: Infectar o curar agentes vivos.
        for entity_id in pending.infections:
            p = self.get_person(entity_id)
            if p:
                p.set_health_state("enfermo")
                
        for entity_id in getattr(pending, 'recoveries', []):
            p = self.get_person(entity_id)
            if p:
                p.set_health_state("sano")

        # 4. EMBARAZOS Y NACIMIENTOS
        # Procesamos la actualización de estados de gestación
        for entity_id, data in pending.pregnancy_updates.items():
            madre = self.get_person(entity_id)
            if madre:
                madre.update_pregnancy(data["is_pregnant"], data.get("pregnancy_days", 0.0))
                if "failed_increment" in data and data["failed_increment"] > 0:
                    for _ in range(data["failed_increment"]):  
                        madre.add_failed_pregnancy()

        # Procesamos nacimientos
        for data in pending.births:
            self._last_entity_id += 1
            new_id = self._last_entity_id
            baby_genome = data.get("genome")
            
            newborn = Person(
                entity_id=new_id, 
                age=0.0, 
                x=data["x"], 
                y=data["y"], 
                genome=baby_genome
            )
            newborn.set_parents(data["mother_id"], data["father_id"])
            self.add_person(newborn)
                            
            madre = self.get_historical_person(data["mother_id"])
            padre = self.get_historical_person(data["father_id"]) if data["father_id"] is not None else None
            if madre: madre.add_child()
            if padre: padre.add_child()
            
            if event_bus:
                gender = getattr(newborn, 'gender', 'indefinido')
                event_bus.publish(PersonBornEvent(new_id, data["mother_id"], data["father_id"], data["x"], data["y"], gender, current_tick))

        # 5. ADOPCIONES: Basado en la edad actualizada en el paso 2.
        for adoption in pending.adoptions:
            child = self.get_person(adoption["child_id"])
            parent_a = self.get_person(adoption["parent_a"])
            parent_b = self.get_person(adoption["parent_b"]) if adoption["parent_b"] else None

            if child and parent_a:
                parent_a.add_child()
                if parent_b: parent_b.add_child()
                child.set_parents(parent_a.entity_id, parent_b.entity_id if parent_b else None)
                if event_bus:
                    event_bus.publish(AdoptionCompletedEvent(child.entity_id, parent_a.entity_id, parent_b.entity_id if parent_b else None, current_tick))
        
        # 6. RELACIONES Y MOVIMIENTOS
        for entity_id, (new_x, new_y) in pending.movements.items():
            p = self.get_person(entity_id)
            if p:
                p.set_position(new_x, new_y)

        for p_a_id, p_b_id in pending.divorces:
            pa = self.get_person(p_a_id)
            pb = self.get_person(p_b_id)
            if pa and pa.partner_id == p_b_id: pa.register_divorce()
            if pb and pb.partner_id == p_a_id: pb.register_divorce()
            if event_bus: event_bus.publish(DivorceOccurredEvent(p_a_id, p_b_id, "separacion_natural", current_tick))

        for p_a_id, p_b_id in pending.marriages.items():
            pa = self.get_person(p_a_id)
            pb = self.get_person(p_b_id)
            if pa and pb:
                pa.register_marriage(p_b_id)
                if event_bus and p_a_id < p_b_id:
                    event_bus.publish(MarriageCreatedEvent(p_a_id, p_b_id, current_tick))