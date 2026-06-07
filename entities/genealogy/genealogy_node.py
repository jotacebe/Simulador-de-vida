"""
Ruta: entities/genealogy/genealogy_node.py
"""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GenealogyNode:
    entity_id: int
    parents: List[int] = field(default_factory=list)
    children: List[int] = field(default_factory=list)
    spouse_id: Optional[int] = None

    def add_parent(self, parent_id: int):
        if parent_id not in self.parents:
            self.parents.append(parent_id)

    def add_child(self, child_id: int):
        if child_id not in self.children:
            self.children.append(child_id)