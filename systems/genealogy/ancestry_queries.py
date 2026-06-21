"""Módulo de fachada para la resolución de parentescos y árboles genealógicos.

Expone una API limpia para consultas analíticas complejas, estadísticas de linaje
y validación de leyes sociales sin exponer el grafo subyacente.
"""

from typing import Dict, Any, Set, List
from systems.genealogy.genealogy_system import GenealogySystem

class AncestryQueries:
    """Servicio para aislar consultas complejas y estadísticas del sistema central."""

    def __init__(self, genealogy_system: GenealogySystem) -> None:
        """Inicializa el servicio vinculándolo al motor genealógico central."""
        self._genealogy = genealogy_system

    def is_forbidden_marriage(self, id_a: int, id_b: int) -> bool:
        """Determina si una unión está biológicamente prohibida por consanguinidad."""
        limit = self._genealogy.config.genealogy.consanguinity_limit
        return self._genealogy.is_consanguineous(id_a, id_b, limit=limit)

    def get_kinship_degree(self, id_a: int, id_b: int) -> int:
        """Calcula y retorna el grado exacto de parentesco biológico."""
        return self._genealogy.get_degree_of_kinship(id_a, id_b)

    # ==========================================
    # HERRAMIENTAS POTENTES DE ESTADÍSTICA (NUEVO)
    # ==========================================
    def calculate_lineage_success(self, founder_id: int, vivos_ids: Set[int]) -> Dict[str, Any]:
        """Calcula el éxito reproductivo de un individuo para el motor evolutivo.
        
        Args:
            founder_id: ID del individuo a analizar.
            vivos_ids: Set con los IDs de las entidades actualmente vivas.
            
        Returns:
            Diccionario con métricas de éxito genético.
        """
        descendants = self._genealogy.get_all_descendants(founder_id)
        descendencia_viva = len([d for d in descendants if d in vivos_ids])
        
        return {
            "total_descendencia_historica": len(descendants),
            "total_descendencia_viva": descendencia_viva,
            "tasa_supervivencia": descendencia_viva / max(1, len(descendants))
        }

    def get_lineage_statistics(self, lineage_id: int) -> Dict[str, Any]:
        """Genera un reporte automático completo sobre una familia entera.
        
        Útil para interfaces gráficas (GUI) o recolección de métricas al final
        de la simulación.
        """
        if lineage_id not in self._genealogy.lineages:
            return {"error": "Linaje no encontrado"}
            
        lineage = self._genealogy.lineages[lineage_id]
        miembros_ids = lineage.members
        
        vivos = 0
        muertos = 0
        edades_al_morir = []
        generaciones_alcanzadas = set()
        
        for m_id in miembros_ids:
            if m_id in self._genealogy.registry:
                node = self._genealogy.registry[m_id]
                generaciones_alcanzadas.add(node.generation_index)
                
                if node.is_alive:
                    vivos += 1
                else:
                    muertos += 1
                    # Calcula la edad al morir (si el dato de tick está disponible)
                    if node.death_tick is not None:
                        edades_al_morir.append(node.death_tick - node.birth_tick)

        avg_lifespan = sum(edades_al_morir) / len(edades_al_morir) if edades_al_morir else 0.0

        return {
            "lineage_id": lineage_id,
            "founder_id": lineage.founder_id,
            "is_extinct": lineage.is_extinct,
            "total_members": len(miembros_ids),
            "alive_members": vivos,
            "deceased_members": muertos,
            "generations_span": max(generaciones_alcanzadas) if generaciones_alcanzadas else 0,
            "average_historical_lifespan_days": avg_lifespan
        }

    def analyze_inbreeding_risk(self, entity_id: int) -> float:
        """Detecta eventos genealógicos de riesgo (Endogamia/Cuello de botella).
        
        Calcula un coeficiente simplificado basado en el solapamiento de 
        ancestros paternos y maternos. Retorna [0.0 - 1.0].
        """
        if entity_id not in self._genealogy.registry:
            return 0.0
            
        node = self._genealogy.registry[entity_id]
        if len(node.biological_parents) != 2:
            return 0.0 # Familias monoparentales o fundadores no tienen riesgo detectable aquí
            
        padre_id, madre_id = node.biological_parents
        
        # Obtenemos todos los ancestros de ambos padres
        ancestros_padre = self._get_all_ancestors(padre_id)
        ancestros_madre = self._get_all_ancestors(madre_id)
        
        if not ancestros_padre or not ancestros_madre:
            return 0.0
            
        solapamiento = ancestros_padre.intersection(ancestros_madre)
        total_unicos = ancestros_padre.union(ancestros_madre)
        
        # El riesgo aumenta cuantos más ancestros compartan en su árbol
        return len(solapamiento) / max(1, len(total_unicos))

    def _get_all_ancestors(self, entity_id: int) -> Set[int]:
        """Algoritmo recursivo protegido para extraer la línea ascendente completa."""
        ancestros = set()
        if entity_id not in self._genealogy.registry:
            return ancestros
            
        parents = self._genealogy.registry[entity_id].biological_parents
        for parent_id in parents:
            ancestros.add(parent_id)
            ancestros.update(self._get_all_ancestors(parent_id))
            
        return ancestros