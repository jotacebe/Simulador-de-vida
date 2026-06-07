"""
Ruta: systems/genealogy/ancestry_queries.py
Responsabilidad: Servicio fachada para consultas de parentesco.
Ahora delega al motor centralizado GenealogySystem.
"""
from systems.genealogy.genealogy_system import GenealogySystem

class AncestryQueries:
    def __init__(self, genealogy_system: GenealogySystem):
        self._genealogy = genealogy_system

    def is_forbidden_marriage(self, id_a: int, id_b: int, limit: int = 3) -> bool:
        """
        Determina si una unión está prohibida por consanguinidad.
        Delega al GenealogySystem, que ahora gestiona el registro y el BFS.
        """
        # Usamos el método unificado que ahora vive dentro del GenealogySystem
        return self._genealogy.is_consanguineous(id_a, id_b, limit=limit)

    def get_kinship_degree(self, id_a: int, id_b: int) -> int:
        """Retorna el grado exacto de parentesco para fines estadísticos."""
        return self._genealogy.get_degree_of_kinship(id_a, id_b)