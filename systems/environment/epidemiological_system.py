"""Módulo responsable de la interacción entre los agentes y los patógenos del entorno.

Gestiona la retroalimentación de enfermedades: los agentes infectados exhalan 
y contaminan el entorno (fómites), y las celdas altamente contaminadas 
infectan a los agentes sanos instanciando nuevas cepas ambientales.
"""

from __future__ import annotations

import logging
import math
import random

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.diseases.pathogen import Pathogen
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

        # 1. PROPAGACIÓN: Los agentes enfermos contaminan el entorno
        for person in all_persons:
            if person.entity_id in pending.deaths:
                continue

            if getattr(person, "is_sick", False):
                # La cantidad exhalada es proporcional al tiempo transcurrido en el tick
                ep_map.add_viral_load(person.x, person.y, amount=(0.5 * delta_days))

        # 2. CONTAGIO: El entorno infecta a los agentes sanos
        # Tasa diaria base de infección ambiental (Fallback a 0.1 si no está definida)
        base_transmission_rate = getattr(dis_cfg, "environmental_transmission_rate", 0.1)
        daily_transmission_rate = base_transmission_rate / 30.0

        for person in all_persons:
            if person.entity_id in pending.deaths or getattr(person, "is_sick", False):
                continue

            viral_load = ep_map.get_viral_load(person.x, person.y)

            if viral_load > 0.1:
                # El riesgo escala proporcionalmente con la carga viral local acumulada
                daily_risk = viral_load * daily_transmission_rate

                # Integración temporal del riesgo (probabilidad exponencial acumulada)
                total_risk = 1.0 - math.exp(-daily_risk * delta_days)

                if random.random() < total_risk:
                    # Instanciamos una cepa ambiental base. Al recoger el virus 
                    # de un fómite, adquiere una firma genérica del entorno.
                    env_pathogen = Pathogen(
                        family="Environmental",
                        variant_id=1,
                        virulence=getattr(dis_cfg, "base_virulence", 0.5),
                        transmission=getattr(dis_cfg, "base_transmission", 0.5),
                        lethality=getattr(dis_cfg, "base_lethality", 0.1),
                    )

                    # El registro ahora cumple con la firma exacta del PendingChanges
                    pending.register_infection(person.entity_id, env_pathogen)
                    self.logger.debug(
                        "Agente %s contagiado por rastro ambiental.",
                        person.entity_id,
                    )

        # 3. DECAIMIENTO: El virus se disipa o muere en el ambiente por radiación/tiempo
        # Aplicamos el factor de decaimiento ajustado por los días transcurridos
        decay_factor = getattr(env_cfg, "viral_decay_factor", 0.9)
        decay = decay_factor ** delta_days
        ep_map.decay_viral_load(factor=decay)