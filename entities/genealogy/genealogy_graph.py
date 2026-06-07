"""
Ruta: entities/genealogy/genealogy_graph.py
"""
from typing import Dict, Set
from entities.genealogy.genealogy_node import GenealogyNode

class GenealogyGraph:
    def __init__(self):
        self.nodes: Dict[int, GenealogyNode] = {}

    def get_node(self, entity_id: int) -> GenealogyNode:
        if entity_id not in self.nodes:
            self.nodes[entity_id] = GenealogyNode(entity_id)
        return self.nodes[entity_id]

    def register_parentage(self, parent_id: int, child_id: int):
        parent_node = self.get_node(parent_id)
        child_node = self.get_node(child_id)
        
        parent_node.add_child(child_id)
        child_node.add_parent(parent_id)

    def get_ancestors(self, entity_id: int, generation_limit: int = 3) -> Set[int]:
        """Busca ancestros hasta un límite de generaciones para evitar bucles infinitos."""
        ancestors = set()
        if generation_limit <= 0:
            return ancestors
        
        node = self.nodes.get(entity_id)
        if node:
            for parent_id in node.parents:
                ancestors.add(parent_id)
                ancestors.update(self.get_ancestors(parent_id, generation_limit - 1))
        return ancestors

    def are_related(self, id_a: int, id_b: int) -> bool:
        """Comprueba si comparten ancestros comunes."""
        if id_a == id_b: return True
        ancestors_a = self.get_ancestors(id_a)
        ancestors_b = self.get_ancestors(id_b)
        
        # Si hay intersección, son parientes
        return not ancestors_a.isdisjoint(ancestors_b)