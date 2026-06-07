# application/core/state/world_grid.py

from typing import List, Dict, Any

class WorldGrid:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._cells: Dict[tuple, List[Any]] = {}

    def get_occupants_at(self, x: int, y: int) -> List[Any]:
        return self._cells.get((x, y), [])

    def can_move_to(self, x: int, y: int) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return len(self.get_occupants_at(x, y)) == 0

    def place_person(self, person: Any, x: int, y: int) -> None:
        if (x, y) not in self._cells:
            self._cells[(x, y)] = []
        self._cells[(x, y)].append(person)
        person.x = x
        person.y = y

    def remove_person(self, person: Any) -> None:
        coord = (person.x, person.y)
        if coord in self._cells and person in self._cells[coord]:
            self._cells[coord].remove(person)
            if not self._cells[coord]:
                del self._cells[coord]

    # --- NUEVA FUNCIONALIDAD: Cálculo de densidad integrado ---
    def get_density_at(self, x: int, y: int) -> int:
        """Devuelve cuántas personas hay en una coordenada específica."""
        return len(self.get_occupants_at(x, y))

    def get_area_density(self, x: int, y: int, radius: int) -> int:
        """Devuelve la densidad total en un radio alrededor de un punto."""
        count = 0
        for i in range(x - radius, x + radius + 1):
            for j in range(y - radius, y + radius + 1):
                count += len(self.get_occupants_at(i, j))
        return count