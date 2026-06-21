"""Módulo de Búfer Atómico Universal del ciclo de ejecución.

Actúa como un 'Staging Area' (zona de pruebas) donde los sistemas registran 
sus intenciones sin alterar el mundo real. Esto garantiza que el orden de 
ejecución de los sistemas no cause efectos secundarios indeseados y que 
los datos fluyan de forma segura hacia la fase de consolidación (commit).
"""

from typing import List, Dict, Tuple, Any, Optional
from systems.diseases.pathogen import Pathogen

class PendingChanges:
    """Contenedor de mutaciones encoladas para el estado del mundo.
    
    Acumula las decisiones de los sistemas biológicos, espaciales y sociales
    durante el tick actual para ser aplicadas atómicamente por el WorldState.
    """

    def __init__(self) -> None:
        """Inicializa todas las colecciones transaccionales vacías."""
        self.movements: Dict[int, Tuple[int, int]] = {}
        
        # Colecciones médicas (Soportan objetos de cepas virales e inmunidad)
        self.infections: List[Tuple[int, Pathogen]] = []
        self.recoveries: List[Tuple[int, str]] = []
        
        # Colecciones sociales
        self.divorces: List[Tuple[int, int]] = []
        self.marriages: Dict[int, int] = {}
        self.adoptions: List[Dict[str, Any]] = []
        
        # Colecciones biológicas
        self.pregnancy_updates: Dict[int, Dict[str, Any]] = {}
        self.births: List[Dict[str, Any]] = []
        self.age_increments: Dict[int, float] = {}
        self.deaths: Dict[int, str] = {} 
        self.days_to_add: float = 0.0

    # ==========================================
    # SALUD Y EPIDEMIOLOGÍA
    # ==========================================
    def register_infection(self, entity_id: int, pathogen: Pathogen) -> None:
        """Encola el contagio de un agente con una cepa viral específica."""
        self.infections.append((entity_id, pathogen))

    def register_recovery(self, entity_id: int, pathogen_id: str) -> None:
        """Encola la curación y la consiguiente adquisición de inmunidad."""
        self.recoveries.append((entity_id, pathogen_id))

    # ==========================================
    # ESPACIO Y TIEMPO
    # ==========================================
    def register_movement(self, entity_id: int, x: int, y: int) -> None:
        """Registra una intención de desplazamiento espacial validada."""
        self.movements[entity_id] = (x, y)

    def register_time_pass(self, days: float) -> None:
        """Suma tiempo al reloj biológico global (si aplica)."""
        self.days_to_add += days

    def register_age_increment(self, entity_id: int, increment_days: float) -> None:
        """Acumula los días envejecidos o el desgaste celular en este ciclo."""
        if entity_id not in self.age_increments:
            self.age_increments[entity_id] = 0.0
        self.age_increments[entity_id] += float(increment_days)

    # ==========================================
    # DINÁMICAS POBLACIONALES
    # ==========================================
    def register_death(self, entity_id: int, reason: str = "Desconocido") -> None:
        """Marca una entidad para ser eliminada con diagnóstico forense."""
        if entity_id not in self.deaths:
            self.deaths[entity_id] = reason

    def register_birth(self, mother_id: int, father_id: Optional[int], x: int, y: int, genome: Any) -> None:
        """Registra un nacimiento pendiente con el ADN recombinado multiespecie."""
        self.births.append({
            "mother_id": mother_id,
            "father_id": father_id,
            "x": x,
            "y": y,
            "genome": genome
        })

    def register_pregnancy_update(self, entity_id: int, is_pregnant: bool, 
                                  pregnancy_days: float, failed_increment: int = 0,
                                  litter_size: int = 1) -> None:
        """Registra el avance de gestación o abortos, soportando camadas."""
        self.pregnancy_updates[entity_id] = {
            "is_pregnant": is_pregnant,
            "pregnancy_days": float(pregnancy_days),
            "failed_increment": int(failed_increment),
            "litter_size": int(litter_size)
        }

    # ==========================================
    # RELACIONES Y LEGALIDAD
    # ==========================================
    def register_marriage(self, p1: int, p2: int) -> None:
        """Registra la intención de matrimonio simétrico."""
        self.marriages[p1] = p2

    def register_divorce(self, p1: int, p2: int) -> None:
        """Registra una ruptura o viudedad atómica para limpiar el grafo social."""
        self.divorces.append((p1, p2))

    def register_adoption(self, child_id: int, parent_a: int, parent_b: Optional[int] = None) -> None:
        """Añade una transferencia de filiación legal a la cola transaccional."""
        self.adoptions.append({
            "child_id": child_id, 
            "parent_a": parent_a, 
            "parent_b": parent_b
        })
    
    # ==========================================
    # CICLO DE VIDA DEL BÚFER
    # ==========================================
    def clear(self) -> None:
        """Limpia el búfer reasignando las colecciones (Memory-Safe).
        
        Debe ser llamado obligatoriamente tras cada commit global en el WorldState.
        """
        self.movements.clear()
        self.infections.clear()
        self.recoveries.clear()
        self.divorces.clear()
        self.marriages.clear()
        self.pregnancy_updates.clear()
        self.births.clear()
        self.age_increments.clear()
        self.adoptions.clear()
        self.deaths.clear()
        self.days_to_add = 0.0