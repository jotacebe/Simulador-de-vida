"""Módulo que define el contexto espacial y ambiental para la simulación."""

from collections import defaultdict
from core.state.world_state import WorldState

class EnvironmentContext:
    """Representa el estado del entorno y distribuye espacialmente a los agentes."""

    def __init__(self, state: WorldState, sector_size: int = 10, carrying_capacity: int = 200) -> None:
        """Inicializa el contexto ambiental y construye el mapa de sectores."""
        self.sector_size = sector_size
        self.carrying_capacity = carrying_capacity
        
        # Calculamos el mapa de sectores al instanciarse (una sola vez por tick)
        self.sector_map = self._build_sector_map(state)
        self.pressure_map = {}

    def _build_sector_map(self, state: WorldState) -> dict:
        """Agrupa a los agentes por sector para agilizar la lectura de los sistemas."""
        sector_map = defaultdict(list)
        for person in state.get_all_persons():
            key = (person.x // self.sector_size, person.y // self.sector_size)
            sector_map[key].append(person)
        return sector_map
    
    def get_local_pressure(self, x: int, y: int) -> float:
        """Devuelve la presión ambiental o atmosférica en una coordenada dada."""
        # Intenta obtener la presión del mapa de presión (si existe)
        # Si no existe, devuelve 1.0 por defecto
        return self.pressure_map.get((x, y), 1.0)

    def get_agents_in_sector(self, x: int, y: int) -> list:
        """Devuelve la lista de agentes presentes en el sector correspondiente a la coordenada."""
        return self.sector_map.get((x // self.sector_size, y // self.sector_size), [])