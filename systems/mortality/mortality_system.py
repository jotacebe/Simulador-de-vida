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
        """Inicializa el sistema con la configuración centralizada."""
        self.config = config
        self.logger = logging.getLogger("MortalitySystem")
        
        # Parámetros base para la curva de Gompertz.
        # Alpha: Mortalidad basal (independiente de la edad).
        # Beta: Velocidad de envejecimiento (exponencial).
        self.alpha_base = 0.0001
        self.beta_base = 0.08 

    def _get_daily_hazard_rate(self, age_days: float, longevity: float, 
                               immunity: float, pressure: float, 
                               is_sick: bool) -> float:
        """Calcula la probabilidad diaria de fallecimiento basada en rasgos genéticos."""
        # Obtenemos los parámetros desde la configuración centralizada tipada
        mortality_cfg = self.config.mortality
        
        # Ajuste de beta: A mayor longevidad genética, más lenta es la curva de Gompertz.
        adjusted_beta_years = self.beta_base / longevity
        adjusted_beta_days = adjusted_beta_years / 365.0
        
        # Cálculo del riesgo base diario usando la función de Gompertz.
        daily_hazard = (self.alpha_base * math.exp(adjusted_beta_days * age_days)) / 365.0
        
        # Aplicamos penalización por densidad de población según el contexto ambiental.
        # Si la presión supera el umbral, multiplicamos el riesgo.
        density_multiplier = mortality_cfg.density_penalty_multiplier
        risk = daily_hazard * (1.0 + (pressure * density_multiplier))
        
        # Si el agente está enfermo, aplicamos una penalización adicional.
        # La inmunidad mitiga esta penalización (inversamente proporcional).
        if is_sick:
            sickness_penalty = 2.5 / immunity
            risk *= max(1.1, sickness_penalty)
            
        return risk

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa el ciclo de mortalidad para todos los agentes activos."""
        mortality_cfg = self.config.mortality

        for person in state.get_all_persons():
            # Filtro de seguridad: si ya está registrado para morir, saltamos el cálculo.
            if person.entity_id in pending.deaths:
                continue
            
            # 1. SELECCIÓN NATURAL (Determinista):
            # Comprobamos el límite biológico (hard cap) ajustado por la genética.
            adjusted_cap = mortality_cfg.hard_cap_age_days * person.genome.longevity
            if person.age >= adjusted_cap:
                pending.register_death(person.entity_id, reason="Vejez extrema")
                continue

            # 2. RIESGO PROBABILÍSTICO (Estocástico):
            # Obtenemos la presión local del entorno para evaluar riesgos externos.
            pressure = context.get_local_pressure(person.x, person.y)
            
            # Calculamos la tasa de peligro diaria.
            daily_rate = self._get_daily_hazard_rate(
                age_days=person.age, 
                longevity=person.genome.longevity, 
                immunity=person.genome.immunity,
                pressure=pressure, 
                is_sick=person.is_sick
            )
            
            # Convertimos la tasa diaria a probabilidad acumulada para el periodo delta_days.
            # Fórmula: P = 1 - e^(-rate * t)
            total_death_chance = 1.0 - math.exp(-daily_rate * delta_days)

            # Ejecutamos el azar contra la probabilidad calculada.
            if random.random() < total_death_chance:
                reason = "Infección letal" if person.is_sick else "Senescencia/Estrés ambiental"
                pending.register_death(person.entity_id, reason=reason)