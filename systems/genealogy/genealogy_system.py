"""Módulo responsable del registro histórico y rastreo de linajes biológicos.

Consolida el árbol genealógico global, persistiendo en memoria a los agentes
fallecidos y detectando eventos macro-históricos como la extinción de ramas.
"""

import logging
from collections import deque
from typing import Dict, List, Optional, Set, Any

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class HistoricalPersonNode:
    """Estructura de datos pura para almacenar el historial de una entidad."""
    
    def __init__(self, entity_id: int, name: str, gender: str, birth_tick: float) -> None:
        """Inicializa un nodo histórico desvinculado de dependencias lógicas."""
        self.entity_id = entity_id
        self.name = name
        self.gender = gender
        self.birth_tick = birth_tick
        self.death_tick: Optional[float] = None
        self.is_alive = True
        
        # Relaciones topológicas (Grafo familiar bidireccional)
        self.biological_parents: List[int] = []
        self.adoptive_parents: List[int] = []
        self.children: List[int] = []
        self.spouses: List[int] = []
        
        # Datos de jerarquía y linaje
        self.lineage_id: Optional[int] = None
        self.generation_index: int = 0
        
        # Snapshot fenotípico para analítica post-mortem
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
    """Motor de sincronización histórica y algoritmos de parentesco en grafos."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.registry: Dict[int, HistoricalPersonNode] = {}
        self.lineages: Dict[int, Lineage] = {}
        self._next_lineage_id = 1
        self.total_days_elapsed = 0.0
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Sincroniza el grafo histórico detectando eventos relevantes."""
        self.total_days_elapsed += delta_days
        
        # 1. SINCRONIZACIÓN DE CENSO (Altas)
        for person in state.get_all_persons():
            if person.entity_id not in self.registry:
                self._sync_new_person(person)

        # 2. PROCESAMIENTO DE ADOPCIONES
        for adoption in getattr(pending, 'adoptions', []):
            child_id = adoption.get('child_id')
            if child_id in self.registry:
                node = self.registry[child_id]
                for parent_key in ['parent_a', 'parent_b']:
                    p_id = adoption.get(parent_key)
                    if p_id and p_id not in node.adoptive_parents:
                        node.adoptive_parents.append(p_id)

        # 3. PROCESAMIENTO DE FALLECIMIENTOS (Bajas)
        for dead_id in pending.deaths:
            if dead_id in self.registry and self.registry[dead_id].is_alive:
                self.registry[dead_id].is_alive = False
                self.registry[dead_id].death_tick = self.total_days_elapsed

        # 4. MANTENIMIENTO DE LINAJES Y DETECCIÓN DE EXTINCIONES
        for lineage in self.lineages.values():
            if not lineage.is_extinct:
                alive_members = any(
                    self.registry[m_id].is_alive 
                    for m_id in lineage.members if m_id in self.registry
                )
                if not alive_members:
                    lineage.is_extinct = True
                    # Evento genealógico relevante detectado
                    self.logger.info(f"📜 Evento Histórico: El linaje {lineage.lineage_id} "
                                     f"(Fundador {lineage.founder_id}) se ha extinguido.")

    def _sync_new_person(self, person: Any) -> None:
        """Extrae la huella genética y relacional de un agente para el registro."""
        birth_tick = self.total_days_elapsed if getattr(person, 'age', 0) <= 1 else 0.0
        
        node = HistoricalPersonNode(
            entity_id=person.entity_id,
            name=getattr(person, 'name', f"Agent_{person.entity_id}"),
            gender=getattr(person, 'gender', 'unknown'),
            birth_tick=birth_tick
        )
        
        # Guardado de snapshot mediante introspección de propiedades (Genome)
        if hasattr(person, 'genome'):
            node.longevity = getattr(person.genome, 'longevity', 1.0)
            node.sociability = getattr(person.genome, 'sociability', 0.5)
            node.temperament = getattr(person.genome, 'temperament', 0.5)
        
        father_id = getattr(person, 'father_id', None)
        mother_id = getattr(person, 'mother_id', None)
        
        if father_id is not None and father_id in self.registry:
            node.biological_parents.append(father_id)
            self.registry[father_id].children.append(person.entity_id)
                
        if mother_id is not None and mother_id in self.registry:
            node.biological_parents.append(mother_id)
            self.registry[mother_id].children.append(person.entity_id)

        # Resolución de Generación y Linaje
        if not node.biological_parents:
            node.generation_index = 0
            lineage_id = self._next_lineage_id
            self._next_lineage_id += 1
            self.lineages[lineage_id] = Lineage(lineage_id, person.entity_id)
            node.lineage_id = lineage_id
        else:
            parent_gens = [self.registry[p_id].generation_index for p_id in node.biological_parents]
            node.generation_index = max(parent_gens) + 1
            
            # Hereda linaje (preferencia matrilineal si no hay padre)
            if father_id in self.registry and self.registry[father_id].lineage_id is not None:
                node.lineage_id = self.registry[father_id].lineage_id
            elif mother_id in self.registry and self.registry[mother_id].lineage_id is not None:
                node.lineage_id = self.registry[mother_id].lineage_id
                
            if node.lineage_id is not None and node.lineage_id in self.lineages:
                self.lineages[node.lineage_id].members.add(person.entity_id)
                
        self.registry[person.entity_id] = node

    # ==========================================
    # ALGORITMOS DE GRAFOS PARA CONSULTAS
    # ==========================================
    def get_degree_of_kinship(self, id_a: int, id_b: int) -> int:
        """Calcula el grado de parentesco civil mediante un algoritmo BFS."""
        if id_a not in self.registry or id_b not in self.registry:
            return -1
        if id_a == id_b:
            return 0

        visited: Set[int] = {id_a}
        queue: deque = deque([(id_a, 0)]) 
        
        while queue:
            current_id, dist = queue.popleft()
            if current_id == id_b:
                return dist
                
            node = self.registry[current_id]
            blood_relatives = node.biological_parents + node.children
            
            for relative_id in blood_relatives:
                if relative_id not in visited:
                    visited.add(relative_id)
                    queue.append((relative_id, dist + 1))
                    
        return -1 

    def is_consanguineous(self, id_a: int, id_b: int, limit: int) -> bool:
        """Evalúa si la distancia genética incurre en prohibición legal."""
        degree = self.get_degree_of_kinship(id_a, id_b)
        if degree == -1:
            return False 
        return degree <= limit

    def get_all_descendants(self, entity_id: int) -> Set[int]:
        """Recupera la totalidad de descendientes directos e indirectos (BFS)."""
        if entity_id not in self.registry:
            return set()
            
        descendants = set()
        queue: deque = deque(self.registry[entity_id].children)
        
        while queue:
            current = queue.popleft()
            if current not in descendants:
                descendants.add(current)
                if current in self.registry:
                    queue.extend(self.registry[current].children)
                    
        return descendants