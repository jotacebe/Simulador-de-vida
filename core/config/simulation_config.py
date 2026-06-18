"""Módulo centralizado de configuración de la simulación.

Responsabilidad: 
Proveer una única fuente de verdad (Single Source of Truth) para todas las constantes, 
probabilidades y límites biológicos del motor. Esto elimina números mágicos y asegura 
que todos los sistemas compartan las mismas reglas físicas y temporales.
"""

import logging
from typing import Any

class EngineConfig:
    """Parámetros de ejecución del bucle principal."""
    
    def __init__(self) -> None:
        self.total_days: float = 365.0
        self.delta_days: float = 1.0


class AdoptionsConfig:
    """Umbrales biológicos y legales para el sistema de adopciones."""
    
    def __init__(self) -> None:
        self.max_orphan_age_days: float = 6205.0   
        self.min_adoptive_age_days: float = 9125.0 
        self.max_children_for_adoption: int = 3


class CognitionConfig:
    """Parámetros de memoria, trauma y psicología de los agentes."""
    
    def __init__(self) -> None:
        self.base_forgetting_rate: float = 0.2
        self.overcrowding_threshold: float = 1.3
        self.overcrowding_impact: float = 0.1
        self.sickness_impact: float = 0.15
        self.temperament_modifier: float = 0.5     
        self.max_trauma_cap: float = 1.0           


class ReproductionConfig:
    """Límites, ventanas de fertilidad y probabilidades de reproducción."""
    
    def __init__(self) -> None:
        self.single_mother_conception_chance: float = 0.03
        self.miscarriage_chance_sick: float = 0.25
        self.pregnancy_duration_days: float = 270.0
        self.mutation_factor: float = 0.05
        self.min_genome_value: float = 0.01
        self.min_fertility_age_days: float = 6570.0   
        self.max_fertility_age_days: float = 16425.0  
        self.daily_birth_rate: float = 0.0033         
        self.base_conception_chance: float = 0.15     


class MovementConfig:
    """Parámetros de desplazamiento espacial."""
    
    def __init__(self) -> None:
        self.base_speed: float = 0.5  
        self.proximity_threshold: float = 0.1  


class DiseasesConfig:
    """Parámetros de propagación y comportamiento epidemiológico."""
    
    def __init__(self) -> None:
        self.base_outbreak_chance: float = 0.02
        self.base_transmission_chance: float = 0.18
        self.base_recovery_chance: float = 0.15
        self.base_lethality_rate: float = 0.06
        self.transmission_radius: int = 2
        self.environmental_transmission_rate: float = 0.15
        self.immunity_clamping: float = 0.1  


class EvolutionConfig:
    """Parámetros para la analítica macroevolutiva y recolección de métricas."""
    
    def __init__(self) -> None:
        self.snapshot_interval_days: float = 30.0
        self.variance_extinction_threshold: float = 0.01
        self.mean_extinction_threshold: float = 0.2


class FreeWillConfig:
    """Parámetros de comportamiento autónomo y umbrales de decisión."""
    
    def __init__(self) -> None:
        self.base_daily_chance: float = 0.005
        self.divorce_temperament_threshold: float = 0.75
        self.divorce_chance_multiplier: float = 0.1
        self.migration_density_threshold: float = 1.6
        self.migration_sociability_threshold: float = 0.3
        self.migration_chance_multiplier: float = 0.2
        self.migration_radius: int = 12
        self.fertility_rebellion_children_threshold: int = 3
        self.fertility_rebellion_temperament_threshold: float = 0.7


class MortalityConfig:
    """Reglas de la curva de Gompertz y selección natural."""
    
    def __init__(self) -> None:
        self.base_life_expectancy_days: float = 25550.0
        self.infant_threshold_days: float = 1095.0
        self.infant_mortality_rate: float = 0.02
        self.hard_cap_age_days: float = 41975.0 
        self.density_penalty_threshold: float = 1.2
        self.density_penalty_multiplier: float = 1.5
        self.alpha_base: float = 0.0001
        self.beta_base: float = 0.08
        self.sickness_penalty_multiplier: float = 2.5
        self.min_sickness_penalty: float = 1.1
        self.genome_clamping: float = 0.01  


class RelationshipsConfig:
    """Parámetros de cortejo, emparejamiento, noviazgo y selección sexual."""
    
    def __init__(self) -> None:
        self.min_marriage_age_days: float = 6570.0    
        self.ideal_marriage_age_days: float = 8395.0  
        self.courtship_radius: int = 20
        self.base_marriage_chance: float = 0.01
        self.daily_marriage_rate: float = 0.00137
        self.love_at_first_sight_chance: float = 0.001


class EnvironmentConfig:
    """Restricciones espaciales y de capacidad de carga de recursos."""
    
    def __init__(self) -> None:
        self.sector_size: int = 10
        self.carrying_capacity: int = 200
        self.max_agents_per_sector: int = 8
        self.max_viral_load: float = 10.0
        self.viral_decay_factor: float = 0.90


class TimeConfig:
    """Parámetros para la progresión temporal macroscópica y ciclos vitales."""
    
    def __init__(self) -> None:
        self.adult_age_days: float = 6570.0   
        self.senior_age_days: float = 21900.0 
        self.days_per_month: float = 30.0    
        self.days_per_year: float = 365.0    


class GenealogyConfig:
    """Parámetros de rastreo histórico y restricciones de parentesco."""
    
    def __init__(self) -> None:
        self.consanguinity_limit: int = 3  


class MetricsConfig:
    """Parámetros para la recolección de métricas poblacionales."""
    
    def __init__(self) -> None:
        self.snapshot_interval_days: float = 1.0 


class SimulationConfig:
    """Configuración maestra que agrupa y expone todos los subsistemas.
    
    Debe ser instanciada una sola vez al arrancar el motor y pasada por
    inyección de dependencias a los sistemas, garantizando consistencia global.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("SimulationConfig")
        
        self.engine = EngineConfig()
        self.time = TimeConfig()
        self.reproduction = ReproductionConfig()
        self.diseases = DiseasesConfig()
        self.mortality = MortalityConfig()
        self.environment = EnvironmentConfig()
        self.adoptions = AdoptionsConfig()
        self.cognition = CognitionConfig()
        self.evolution = EvolutionConfig()
        self.free_will = FreeWillConfig()
        self.genealogy = GenealogyConfig()
        self.metrics = MetricsConfig()
        self.movement = MovementConfig()
        self.relationships = RelationshipsConfig()

    def set_parameter(self, category: str, key: str, value: Any) -> bool:
        """Modifica un parámetro en caliente durante la ejecución."""
        target_obj = getattr(self, category, None)
        if not target_obj or not hasattr(target_obj, key):
            self.logger.warning(f"[CONFIG] Error: No existe la propiedad {category}.{key}")
            return False
            
        old_val = getattr(target_obj, key)
        setattr(target_obj, key, value)
        self.logger.info(f"[CONFIG] {category}.{key} actualizado dinámicamente: {old_val} -> {value}")
        return True

    def get_parameter(self, category: str, key: str, default: Any = None) -> Any:
        """Recupera un parámetro de forma segura."""
        target_obj = getattr(self, category, None)
        if not target_obj:
            self.logger.error(f"[CONFIG] Categoría '{category}' no encontrada en el sistema.")
            return default
        return getattr(target_obj, key, default)