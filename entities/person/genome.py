"""Módulo que define la genética y herencia de las entidades del simulador."""

import random

class Genome:
    """Representa el conjunto de rasgos genéticos de una entidad y su evolución."""

    def __init__(self, longevity: float = 1.0, sociability: float = 1.0, 
                 temperament: float = 1.0, fertility: float = 1.0, 
                 immunity: float = 1.0):
        """Inicializa un nuevo genoma con valores biológicos base."""
        self._longevity = longevity
        self._sociability = sociability
        self._temperament = temperament
        self._fertility = fertility
        self._immunity = immunity

    @property
    def longevity(self) -> float:
        """Devuelve el factor de longevidad de la entidad."""
        return self._longevity
    
    @longevity.setter
    def longevity(self, value: float) -> None:
        """Establece el factor de longevidad de la entidad."""
        self._longevity = value

    @property
    def sociability(self) -> float:
        """Devuelve el factor de sociabilidad de la entidad."""
        return self._sociability
    
    @sociability.setter
    def sociability(self, value: float) -> None:
        """Establece el factor de sociabilidad de la entidad."""
        self._sociability = value

    @property
    def temperament(self) -> float:
        """Devuelve el factor de temperamento de la entidad."""
        return self._temperament
    
    @temperament.setter
    def temperament(self, value: float) -> None:
        """Establece el factor de temperamento de la entidad."""
        self._temperament = value

    @property
    def fertility(self) -> float:
        """Devuelve el factor de fertilidad de la entidad."""
        return self._fertility
    
    @fertility.setter
    def fertility(self, value: float) -> None:
        """Establece el factor de fertilidad de la entidad."""
        self._fertility = value

    @property
    def immunity(self) -> float:
        """Devuelve el factor de inmunidad de la entidad."""
        return self._immunity
    
    @immunity.setter
    def immunity(self, value: float) -> None:
        """Establece el factor de inmunidad de la entidad."""
        self._immunity = value

    def combine(self, other_genome: 'Genome') -> 'Genome':
        """Combina este genoma con otro para generar un nuevo descendiente.

        Aplica herencia por promedio, añade deriva genética mediante mutación
        y restringe los valores resultantes dentro de los límites biológicos.
        """
        def get_inherited_value(v1: float, v2: float) -> float:
            # 1. Herencia (Promedio de los padres)
            base = (v1 + v2) / 2.0
            
            # 2. Mutación (Deriva genética: +/- 2% de variabilidad)
            mutation = random.uniform(-0.02, 0.02)
            
            # 3. Resultado (Clamping: mantenemos el valor en rangos biológicos 0.5 - 1.5)
            return max(0.5, min(1.5, base + mutation))

        return Genome(
            longevity=get_inherited_value(self.longevity, other_genome.longevity),
            sociability=get_inherited_value(self.sociability, other_genome.sociability),
            temperament=get_inherited_value(self.temperament, other_genome.temperament),
            fertility=get_inherited_value(self.fertility, other_genome.fertility),
            immunity=get_inherited_value(self.immunity, other_genome.immunity)
        )