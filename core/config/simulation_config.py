"""
Módulo centralizado de configuración (core/config/simulation_config.py).

Responsabilidad: 
Proveer una única fuente de verdad para todas las constantes, probabilidades y 
límites biológicos del motor.

Diseño:
- Uso de clases contenedoras (Dataclasses implícitas) para cada subsistema.
- Tipado fuerte para facilitar el autocompletado y evitar errores de 'KeyError'.
- Acceso mediante métodos de seguridad para permitir la mutación en runtime.
"""

import logging
from typing import Any

# =============================================================================
# DEFINICIÓN DE SUBSISTEMAS DE CONFIGURACIÓN
# =============================================================================

class TimeConfig:
    """Parámetros de resolución temporal."""
    def __init__(self) -> None:
        self.days_per_tick: float = 30.0

class AdoptionsConfig:
    """Umbrales biológicos y legales para el sistema de adopciones."""
    def __init__(self) -> None:
        self.max_orphan_age_days: float = 6205.0   # 17 años
        self.min_adoptive_age_days: float = 9125.0 # 25 años

class CognitionConfig:
    """Parámetros de memoria, trauma y psicología de los agentes."""
    def __init__(self) -> None:
        self.base_forgetting_rate: float = 0.2
        self.overcrowding_threshold: float = 1.3
        self.overcrowding_impact: float = 0.1
        self.sickness_impact: float = 0.15

class ReproductionConfig:
    """Límites y probabilidades del sistema de reproducción."""
    def __init__(self) -> None:
        self.base_conception_chance: float = 0.22
        self.single_mother_conception_chance: float = 0.03
        self.miscarriage_chance_sick: float = 0.25
        self.min_age_days: float = 6570.0  # 18 años
        self.max_age_days: float = 16425.0 # 45 años
        self.pregnancy_duration_days: float = 270.0
        self.mutation_factor: float = 0.05
        self.min_genome_value: float = 0.01

class DiseasesConfig:
    """Parámetros de propagación y comportamiento epidemiológico."""
    def __init__(self) -> None:
        self.base_outbreak_chance: float = 0.02
        self.base_transmission_chance: float = 0.18
        self.base_recovery_chance: float = 0.15
        self.base_lethality_rate: float = 0.06
        self.transmission_radius: int = 2
        self.environmental_transmission_rate: float = 0.15

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
        self.hard_cap_age_days: float = 41975.0 # Límite biológico absoluto
        self.density_penalty_threshold: float = 1.2
        self.density_penalty_multiplier: float = 1.5
        self.alpha_base: float = 0.0001
        self.beta_base: float = 0.08
        self.sickness_penalty_multiplier: float = 2.5
        self.min_sickness_penalty: float = 1.1

class MarriageConfig:
    """Reglas de comportamiento social y emparejamiento."""
    def __init__(self) -> None:
        self.min_marriage_age_days: float = 6570.0
        self.courtship_radius: int = 3
        self.base_marriage_chance: float = 0.15
        self.love_at_first_sight_chance: float = 0.03

class EnvironmentConfig:
    """Restricciones espaciales y de recursos."""
    def __init__(self) -> None:
        self.sector_size: int = 10
        self.carrying_capacity: int = 200
        self.max_agents_per_sector: int = 8
        self.max_viral_load: float = 10.0
        self.viral_decay_factor: float = 0.90

class GenealogyConfig:
    """Parámetros de rastreo histórico y restricciones de parentesco."""
    def __init__(self) -> None:
        self.consanguinity_limit: int = 3  # Grado de parentesco prohibido para matrimonio

class MetricsConfig:
    """Parámetros para la recolección de métricas poblacionales."""
    def __init__(self) -> None:
        # Guardar un registro cada 1.0 días biológicos (ajustable)
        self.snapshot_interval_days: float = 1.0 

# =============================================================================
# CONFIGURACIÓN MAESTRA
# =============================================================================

class SimulationConfig:
    """Configuración maestra que agrupa todos los subsistemas."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("SimulationConfig")
        
        # Subsistemas
        self.time = TimeConfig()
        self.reproduction = ReproductionConfig()
        self.diseases = DiseasesConfig()
        self.mortality = MortalityConfig()
        self.marriage = MarriageConfig()
        self.environment = EnvironmentConfig()
        self.adoptions = AdoptionsConfig()
        self.cognition = CognitionConfig()
        self.evolution = EvolutionConfig()
        self.free_will = FreeWillConfig()
        self.genealogy = GenealogyConfig()
        self.metrics = MetricsConfig()

    def set_parameter(self, category: str, key: str, value: Any) -> bool:
        """Modifica un valor mediante reflexión. Permite la mutación en runtime."""
        target_obj = getattr(self, category, None)
        if not target_obj or not hasattr(target_obj, key):
            self.logger.warning(f"Error: No existe {category}.{key}")
            return False
            
        old_val = getattr(target_obj, key)
        setattr(target_obj, key, value)
        self.logger.info(f"[CONFIG] {category}.{key} actualizado: {old_val} -> {value}")
        return True

    def get_parameter(self, category: str, key: str) -> Any:
        """Obtiene un parámetro de forma segura."""
        return getattr(getattr(self, category), key)