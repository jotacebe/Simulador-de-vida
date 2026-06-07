"""
Ruta: systems/environment/density_system.py
Responsabilidad: Gestión del mapa de densidad y consultas espaciales de optimización.
"""
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext

class DensitySystem:
    def __init__(self, config):
        self.config = config
        self.sector_size = 10
        self.max_agents_per_sector = 8

    def get_density_factor(self, x: int, y: int) -> float:
        """Retorna el factor de densidad en una coordenada específica."""
        # Nota: Aquí iría tu lógica real de cálculo de densidad
        return 0.5 

    def find_best_nearby_cell(self, x: int, y: int, radius: int, mode: str, width: int, height: int) -> tuple:
        """
        SERVICIO: Busca la mejor celda en un radio dado basándose en la densidad.
        mode: 'min' (para huida estratégica), 'max' (para búsqueda de comunidad).
        """
        best_cell = (x, y)
        best_value = self.get_density_factor(x, y)
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                
                # Verificar límites
                if 0 <= nx < width and 0 <= ny < height:
                    current_value = self.get_density_factor(nx, ny)
                    
                    if mode == "min":
                        if current_value < best_value:
                            best_value = current_value
                            best_cell = (nx, ny)
                    elif mode == "max":
                        if current_value > best_value:
                            best_value = current_value
                            best_cell = (nx, ny)
                            
        return best_cell

    def process(self, state: WorldState, pending: PendingChanges, delta_days: int, context: EnvironmentContext) -> None:
        """Actualización del sistema de densidad."""
        # Aunque actualmente no necesitemos registrar cambios en 'pending',
        # debemos aceptar el argumento para cumplir con el contrato del pipeline.
        pass