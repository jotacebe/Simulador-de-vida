"""Módulo responsable de la interacción entre los agentes y los patógenos del entorno.

Gestiona la retroalimentación de enfermedades: los agentes infectados exhalan 
y contaminan el entorno (fómites), y las celdas altamente contaminadas 
infectan a los agentes sanos instanciando nuevas cepas ambientales.

Mejoras implementadas:
- Usa configuración centralizada (no valores hardcodeados)
- Contagio ambiental respeta fases de infección (solo contagioso/sintomático exhalan)
- Crea patógenos ambientales con propiedades realistas
"""

from __future__ import annotations

import logging
import math
import random

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.diseases.pathogen import Pathogen, InfectionPhase
from systems.environment.environment_context import EnvironmentContext


class EpidemiologicalSystem:
    """Gestiona el rastro viral dejado por enfermos y el contagio por fómites."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada.

        Args:
            config: Configuración compartida de la simulación.
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Procesa la retroalimentación virus-entorno-agente en cada tick.

        Args:
            state: Estado actual del mundo.
            pending: Búfer transaccional para encolar nuevas infecciones.
            delta_days: Fracción de tiempo simulado.
            context: Variables espaciales del entorno.
        """
        env_cfg = self.config.environment
        dis_cfg = self.config.diseases

        ep_map = state.epidemiological_map
        all_persons = state.get_all_persons()

        # =====================================================================
        # 1. PROPAGACIÓN: Los agentes enfermos contaminan el entorno
        # =====================================================================
        # Solo los agentes en fase contagiosa o sintomática exhalan virus
        for person in all_persons:
            if person.entity_id in pending.deaths:
                continue

            if getattr(person, "is_sick", False):
                # Verificar si tiene alguna infección en fase contagiosa
                is_contagious = False
                for infection_state in person.active_infections.values():
                    if infection_state.is_contagious():
                        is_contagious = True
                        break
                
                # Solo exhala virus si está en fase contagiosa
                if is_contagious:
                    # La cantidad exhalada es proporcional al tiempo transcurrido
                    exhalation_rate = env_cfg.viral_exhalation_rate
                    ep_map.add_viral_load(person.x, person.y, amount=(exhalation_rate * delta_days))

        # =====================================================================
        # 2. CONTAGIO: El entorno infecta a los agentes sanos
        # =====================================================================
        # Usar configuración centralizada
        base_transmission_rate = env_cfg.environmental_transmission_rate
        viral_load_threshold = env_cfg.viral_load_threshold
        viral_to_risk_factor = env_cfg.viral_to_risk_factor
        
        # Tasa diaria base de infección ambiental
        daily_transmission_rate = base_transmission_rate * viral_to_risk_factor

        for person in all_persons:
            if person.entity_id in pending.deaths or getattr(person, "is_sick", False):
                continue

            viral_load = ep_map.get_viral_load(person.x, person.y)

            # Solo hay riesgo si la carga viral supera el umbral
            if viral_load > viral_load_threshold:
                # El riesgo escala proporcionalmente con la carga viral local acumulada
                daily_risk = viral_load * daily_transmission_rate

                # Integración temporal del riesgo (probabilidad exponencial acumulada)
                total_risk = 1.0 - math.exp(-daily_risk * delta_days)

                if random.random() < total_risk:
                    # Crear un patógeno ambiental con propiedades realistas
                    # Usar valores de configuración centralizada
                    env_pathogen = Pathogen(
                        family="Environmental",
                        variant_id=1,
                        virulence=dis_cfg.base_virulence,
                        transmission=dis_cfg.base_transmission,
                        lethality=dis_cfg.base_lethality,
                        asymptomatic_chance=0.3,  # 30% de probabilidad de ser asintomático
                        incubation_days=5.0,  # 5 días de incubación
                    )

                    # Registrar la infección en el búfer transaccional
                    pending.register_infection(person.entity_id, env_pathogen)
                    self.logger.debug(
                        "🦠 Agente %s contagiado por rastro ambiental (carga viral: %.2f)",
                        person.entity_id,
                        viral_load,
                    )

        # =====================================================================
        # 3. DECAIMIENTO: El virus se disipa o muere en el ambiente
        # =====================================================================
        # Aplicar el factor de decaimiento ajustado por los días transcurridos
        decay_factor = env_cfg.viral_decay_factor
        decay = decay_factor ** delta_days
        ep_map.decay_viral_load(factor=decay)