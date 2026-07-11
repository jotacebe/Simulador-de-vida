"""Módulo responsable del Entorno: Presión espacial, Clima y Recursos.

Calcula la presión espacial basada en densidad poblacional y actúa como 
infraestructura base para futuras expansiones de clima y catástrofes.

NOTA: Este sistema es el ÚNICO que calcula presión. EnvironmentContext solo la lee.
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
    """Estaciones del año (placeholder para futuro sistema climático)."""
    SPRING = auto()
    SUMMER = auto()
    AUTUMN = auto()
    WINTER = auto()


class Weather(Enum):
    """Tipos de clima (placeholder para futuro sistema climático)."""
    CLEAR = auto()
    RAINY = auto()
    STORMY = auto()
    DROUGHT = auto()
    BLIZZARD = auto()


class BiomeType(Enum):
    """Tipos de bioma (placeholder para futuro sistema de biomas emergentes)."""
    PLAINS = auto()
    FOREST = auto()
    DESERT = auto()
    TUNDRA = auto()


class EnvironmentSystem:
    """Calcula la presión espacial y gestiona la infraestructura climática."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración central."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # INFRAESTRUCTURA CLIMÁTICA (Inicialización explícita y segura)
        self.current_season: Season = Season.SPRING
        self.current_weather: Weather = Weather.CLEAR
        self.days_in_current_season: float = 0.0
        self.season_duration_days: float = getattr(config.environment, 'season_duration_days', 90.0)
        
        # INFRAESTRUCTURA DE BIOMAS (Placeholder)
        self.biome_map: Dict[Tuple[int, int], BiomeType] = {}
        self.resource_grid: Dict[Tuple[int, int], Dict[str, float]] = {}
        self.danger_zones: Dict[Tuple[int, int], float] = {}

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Evalúa la densidad poblacional y actualiza el reloj climático."""
        env_cfg = self.config.environment
        max_agents = env_cfg.max_agents_per_sector
        
        # =====================================================================
        # 1. CÁLCULO DE PRESIÓN ESPACIAL (ÚNICA FUENTE DE VERDAD)
        # =====================================================================
        context.pressure_map.clear()
        
        for sector_coords, agents_in_sector in context.sector_map.items():
            current_sector_pop = len(agents_in_sector)
            
            if current_sector_pop <= max_agents:
                pressure = 1.0
            else:
                excess_ratio = (current_sector_pop - max_agents) / max_agents
                pressure = 1.0 + excess_ratio
            
            # Asignar presión a TODAS las celdas del sector
            sector_x, sector_y = sector_coords
            for dx in range(env_cfg.sector_size):
                for dy in range(env_cfg.sector_size):
                    cell_x = sector_x * env_cfg.sector_size + dx
                    cell_y = sector_y * env_cfg.sector_size + dy
                    context.pressure_map[(cell_x, cell_y)] = pressure

        # =====================================================================
        # 2. INFRAESTRUCTURA CLIMÁTICA (Segura contra estados None)
        # =====================================================================
        # Verificación de seguridad: si por alguna razón el estado es None, reinicializar
        if self.current_season is None:
            self.current_season = Season.SPRING
            self.logger.warning("current_season era None, reinicializado a SPRING")
            
        self.days_in_current_season += delta_days
        if self.days_in_current_season >= self.season_duration_days:
            self.days_in_current_season = 0.0
            self._advance_season()

        self._update_weather_placeholder(delta_days)

        # Inyectar datos climáticos en el contexto (para uso futuro)
        context.current_season = self.current_season
        context.current_weather = self.current_weather

    def _advance_season(self) -> None:
        """Cicla las estaciones de forma secuencial."""
        # Protección explícita contra None
        if self.current_season is None:
            self.current_season = Season.SPRING
            
        seasons = list(Season)
        try:
            next_index = (seasons.index(self.current_season) + 1) % len(seasons)
            self.current_season = seasons[next_index]
            self.logger.info(f"🌍 El entorno ha cambiado de estación a: {self.current_season.name}")
        except ValueError as e:
            # Si por alguna razón la estación no está en la lista, forzar SPRING
            self.logger.error(f"Error avanzado estación: {e}. Forzando SPRING.")
            self.current_season = Season.SPRING

    def _update_weather_placeholder(self, delta_days: float) -> None:
        """Cambia el clima de forma pseudoaleatoria basada en la estación."""
        if self.current_season is None:
            return  # Protección
            
        if random.random() < (0.01 * delta_days):
            if self.current_season == Season.WINTER:
                self.current_weather = random.choice([Weather.CLEAR, Weather.RAINY, Weather.BLIZZARD])
            elif self.current_season == Season.SUMMER:
                self.current_weather = random.choice([Weather.CLEAR, Weather.DROUGHT])
            else:
                self.current_weather = random.choice([Weather.CLEAR, Weather.RAINY, Weather.STORMY])

    # =====================================================================
    # INTERFAZ DE CONSULTA DE INFRAESTRUCTURA (Para uso futuro)
    # =====================================================================
    def get_biome_at(self, x: float, y: float) -> BiomeType:
        """Obtiene el bioma en una coordenada (placeholder: siempre PLAINS)."""
        return self.biome_map.get((int(x), int(y)), BiomeType.PLAINS)

    def get_resource_level(self, x: float, y: float, resource_type: str) -> float:
        """Obtiene el nivel de un recurso específico (placeholder: siempre 100.0)."""
        cell_resources = self.resource_grid.get((int(x), int(y)))
        if cell_resources:
            return cell_resources.get(resource_type, 100.0)
        return 100.0

    def get_danger_level(self, x: float, y: float) -> float:
        """Obtiene el nivel de peligro en una coordenada.
        
        NOTA: Actualmente siempre devuelve 0.0 porque biome_map está vacío.
        En el futuro, esto se usará para biomas emergentes.
        """
        biome = self.get_biome_at(x, y)
        base_danger = 0.3 if biome in [BiomeType.DESERT, BiomeType.TUNDRA] else 0.0
        return min(1.0, self.danger_zones.get((int(x), int(y)), 0.0) + base_danger)

    def trigger_catastrophe(self, x: float, y: float, radius: float, severity: float) -> None:
        """Marca un área como zona de peligro extremo instantáneo.
        
        Args:
            x: Coordenada X del centro.
            y: Coordenada Y del centro.
            radius: Radio del área afectada.
            severity: Severidad del peligro [0.0, 1.0].
        """
        self.logger.warning(f"¡CATÁSTROFE ACTIVADA en ({x}, {y}) con radio {radius}!")
        for dx in range(int(-radius), int(radius) + 1):
            for dy in range(int(-radius), int(radius) + 1):
                target_coord = (int(x + dx), int(y + dy))
                self.danger_zones[target_coord] = severity