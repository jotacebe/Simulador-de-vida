"""
Ruta: systems/mortality/mortality_system.py
Responsabilidad: Motor de mortalidad probabilístico (Gompertz-Makeham)
                 con presión de selección natural (Longevidad e Inmunidad)
                 normalizado por tiempo cronológico continuo (días).
"""
import random
import math
import logging
from systems.environment.environment_context import EnvironmentContext
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

class MortalitySystem:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("MortalitySystem")
        # Parámetros base anuales tradicionales de la curva de Gompertz
        self.alpha_base = 0.0001
        self.beta_base = 0.08 

    def _get_daily_hazard_rate(self, age_days: float, longevity: float, immunity: float, 
                               pressure: float, is_sick: bool, cfg: dict) -> float:
        """Calcula la tasa de riesgo diaria aplicando selección natural genética."""
        # 1. PRESIÓN SELECTIVA DE LONGEVIDAD: Ajustamos la curva de envejecimiento exponencial
        adjusted_beta_years = self.beta_base / longevity
        
        # Escalamos el crecimiento exponencial a días para evitar OverflowError
        adjusted_beta_days = adjusted_beta_years / 365.0
        
        # Gompertz diurno base: (alpha_base / 365) * exp(beta_days * age_days)
        daily_hazard = (self.alpha_base * math.exp(adjusted_beta_days * age_days)) / 365.0
        
        # Multiplicadores de riesgo ambientales leídos de la configuración
        density_multiplier = cfg.get("density_penalty_multiplier", 1.5)
        risk = daily_hazard * (1.0 + (pressure * density_multiplier))
        
        # 2. PRESIÓN SELECTIVA DE INMUNIDAD: Mitiga el impacto letal de la enfermedad
        if is_sick:
            # Si immunity es > 1.0, el multiplicador disminuye (mayor supervivencia)
            # Si immunity es < 1.0, el multiplicador aumenta (muerte más rápida)
            sickness_penalty = 2.5 / immunity
            risk *= max(1.1, sickness_penalty)  # Aseguramos que estar enfermo siempre sume riesgo
            
        return risk

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        cfg = getattr(state.config, 'mortality', {})
        # Leemos el límite absoluto base en días (115 años por defecto)
        max_age_cap_days = cfg.get("hard_cap_age_days", 41975.0)

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue
            
            # 1. SELECCIÓN NATURAL: Muerte determinista por límite de edad biológica adaptativa
            # El gen de longevidad expande o contrae de forma absoluta el techo biológico de la entidad
            adjusted_cap = max_age_cap_days * person.genome.longevity
            if person.age >= adjusted_cap:
                pending.register_death(person.entity_id, reason="Vejez extrema (Límite biológico superado)")
                continue

            # 2. Riesgo probabilístico evolutivo (Gompertz-Makeham adaptativo)
            pressure = context.get_local_pressure(person.x, person.y)
            daily_rate = self._get_daily_hazard_rate(
                age_days=person.age, 
                longevity=person.genome.longevity, 
                immunity=person.genome.immunity,  # Pasamos el gen de inmunidad
                pressure=pressure, 
                is_sick=person.is_sick, 
                cfg=cfg
            )
            
            # Probabilidad exacta acumulada en el periodo delta_days: 1 - exp(-rate * delta_days)
            total_death_chance = 1.0 - math.exp(-daily_rate * delta_days)

            if random.random() < total_death_chance:
                reason = "Infección letal (Fallo inmunológico)" if person.is_sick else "Senescencia o estrés ambiental"
                pending.register_death(person.entity_id, reason=reason)