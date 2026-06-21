"""Módulo responsable del Entorno: Presión espacial, Clima, Biomas y Recursos.

Actualmente calcula funcionalmente el estrés por hacinamiento (presión espacial),
y actúa como infraestructura base para futuras expansiones de clima y catástrofes.
"""

import logging
import random
from enum import Enum, auto
from typing import Dict, Tuple

from systems.environment.environment_context import EnvironmentContext
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from core.config.simulation_config import SimulationConfig

class Season(Enum):
    SPRING = auto()
    SUMMER = auto()
    AUTUMN = auto()
    WINTER = auto()

class Weather(Enum):
    CLEAR = auto()
    RAINY = auto()
    STORMY = auto()
    DROUGHT = auto()
    BLIZZARD = auto()

class BiomeType(Enum):
    PLAINS = auto()    # Templado, recursos estándar
    FOREST = auto()    # Abundante madera/comida, movimiento lento
    DESERT = auto()    # Calor extremo, agua escasa, peligroso
    TUNDRA = auto()    # Frío extremo, comida escasa, peligroso

class EnvironmentSystem:
    """Calcula la presión espacial y gestiona la infraestructura climática."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración central."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 1. INFRAESTRUCTURA MACRO: Reloj Climático de la Simulación
        self.current_season = Season.SPRING
        self.current_weather = Weather.CLEAR
        self.days_in_current_season = 0.0
        self.season_duration_days = 90.0  # Días por estación
        
        # 2. INFRAESTRUCTURA MICRO: Mapas de Grid futuros
        self.biome_map: Dict[Tuple[int, int], BiomeType] = {}
        self.resource_grid: Dict[Tuple[int, int], Dict[str, float]] = {}
        self.danger_zones: Dict[Tuple[int, int], float] = {} 

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Evalúa la densidad poblacional y actualiza el reloj climático."""
        
        # =====================================================================
        # 1. LÓGICA ACTIVA: CÁLCULO DE PRESIÓN ESPACIAL (Tu código original)
        # =====================================================================
        env_cfg = getattr(self.config, 'environment', None)
        # Fallback seguro por si la config no tiene max_agents_per_sector definido aún
        max_agents = getattr(env_cfg, 'max_agents_per_sector', 10) if env_cfg else 10
        
        context.pressure_map.clear()

        for sector_coords, agents_in_sector in context.sector_map.items():
            current_sector_pop = len(agents_in_sector)
            
            if current_sector_pop <= max_agents:
                pressure = 1.0
            else:
                excess_ratio = (current_sector_pop - max_agents) / max_agents
                pressure = 1.0 + excess_ratio

            for person in agents_in_sector:
                context.pressure_map[(person.x, person.y)] = pressure

        # =====================================================================
        # 2. INFRAESTRUCTURA (SCAFFOLDING): ESTACIONES Y CLIMA
        # =====================================================================
        self.days_in_current_season += delta_days
        if self.days_in_current_season >= self.season_duration_days:
            self.days_in_current_season = 0.0
            self._advance_season()

        self._update_weather_placeholder(delta_days)

        # Inyectamos los datos climáticos en el contexto para otros sistemas
        setattr(context, "current_season", self.current_season)
        setattr(context, "current_weather", self.current_weather)

    def _advance_season(self) -> None:
        """Cicla las estaciones de forma secuencial."""
        seasons = list(Season)
        next_index = (seasons.index(self.current_season) + 1) % len(seasons)
        self.current_season = seasons[next_index]
        self.logger.info(f"El entorno ha cambiado de estación a: {self.current_season.name}")

    def _update_weather_placeholder(self, delta_days: float) -> None:
        """Cambia el clima de forma pseudoaleatoria basada en la estación."""
        if random.random() < (0.01 * delta_days):
            if self.current_season == Season.WINTER:
                self.current_weather = random.choice([Weather.CLEAR, Weather.RAINY, Weather.BLIZZARD])
            elif self.current_season == Season.SUMMER:
                self.current_weather = random.choice([Weather.CLEAR, Weather.DROUGHT])
            else:
                self.current_weather = random.choice([Weather.CLEAR, Weather.RAINY, Weather.STORMY])

    # =====================================================================
    # INTERFAZ DE CONSULTA DE INFRAESTRUCTURA (Para el futuro)
    # =====================================================================
    def get_biome_at(self, x: float, y: float) -> BiomeType:
        return self.biome_map.get((int(x), int(y)), BiomeType.PLAINS)

    def get_resource_level(self, x: float, y: float, resource_type: str) -> float:
        cell_resources = self.resource_grid.get((int(x), int(y)))
        if cell_resources:
            return cell_resources.get(resource_type, 100.0)
        return 100.0

    def get_danger_level(self, x: float, y: float) -> float:
        biome = self.get_biome_at(x, y)
        base_danger = 0.3 if biome in [BiomeType.DESERT, BiomeType.TUNDRA] else 0.0
        return min(1.0, self.danger_zones.get((int(x), int(y)), 0.0) + base_danger)

    def trigger_catastrophe(self, x: float, y: float, radius: float, severity: float) -> None:
        """Marca un área como zona de peligro extremo instantáneo."""
        self.logger.warning(f"¡CATÁSTROFE ACTIVADA en ({x}, {y}) con radio {radius}!")
        for dx in range(int(-radius), int(radius) + 1):
            for dy in range(int(-radius), int(radius) + 1):
                target_coord = (int(x + dx), int(y + dy))
                self.danger_zones[target_coord] = severity