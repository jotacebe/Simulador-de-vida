"""Módulo de fachada para la resolución de parentescos y árboles genealógicos."""

from systems.genealogy.genealogy_system import GenealogySystem

class AncestryQueries:
    """Servicio para aislar las consultas complejas de parentesco del sistema principal.
    
    Actúa como una fachada (Facade Pattern) sobre el GenealogySystem, ofreciendo
    respuestas booleanas o numéricas para la toma de decisiones sociales.
    """

    def __init__(self, genealogy_system: GenealogySystem) -> None:
        """Inicializa el servicio vinculándolo al motor genealógico central."""
        self._genealogy = genealogy_system

    def is_forbidden_marriage(self, id_a: int, id_b: int) -> bool:
        """Determina si una unión está biológicamente prohibida por consanguinidad.
        
        Evalúa el parentesco utilizando el límite legal/biológico definido
        en la configuración centralizada del ecosistema.
        """
        # Extraemos el límite de la configuración en lugar de usar un valor quemado (hardcoded)
        limit = self._genealogy.config.genealogy.consanguinity_limit
        return self._genealogy.is_consanguineous(id_a, id_b, limit=limit)

    def get_kinship_degree(self, id_a: int, id_b: int) -> int:
        """Calcula y retorna el grado exacto de parentesco biológico."""
        return self._genealogy.get_degree_of_kinship(id_a, id_b)