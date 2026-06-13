"""Módulo responsable del registro histórico y rastreo de linajes biológicos."""

import logging
from collections import deque
from typing import Dict, List, Optional, Set, Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class HistoricalPersonNode:
    """Estructura de datos pura para almacenar el historial de una entidad.
    
    Persiste en memoria incluso después de que la entidad haya fallecido en
    la simulación, permitiendo consultas retrospectivas de consanguinidad.
    """
    
    def __init__(self, entity_id: int, name: str, gender: str, birth_tick: float) -> None:
        """Inicializa un nodo histórico desvinculado de dependencias lógicas."""
        self.entity_id = entity_id
        self.name = name
        self.gender = gender
        self.birth_tick = birth_tick
        self.death_tick: Optional[float] = None
        self.is_alive = True
        
        # Relaciones topológicas (Grafo familiar)
        self.biological_parents: List[int] = []
        self.adoptive_parents: List[int] = []
        self.children: List[int] = []
        self.spouses: List[int] = []
        
        # Datos de linaje
        self.lineage_id: Optional[int] = None
        self.generation_index: int = 0
        
        # Snapshot fenotípico (útil para análisis post-mortem sin cargar el genoma completo)
        self.longevity: float = 1.0
        self.sociability: float = 0.5
        self.temperament: float = 0.5

class Lineage:
    """Contenedor analítico para agrupar entidades bajo un mismo ancestro fundador."""
    
    def __init__(self, lineage_id: int, founder_id: int) -> None:
        self.lineage_id = lineage_id
        self.founder_id = founder_id
        self.members: Set[int] = {founder_id}
        self.is_extinct = False

