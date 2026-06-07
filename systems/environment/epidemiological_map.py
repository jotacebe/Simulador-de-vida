"""
Ruta: systems/environment/epidemiological_map.py
Responsabilidad: Almacén de datos espacial para cargas virales (Sparse Grid).
"""
from collections import defaultdict
import logging

class EpidemiologicalMap:
    def __init__(self, max_viral_load: float = 10.0):
        # Usamos defaultdict para no consumir memoria en zonas vacías
        self.grid = defaultdict(float)
        self.max_viral_load = max_viral_load
        self.logger = logging.getLogger("EpidemiologicalMap")

    def add_viral_load(self, x: int, y: int, amount: float):
        """Añade carga viral a una coordenada, limitando por un máximo."""
        coord = (int(x), int(y))
        new_val = self.grid[coord] + amount
        self.grid[coord] = min(new_val, self.max_viral_load)

    def get_viral_load(self, x: int, y: int) -> float:
        """Devuelve la carga viral en una coordenada específica."""
        return self.grid.get((int(x), int(y)), 0.0)

    def decay_viral_load(self, factor: float = 0.95):
        """Reduce la carga viral en todo el mapa para simular desinfección/muerte del virus."""
        keys_to_delete = []
        for coord, load in self.grid.items():
            self.grid[coord] *= factor
            if self.grid[coord] < 0.01:
                keys_to_delete.append(coord)
        
        for coord in keys_to_delete:
            del self.grid[coord]