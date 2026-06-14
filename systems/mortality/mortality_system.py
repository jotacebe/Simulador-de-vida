"""Módulo que define el motor probabilístico de mortalidad del ecosistema."""

import random
import math
import logging
from systems.environment.environment_context import EnvironmentContext
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from core.config.simulation_config import SimulationConfig

class MortalitySystem:
    """Motor de mortalidad probabilístico (Gompertz-Makeham) con selección natural."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada."""
        self.config = config
        self.logger = logging.getLogger("MortalitySystem")

    def _get_daily_hazard_rate(self, age_days: float, longevity: float, 
                               immunity: float, pressure: float, 
                               is_sick: bool) -> float:
        """Calcula la probabilidad diaria de fallecimiento basada en genética y entorno."""
        mortality_cfg = self.config.mortality
        
        # Ajuste de beta: A mayor longevidad genética, más lenta es la curva de Gompertz.
        # Se aplica un clamping de 0.01 para evitar divisiones por cero si el genoma es defectuoso.
        adjusted_beta_years = mortality_cfg.beta_base / max(0.01, longevity)
        adjusted_beta_days = adjusted_beta_years / 365.0
        
        # Cálculo del riesgo base diario
        daily_hazard = (mortality_cfg.alpha_base * math.exp(adjusted_beta_days * age_days)) / 365.0
        
        # Penalización por densidad de población (Hacinamiento)
        risk = daily_hazard * (1.0 + (pressure * mortality_cfg.density_penalty_multiplier))
        
        # Penalización inmunológica si cursa una enfermedad
        if is_sick:
            sickness_penalty = mortality_cfg.sickness_penalty_multiplier / max(0.01, immunity)
            risk *= max(mortality_cfg.min_sickness_penalty, sickness_penalty)
            
        return risk

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa el ciclo estocástico de mortalidad para todos los agentes activos."""
        mortality_cfg = self.config.mortality

        for person in state.get_all_persons():
            # Filtro de integridad referencial
            if person.entity_id in pending.deaths:
                continue
            
            # 1. SELECCIÓN NATURAL (Límite Biológico Determinista)
            adjusted_cap = mortality_cfg.hard_cap_age_days * person.genome.longevity
            if person.age >= adjusted_cap:
                pending.register_death(person.entity_id, reason="Vejez extrema")
                continue

            # 2. RIESGO PROBABILÍSTICO (Gompertz)
            pressure = context.get_local_pressure(person.x, person.y)
            
            daily_rate = self._get_daily_hazard_rate(
                age_days=person.age, 
                longevity=person.genome.longevity, 
                immunity=person.genome.immunity,
                pressure=pressure, 
                is_sick=person.is_sick
            )
            
            # Integración continua temporal: P = 1 - e^(-rate * t)
            total_death_chance = 1.0 - math.exp(-daily_rate * delta_days)

            # Resolución del azar contra el entorno
            if random.random() < total_death_chance:
                reason = "Infección letal" if person.is_sick else "Senescencia/Estrés"
                pending.register_death(person.entity_id, reason=reason)