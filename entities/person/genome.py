"""Módulo que define la genética y herencia mendeliana de las entidades.

Responsabilidad:
Actuar como el contenedor del genotipo diploide de un individuo.
Define la recombinación por segregación independiente y mutación puntual.
"""

import random
import logging
from typing import Optional
from .allele import Allele, Gene

class Genome:
    """Conjunto de pares de alelos que determinan los rasgos de una entidad.
    
    Implementa un sistema mendeliano puro con dominancia y recesividad,
    erradicando la pérdida de varianza (convergencia a la media).
    """

    def __init__(self, 
                 longevity: Optional[Gene] = None, 
                 sociability: Optional[Gene] = None, 
                 temperament: Optional[Gene] = None, 
                 fertility: Optional[Gene] = None, 
                 immunity: Optional[Gene] = None,
                 species_baseline: str = "human"):
        """Inicializa el genoma, generando genes fundadores si no se proveen."""
        
        self._species_baseline = species_baseline
        self.logger = logging.getLogger(self.__class__.__name__)

        # Si no se proveen genes, creamos homocigotos aleatorios (Generación 0)
        self._genes = {
            "longevity": longevity or self._create_founder_gene(1.0),
            "sociability": sociability or self._create_founder_gene(1.0),
            "temperament": temperament or self._create_founder_gene(1.0),
            "fertility": fertility or self._create_founder_gene(1.0),
            "immunity": immunity or self._create_founder_gene(1.0),
        }

    def _create_founder_gene(self, base_val: float) -> Gene:
        """Crea un gen inicial aplicando una ligera diversidad a la especie base."""
        return Gene(
            allele_a=Allele.create_random(base_val, 0.1),
            allele_b=Allele.create_random(base_val, 0.1)
        )

    # ==========================================
    # PROPERTIES FENOTÍPICAS (Interfaz retrocompatible)
    # ==========================================
    # Los sistemas leerán estas propiedades creyendo que son flotantes estáticos,
    # pero bajo el capó están llamando a la expresión de dominancia genética.

    @property
    def longevity(self) -> float: return self._genes["longevity"].express()
    
    @property
    def sociability(self) -> float: return self._genes["sociability"].express()
    
    @property
    def temperament(self) -> float: return self._genes["temperament"].express()
    
    @property
    def fertility(self) -> float: return self._genes["fertility"].express()
    
    @property
    def immunity(self) -> float: return self._genes["immunity"].express()

    @property
    def species_baseline(self) -> str: return self._species_baseline

    # ==========================================
    # MOTOR DE HERENCIA MENDELIANA
    # ==========================================
    def combine(self, other_genome: Optional['Genome']) -> 'Genome':
        """Cruza este genotipo con el de una pareja mediante meiosis.

        Args:
            other_genome: Genoma del progenitor masculino (puede ser None para partenogénesis).
            
        Returns:
            Un nuevo Genome recombinado.
        """
        # Partenogénesis: Si no hay padre, la madre aporta ambos alelos (clonación con mutación)
        if other_genome is None:
            other_genome = self

        if self._species_baseline != other_genome.species_baseline:
            self.logger.warning("Cruce interespecie. El híbrido heredará la línea materna.")

        new_genes = {}
        mutation_rate = 0.05 # Probabilidad de mutación cósmica severa

        # Para cada locus genético, extraemos un alelo de cada padre
        for trait_name in self._genes.keys():
            mother_gene = self._genes[trait_name]
            father_gene = other_genome._genes[trait_name]

            # Meiosis: Un alelo de la madre y uno del padre
            allele_m = mother_gene.meiosis()
            allele_f = father_gene.meiosis()

            # Mutación puntual (Deriva genética)
            if random.random() < mutation_rate:
                allele_m = Allele.create_random(allele_m.value, 0.15)
            if random.random() < mutation_rate:
                allele_f = Allele.create_random(allele_f.value, 0.15)

            new_genes[trait_name] = Gene(allele_m, allele_f)

        return Genome(
            longevity=new_genes["longevity"],
            sociability=new_genes["sociability"],
            temperament=new_genes["temperament"],
            fertility=new_genes["fertility"],
            immunity=new_genes["immunity"],
            species_baseline=self._species_baseline
        )