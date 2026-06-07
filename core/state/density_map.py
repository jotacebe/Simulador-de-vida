"""
Ruta: core/state/density_map.py
Responsabilidad: Dividir el mundo en cuadrantes y calcular el factor de hacinamiento.
"""
from typing import Dict, Tuple

class DensityMap:
    def __init__(self, width: int, height: int, sector_size: int = 10):
        self.width = width
        self.height = height
        self.sector_size = sector_size
        self.ideal_pop_per_sector = 5  # Habitantes ideales por sector (Ajustable)
        
        # Mapea (sector_x, sector_y) -> cantidad_de_personas
        self.grid: Dict[Tuple[int, int], int] = {}

    def build_heatmap(self, persons: list) -> None:
        """Reconstruye el mapa de calor desde cero basándose en las posiciones actuales."""
        self.grid.clear()
        for p in persons:
            sx = p.x // self.sector_size
            sy = p.y // self.sector_size
            self.grid[(sx, sy)] = self.grid.get((sx, sy), 0) + 1

    def get_density_factor(self, x: int, y: int) -> float:
        """
        Devuelve 1.0 si la densidad es óptima o baja.
        Devuelve > 1.0 si hay hacinamiento (Ej: 2.0 = Doble de población ideal).
        """
        sx = x // self.sector_size
        sy = y // self.sector_size
        count = self.grid.get((sx, sy), 0)
        
        if count <= self.ideal_pop_per_sector:
            return 1.0
            
        return count / self.ideal_pop_per_sector

    def get_low_density_sectors(self) -> list:
        """Devuelve una lista de coordenadas de sectores con espacio libre."""
        low_sectors = []
        max_sx = self.width // self.sector_size
        max_sy = self.height // self.sector_size
        
        for sx in range(max_sx):
            for sy in range(max_sy):
                if self.grid.get((sx, sy), 0) < self.ideal_pop_per_sector:
                    low_sectors.append((sx, sy))
        return low_sectors