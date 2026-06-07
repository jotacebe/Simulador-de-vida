"""
Ruta: systems/birth/birth_system.py
Responsabilidad: Lógica de reproducción y registro de nacimientos.
"""
import random
from typing import Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from entities.person.person import Person

class BirthSystem:
    def __init__(self, genealogy_system: Any):
        self.genealogy_system = genealogy_system
        self.birth_chance = 0.10 # Aumentado a 10% para combatir la extinción

    def process(self, state: WorldState, pending: PendingChanges, delta_days: int) -> None:
        persons = state.get_all_persons()
        for person in persons:
            if person.partner_id is None or person.gender != "F":
                continue
            if not (18 <= person.age <= 45):
                continue
            if random.random() < self.birth_chance:
                partner = state.get_person_by_id(person.partner_id)
                if partner:
                    self._register_birth_intent(person, partner, state, pending)

    def _register_birth_intent(self, mother: Person, father: Person, state: WorldState, pending: PendingChanges) -> None:
        new_id = state.get_next_entity_id()
        child = Person(new_id, 0, mother.x, mother.y, father_id=father.entity_id, mother_id=mother.entity_id)
        
        self.genealogy_system.register_birth(child, father.entity_id, mother.entity_id)
        mother.children_count += 1
        father.children_count += 1
        
        pending.register_birth(child)