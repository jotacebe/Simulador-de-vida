"""Módulo que define la estructura biológica de los patógenos y sus mutaciones."""

import random

class Pathogen:
    """Representa una cepa viral específica con capacidad de propagación y mutación."""

    def __init__(self, family: str, variant_id: int, 
                 virulence: float, transmission: float, lethality: float) -> None:
        """Inicializa un patógeno.
        
        Args:
            family: Nombre de la familia del virus (ej: 'Influenza').
            variant_id: Número de la generación o cepa.
            virulence: Resistencia del virus frente al sistema inmune (Dificulta recuperación).
            transmission: Tasa base de contagio (R0).
            lethality: Modificador de daño celular (Aumenta el riesgo en MortalitySystem).
        """
        self.family = family
        self.variant_id = variant_id
        self.pathogen_id = f"{family}_v{variant_id}"
        
        self.virulence = virulence
        self.transmission = transmission
        self.lethality = lethality

    def mutate(self) -> 'Pathogen':
        """Genera una nueva variante mediante deriva genética estocástica.
        
        Aplica una desviación de hasta +/- 15% en los atributos del patógeno.
        """
        return Pathogen(
            family=self.family,
            variant_id=self.variant_id + 1,
            virulence=max(0.1, self.virulence * random.uniform(0.85, 1.15)),
            transmission=max(0.01, self.transmission * random.uniform(0.85, 1.15)),
            lethality=max(0.0, min(1.0, self.lethality * random.uniform(0.85, 1.15)))
        )