class GenealogySystem:
    """Motor de sincronización histórica y algoritmos de parentesco."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config
        self.registry: Dict[int, HistoricalPersonNode] = {}
        self.lineages: Dict[int, Lineage] = {}
        self._next_lineage_id = 1
        self.total_days_elapsed = 0.0
        self.logger = logging.getLogger("GenealogySystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Sincroniza el grafo histórico con los eventos del ciclo actual."""
        self.total_days_elapsed += delta_days
        
        # 1. SINCRONIZACIÓN DE CENSO (Altas)
        # Aseguramos que cualquier persona en el mundo real exista en el registro histórico
        for person in state.get_all_persons():
            if person.entity_id not in self.registry:
                self._sync_new_person(person)

        # 2. PROCESAMIENTO DE ADOPCIONES
        # Escuchamos los eventos del AdoptionSystem para registrar vínculos legales
        for adoption in getattr(pending, 'adoptions', []):
            child_id = adoption.get('child_id')
            if child_id in self.registry:
                node = self.registry[child_id]
                for parent_key in ['parent_a', 'parent_b']:
                    if adoption.get(parent_key):
                        node.adoptive_parents.append(adoption.get(parent_key))

        # 3. PROCESAMIENTO DE FALLECIMIENTOS (Bajas)
        for dead_id in pending.deaths:
            if dead_id in self.registry and self.registry[dead_id].is_alive:
                self.registry[dead_id].is_alive = False
                self.registry[dead_id].death_tick = self.total_days_elapsed

        # 4. MANTENIMIENTO DE LINAJES
        # Comprobamos extinciones: si ningún miembro está vivo, el linaje cae.
        for lineage in self.lineages.values():
            if not lineage.is_extinct:
                alive_members = any(
                    self.registry[m_id].is_alive 
                    for m_id in lineage.members if m_id in self.registry
                )
                if not alive_members:
                    lineage.is_extinct = True

    def _sync_new_person(self, person: Any) -> None:
        """Extrae la huella genética y relacional de un agente para el registro."""
        # Detectamos si es de la población inicial (día 0) o recién nacido
        birth_tick = self.total_days_elapsed if getattr(person, 'age', 0) <= 1 else 0.0
        
        node = HistoricalPersonNode(
            entity_id=person.entity_id,
            name=getattr(person, 'name', f"Agent_{person.entity_id}"),
            gender=getattr(person, 'gender', 'unknown'),
            birth_tick=birth_tick
        )
        
        # Guardado de snapshot genético mediante introspección
        if hasattr(person, 'genome'):
            node.longevity = getattr(person.genome, 'longevity', 1.0)
            node.sociability = getattr(person.genome, 'sociability', 0.5)
            node.temperament = getattr(person.genome, 'temperament', 0.5)
        
        # Vinculación bidireccional biológica
        father_id = getattr(person, 'father_id', None)
        mother_id = getattr(person, 'mother_id', None)
        
        if father_id is not None and father_id in self.registry:
            node.biological_parents.append(father_id)
            self.registry[father_id].children.append(person.entity_id)
                
        if mother_id is not None and mother_id in self.registry:
            node.biological_parents.append(mother_id)
            self.registry[mother_id].children.append(person.entity_id)

        # Resolución de Generación y Linaje Patrilineal/Matrilineal
        if not node.biological_parents:
            # Fundador (Generación 0)
            node.generation_index = 0
            lineage_id = self._next_lineage_id
            self._next_lineage_id += 1
            self.lineages[lineage_id] = Lineage(lineage_id, person.entity_id)
            node.lineage_id = lineage_id
        else:
            # Hereda la generación máxima de sus padres + 1
            parent_gens = [self.registry[p_id].generation_index for p_id in node.biological_parents]
            node.generation_index = max(parent_gens) + 1
            
            # Hereda el linaje preferentemente del padre, o de la madre en familias monoparentales maternas
            if father_id in self.registry and self.registry[father_id].lineage_id is not None:
                node.lineage_id = self.registry[father_id].lineage_id
            elif mother_id in self.registry and self.registry[mother_id].lineage_id is not None:
                node.lineage_id = self.registry[mother_id].lineage_id
                
            # Registrar al miembro en su contenedor de linaje
            if node.lineage_id is not None and node.lineage_id in self.lineages:
                self.lineages[node.lineage_id].members.add(person.entity_id)
                
        self.registry[person.entity_id] = node

    def get_degree_of_kinship(self, id_a: int, id_b: int) -> int:
        """Calcula el grado de parentesco civil mediante un algoritmo BFS.
        
        Retorna la distancia más corta navegando por la red de padres e hijos.
        - Padre e Hijo = Distancia 1
        - Hermanos (A -> Padre -> B) = Distancia 2
        - Tíos y Sobrinos (A -> Padre -> Abuelo -> B) = Distancia 3
        - Primos = Distancia 4
        
        Retorna -1 si no comparten línea de sangre.
        """
        if id_a not in self.registry or id_b not in self.registry:
            return -1
            
        if id_a == id_b:
            return 0

        # Implementación de Breadth-First Search (Búsqueda en anchura)
        visited: Set[int] = {id_a}
        queue: deque = deque([(id_a, 0)])  # Tupla: (entity_id, distancia_acumulada)
        
        while queue:
            current_id, dist = queue.popleft()
            
            if current_id == id_b:
                return dist
                
            node = self.registry[current_id]
            
            # El grafo de sangre se compone exclusivamente de padres e hijos
            blood_relatives = node.biological_parents + node.children
            
            for relative_id in blood_relatives:
                if relative_id not in visited:
                    visited.add(relative_id)
                    queue.append((relative_id, dist + 1))
                    
        return -1  # Grafo disjunto (no son parientes biológicos)

    def is_consanguineous(self, id_a: int, id_b: int, limit: int) -> bool:
        """Evalúa si la distancia genética incurre en prohibición social."""
        degree = self.get_degree_of_kinship(id_a, id_b)
        
        if degree == -1:
            return False  # Sin parentesco
            
        # Si están a una distancia igual o más cercana que el límite (ej. primos=4), es consanguíneo
        return degree <= limit