"""Módulo que define el contexto espacial, ambiental y topográfico para la simulación.

Provee a los sistemas de una instantánea (snapshot) de la distribución demográfica,
la presión del entorno y la disponibilidad de recursos en el tick actual.
"""

import math
from collections import defaultdict
from typing import List, Tuple, Dict, Any
from core.state.world_state import WorldState

class EnvironmentContext:
    """Representa el estado del entorno, distribuyendo recursos y agentes."""

    def __init__(self, state: WorldState, sector_size: int = 10, carrying_capacity: int = 200) -> None:
        """Inicializa la topografía y agrupa a los agentes por sectores.
        
        Args:
            state: Referencia al estado del mundo en el tick actual.
            sector_size: Tamaño de las celdas de la cuadrícula espacial.
            carrying_capacity: Población máxima que un sector soporta antes del colapso.
        """
        self.sector_size = sector_size
        self.carrying_capacity = carrying_capacity
        
        # Calculamos el mapa de sectores al instanciarse (una sola vez por tick)
        self.sector_map = self._build_sector_map(state)
        
        # Mapa de eventos atmosféricos (modificable por un sistema de clima)
        self.pressure_map: Dict[Tuple[int, int], float] = {}

    def _build_sector_map(self, state: WorldState) -> Dict[Tuple[int, int], List[Any]]:
        """Agrupa a los agentes por sector espacial para agilizar las consultas (O(1))."""
        sector_map = defaultdict(list)
        for person in state.get_all_persons():
            key = (person.x // self.sector_size, person.y // self.sector_size)
            sector_map[key].append(person)
        return sector_map

    def get_local_pressure(self, x: int, y: int) -> float:
        """Calcula la presión combinada (Clima + Hacinamiento demográfico).
        
        Sustituye la presión estática por una evaluación dinámica que penaliza
        los sectores cuya población exceda la capacidad de carga (carrying_capacity).
        """
        sector_key = (x // self.sector_size, y // self.sector_size)
        poblacion_local = len(self.sector_map.get(sector_key, []))
        
        # Presión generada por densidad poblacional (Sobrepoblación)
        densidad_presion = poblacion_local / max(1, self.carrying_capacity)
        
        # Presión ambiental extra (ej: tormentas, eventos precalculados)
        clima_presion = self.pressure_map.get((x, y), 0.0)
        
        # Valor base 1.0 (condiciones estables). Todo lo superior es estrés.
        return 1.0 + densidad_presion + clima_presion

    def get_agents_in_sector(self, x: int, y: int) -> List[Any]:
        """Devuelve la lista de agentes presentes en el sector correspondiente."""
        return self.sector_map.get((x // self.sector_size, y // self.sector_size), [])

    def get_resources_at(self, x: int, y: int) -> float:
        """Calcula de forma determinista la disponibilidad de recursos (0.0 a 1.0).
        
        Utiliza matemáticas procedimentales (ruido trigonométrico) para generar 
        "biomas" o zonas fértiles persistentes, sin consumir memoria RAM en matrices.
        """
        # 1. Bioma natural (Oasis vs Desiertos)
        # Una fórmula de ondas entrelazadas que crea patrones suaves en el terreno
        ruido = (math.sin(x * 0.15) + math.cos(y * 0.15)) / 2.0
        recurso_base = (ruido + 1.0) / 2.0  # Normalizado entre 0.0 y 1.0
        
        # 2. Desgaste por sobreexplotación (Hambre poblacional)
        sector_key = (x // self.sector_size, y // self.sector_size)
        consumidores = len(self.sector_map.get(sector_key, []))
        
        # Si un sector rico en recursos se llena de gente, la comida se agota localmente
        desgaste = (consumidores / max(1, self.carrying_capacity)) * 0.8
        
        return max(0.0, min(1.0, recurso_base - desgaste))