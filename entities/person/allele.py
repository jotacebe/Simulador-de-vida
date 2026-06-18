"""Modelo de partícula hereditaria fundamental (Leyes de Mendel)."""

import random
from dataclasses import dataclass

@dataclass(frozen=True)
class Allele:
    """Unidad básica de herencia que codifica una variante de un rasgo.
    
    Es inmutable tras su creación. Contiene tanto la expresión del rasgo 
    como su fuerza de dominancia relativa.
    """
    value: float
    dominance: float

    @classmethod
    def create_random(cls, base_value: float, mutation_range: float = 0.0) -> 'Allele':
        """Instancia un alelo aplicando deriva genética inicial.
        
        Args:
            base_value: El valor fenotípico central del rasgo (e.g., 1.0).
            mutation_range: Variación máxima al momento de la creación.
            
        Returns:
            Un nuevo alelo con una fuerza de dominancia estocástica.
        """
        # La fuerza de dominancia determina si este alelo "vence" a otro en un par
        dominance_strength = random.random()
        
        mutated_value = base_value
        if mutation_range > 0:
            mutated_value += random.uniform(-mutation_range, mutation_range)
            
        # Clamping biológico base (0.1 a 3.0 para evitar desbordamientos matemáticos)
        final_value = max(0.1, min(3.0, mutated_value))
        
        return cls(value=final_value, dominance=dominance_strength)


class Gene:
    """Locus genético compuesto por un par de alelos (Diploidía)."""

    def __init__(self, allele_a: Allele, allele_b: Allele) -> None:
        """Inicializa un gen con los alelos aportados por los progenitores."""
        self.allele_a = allele_a
        self.allele_b = allele_b

    def express(self) -> float:
        """Calcula el fenotipo (rasgo visible) basado en la dominancia.
        
        Rompe la herencia por mezcla: el alelo dominante se expresa al 100%,
        el recesivo se silencia (pero permanece en el genoma para la descendencia).
        
        Returns:
            El valor numérico del alelo ganador.
        """
        if self.allele_a.dominance >= self.allele_b.dominance:
            return self.allele_a.value
        return self.allele_b.value

    def meiosis(self) -> Allele:
        """Segregación independiente: devuelve un alelo al azar para la herencia."""
        return self.allele_a if random.random() < 0.5 else self.allele_b