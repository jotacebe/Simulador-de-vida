"""
Ruta: entities/person/genome.py
Responsabilidad: Almacenar los rasgos hereditarios de una entidad y proporcionar
                 la capacidad de recombinación (cruce) con otros genomas,
                 incorporando la deriva genética y evolución poblacional real.
"""
import random

class Genome:
    def __init__(self, longevity: float = 1.0, sociability: float = 1.0, 
                 temperament: float = 1.0, fertility: float = 1.0, 
                 immunity: float = 1.0): 
        
        # Datos privados
        self._longevity = longevity
        self._sociability = sociability
        self._temperament = temperament
        self._fertility = fertility
        self._immunity = immunity

    @property
    def longevity(self) -> float: return self._longevity

    @property
    def sociability(self) -> float: return self._sociability

    @property
    def temperament(self) -> float: return self._temperament

    @property
    def fertility(self) -> float: return self._fertility

    @property
    def immunity(self) -> float: return self._immunity

    # ==========================================
    # COMPORTAMIENTO GENÉTICO (Motor Integrado)
    # ==========================================
    def combine(self, other_genome: 'Genome') -> 'Genome':
        """
        Calcula los genes de un recién nacido.
        Integra la lógica de herencia (promedio), mutación (deriva genética) 
        y clamping (límites biológicos) para evitar la creación de superhumanos.
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