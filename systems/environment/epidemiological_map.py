"""Estructura de datos espacial para el rastreo de cargas virales ambientales."""

from collections import defaultdict
import logging

class EpidemiologicalMap:
    """Almacén de datos (Sparse Grid) para la concentración de patógenos en el mapa."""

    def __init__(self, max_viral_load: float) -> None:
        """Inicializa la cuadrícula dispersa con el límite biológico del virus."""
        # defaultdict permite no consumir memoria RAM en zonas seguras (vacías)
        self.grid = defaultdict(float)
        self.max_viral_load = max_viral_load
        self.logger = logging.getLogger("EpidemiologicalMap")

    def add_viral_load(self, x: int, y: int, amount: float) -> None:
        """Incrementa la carga viral de una coordenada, topada por el límite máximo."""
        coord = (int(x), int(y))
        new_val = self.grid[coord] + amount
        self.grid[coord] = min(new_val, self.max_viral_load)

    def get_viral_load(self, x: int, y: int) -> float:
        """Devuelve la carga viral presente en una coordenada específica."""
        return self.grid.get((int(x), int(y)), 0.0)

    def decay_viral_load(self, factor: float) -> None:
        """Aplica disipación atmosférica reduciendo la carga de todo el mapa.
        
        Elimina las coordenadas cuya carga es insignificante para liberar memoria.
        """
        keys_to_delete = []
        for coord in self.grid:
            self.grid[coord] *= factor
            if self.grid[coord] < 0.01:
                keys_to_delete.append(coord)
        
        for coord in keys_to_delete:
            del self.grid[coord]