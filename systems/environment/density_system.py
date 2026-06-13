"""Módulo de servicios espaciales para consultas de densidad poblacional."""

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class DensitySystem:
    """Provee algoritmos de búsqueda y consulta de densidad espacial."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración central."""
        self.config = config

    def get_density_factor(self, x: int, y: int, context: EnvironmentContext) -> float:
        """Calcula matemáticamente la ocupación real de un sector en base a su capacidad."""
        env_cfg = self.config.environment
        
        # Convertimos coordenadas exactas a coordenadas de sector (grid)
        sector_x = x // env_cfg.sector_size
        sector_y = y // env_cfg.sector_size
        
        # Consultamos el censo del sector en O(1) gracias al mapa del contexto
        agents = context.sector_map.get((sector_x, sector_y), [])
        
        # Retornamos el factor (0.0 = vacío, >1.0 = sobrepoblado)
        return len(agents) / max(1, env_cfg.max_agents_per_sector)

    def find_best_nearby_cell(self, x: int, y: int, radius: int, mode: str, 
                              width: int, height: int, context: EnvironmentContext) -> tuple:
        """Busca la coordenada óptima en un radio dado según criterios de densidad.
        
        Args:
            mode: 'min' (huida/aislamiento), 'max' (búsqueda de comunidad/gregarismo).
        """
        best_cell = (x, y)
        best_value = self.get_density_factor(x, y, context)
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                
                # Descartamos coordenadas fuera de los límites del mapa
                if 0 <= nx < width and 0 <= ny < height:
                    current_value = self.get_density_factor(nx, ny, context)
                    
                    if mode == "min" and current_value < best_value:
                        best_value = current_value
                        best_cell = (nx, ny)
                    elif mode == "max" and current_value > best_value:
                        best_value = current_value
                        best_cell = (nx, ny)
                            
        return best_cell

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Cumple el contrato de la interfaz base sin realizar mutaciones directas."""
        pass