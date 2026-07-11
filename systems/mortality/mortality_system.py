"""Módulo que define el motor probabilístico de mortalidad del ecosistema.

Implementa un modelo de Gompertz-Makeham expandido, evaluando no solo el 
desgaste biológico, sino también la energía disponible, el estrés psicológico,
la presión del entorno ambiental, el historial médico de la entidad, el
trauma por abandono en huérfanos sin tutela, y la letalidad de las infecciones
activas.

La letalidad de cada patógeno activo se integra en el cálculo de mortalidad,
permitiendo que enfermedades más letales (ej: Ébola con letalidad 0.95) tengan
un impacto significativamente mayor que enfermedades leves (ej: gripe con
letalidad 0.01).
"""

import random
import math
import logging
from typing import Any

from systems.environment.environment_context import EnvironmentContext
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from core.config.simulation_config import SimulationConfig


class MortalitySystem:
    """Motor de mortalidad multifactorial con diagnósticos detallados."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada.
        
        Args:
            config: Configuración maestra de la simulación.
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def _calculate_multifactorial_risk(self, person: Any, pressure: float) -> float:
        """Calcula la probabilidad diaria de fallecimiento (Hazard Rate) holística.
        
        Integra la genética base (Gompertz) multiplicándola por los factores
        dinámicos de desgaste vital (energía, estrés, trauma, abandono) y
        la letalidad de las infecciones activas.
        
        Args:
            person: Entidad a evaluar.
            pressure: Presión ambiental local.
            
        Returns:
            Riesgo diario de muerte (hazard rate).
        """
        mortality_cfg = self.config.mortality
        adoptions_cfg = self.config.adoptions
        time_cfg = self.config.time
        
        # 1. RIESGO BASE POR SENESCENCIA (Curva biológica natural)
        adjusted_beta_years = mortality_cfg.beta_base / max(mortality_cfg.genome_clamping, person.genome.longevity)
        adjusted_beta_days = adjusted_beta_years / time_cfg.days_per_year
        base_hazard = (mortality_cfg.alpha_base * math.exp(adjusted_beta_days * person.age)) / time_cfg.days_per_year
        
        # 2. PENALIZACIONES FENOTÍPICAS (Estados volátiles)
        # La falta de energía dispara el riesgo exponencialmente (hasta 5x)
        energy_level = person.emotions.get("energy", 1.0)
        energy_penalty = 1.0 + ((1.0 - energy_level) * 5.0)
        
        # El estrés crónico y los traumas devalúan la resistencia basal
        stress_level = person.emotions.get("stress", 0.0)
        stress_penalty = 1.0 + (stress_level * 2.0)
        
        trauma_level = person.memory.get("trauma_overcrowding", 0.0)
        trauma_penalty = 1.0 + (trauma_level * 3.0)

        # PENALIZACIÓN POR ABANDONO (Huérfanos sin tutela)
        abandonment_trauma = person.memory.get("trauma_abandonment", 0.0)
        abandonment_penalty = 1.0 + (abandonment_trauma * (adoptions_cfg.abandonment_mortality_multiplier - 1.0))

        # 3. PENALIZACIONES EXTERNAS (Entorno)
        environmental_penalty = 1.0 + (pressure * mortality_cfg.density_penalty_multiplier)
        
        # =====================================================================
        # NUEVO: PENALIZACIÓN POR ENFERMEDADES ACTIVAS (CON LETALIDAD)
        # =====================================================================
        # Calcular el riesgo combinado de todas las infecciones activas
        # usando letalidad × virulencia de cada patógeno
        sickness_penalty = 1.0
        if getattr(person, 'is_sick', False):
            # Sumar el riesgo de todas las infecciones activas
            total_infection_risk = 0.0
            for pathogen in person.active_pathogens.values():
                # Riesgo = letalidad × virulencia
                # Letalidad alta + virulencia alta = riesgo máximo
                infection_risk = pathogen.lethality * pathogen.virulence
                total_infection_risk += infection_risk
            
            # Aplicar el riesgo total como penalización
            # Usar la fórmula: penalty = base × (1 + risk)
            # Donde base es el multiplier y risk amplifica el efecto
            raw_sickness_penalty = mortality_cfg.sickness_penalty_multiplier * (1.0 + total_infection_risk)
            sickness_penalty = max(mortality_cfg.min_sickness_penalty, raw_sickness_penalty)
            
            # Logging detallado para debugging
            if total_infection_risk > 0.1:
                self.logger.debug(
                    "🦠 Agente %s tiene %d infecciones activas, riesgo total: %.2f, penalty: %.2f",
                    person.entity_id,
                    len(person.active_pathogens),
                    total_infection_risk,
                    sickness_penalty,
                )
            
        # Composición del riesgo total
        total_daily_risk = (
            base_hazard * energy_penalty * stress_penalty * trauma_penalty * 
            abandonment_penalty * environmental_penalty * sickness_penalty
        )
            
        return total_daily_risk

    def _diagnose_cause_of_death(self, person: Any, pressure: float) -> str:
        """Realiza una autopsia analítica para determinar la causa forense principal.
        
        Evalúa el estado de las variables dinámicas de la entidad en el momento 
        del fallo sistémico para proveer datos ricos al EvolutionEngine.
        
        Args:
            person: Entidad fallecida.
            pressure: Presión ambiental local.
            
        Returns:
            Causa de muerte como string descriptivo.
        """
        energy = person.emotions.get("energy", 1.0)
        stress = person.emotions.get("stress", 0.0)
        trauma = person.memory.get("trauma_overcrowding", 0.0)
        abandonment_trauma = person.memory.get("trauma_abandonment", 0.0)
        is_sick = getattr(person, 'is_sick', False)

        # Prioridad 1: Condiciones combinadas catastróficas
        if is_sick and energy < 0.2:
            return "Sepsis / Fallo multiorgánico por agotamiento"
            
        # Prioridad 2: Fallos físicos extremos
        if energy < 0.1:
            return "Agotamiento metabólico extremo (Inanición)"
            
        if is_sick:
            return "Infección letal aguda"
            
        # Prioridad 3: Colapsos del entorno/psicológicos
        if trauma > 0.8 or pressure > 2.0:
            return "Asfixia/Traumatismo severo por hacinamiento"
        
        # Muerte por abandono prolongado
        if abandonment_trauma > 0.7 and stress > 0.8:
            return "Colapso sistémico por abandono prolongado"
            
        if stress > 0.85:
            return "Colapso cardiovascular inducido por estrés crónico"

        # Prioridad 4: Muerte biológica
        return "Fallo sistémico por senectud (Causas naturales)"

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Procesa el ciclo estocástico de mortalidad para todos los agentes activos.
        
        Args:
            state: Estado autoritativo del mundo.
            pending: Búfer transaccional de cambios.
            delta_days: Fracción de tiempo simulado.
            context: Contexto del entorno actual.
        """
        mortality_cfg = self.config.mortality

        for person in state.get_all_persons():
            # Filtro de integridad: Ya fallecido en este tick
            if person.entity_id in pending.deaths:
                continue
            
            # 1. SELECCIÓN NATURAL ESTRICTA (Límite Biológico Determinista - Telómeros)
            adjusted_cap = mortality_cfg.hard_cap_age_days * person.genome.longevity
            if person.age >= adjusted_cap:
                pending.register_death(person.entity_id, reason="Degradación telomérica total (Límite biológico)")
                self.logger.debug(f"Muerte natural absoluta (Límite): Agente {person.entity_id}")
                continue

            # 2. RIESGO PROBABILÍSTICO (Modelo de Supervivencia Gompertz + Entorno)
            pressure = context.get_local_pressure(person.x, person.y)
            
            daily_rate = self._calculate_multifactorial_risk(person, pressure)
            
            # Integración continua temporal (Poisson)
            total_death_chance = 1.0 - math.exp(-daily_rate * delta_days)

            if random.random() < total_death_chance:
                # El agente no ha superado la tirada de supervivencia. Generamos diagnóstico.
                reason = self._diagnose_cause_of_death(person, pressure)
                pending.register_death(person.entity_id, reason=reason)