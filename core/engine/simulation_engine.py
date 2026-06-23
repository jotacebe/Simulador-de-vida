"""Motor temporal principal de la simulación.

``SimulationEngine`` contiene el bucle principal. El motor avanza ticks,
solicita al pipeline que ejecute las fases activas y consolida los cambios en
``WorldState``.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
from typing import Any, Optional

from core.config.simulation_config import SimulationConfig
from core.engine.phase_scheduler import PhaseScheduler
from core.execution.execution_pipeline import ExecutionPipeline
from core.state.world_state import WorldState
from entities.person.allele import Allele, Gene
from entities.person.genome import Genome
from entities.person.person import Person


class SimulationEngine:
    """Controla el ciclo temporal completo de la simulación."""

    def __init__(
        self,
        world_state: WorldState,
        config: SimulationConfig,
        pipeline: ExecutionPipeline,
        event_bus: Any = None,
    ) -> None:
        """Inicializa el motor.

        Args:
            world_state: Estado autoritativo del mundo.
            config: Configuración compartida de la simulación.
            pipeline: Pipeline responsable de ejecutar los sistemas por tick.
            event_bus: Bus de eventos opcional para publicar cambios.
        """
        self.state = world_state
        self.config = config
        self.pipeline = pipeline
        self.event_bus = event_bus
        self.logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    def create_default(
        cls,
        config_path: Optional[str] = None,
        width: int = 100,
        height: int = 100,
        founding_population_size: int = 50,
        event_bus: Any = None,
    ) -> SimulationEngine:
        """Crea un motor completo usando la configuración por defecto.

        Args:
            config_path: Archivo JSON opcional con sobrescrituras de
                configuración.
            width: Anchura del mundo.
            height: Altura del mundo.
            founding_population_size: Número de agentes fundadores.
            event_bus: Bus de eventos opcional.

        Returns:
            Instancia de ``SimulationEngine`` lista para ejecutarse.
        """
        config = SimulationConfig()

        if config_path:
            cls._load_external_config(config, config_path)

        state = WorldState(config=config, width=width, height=height)
        cls._generate_founding_population(
            config=config,
            state=state,
            size=founding_population_size,
        )

        scheduler = PhaseScheduler(config)
        pipeline = ExecutionPipeline(
            config=config,
            phases=scheduler.build_phases(),
        )

        return cls(
            world_state=state,
            config=config,
            pipeline=pipeline,
            event_bus=event_bus,
        )

    def run(self) -> None:
        """Ejecuta la simulación hasta alcanzar la duración configurada.

        Raises:
            ValueError: Si ``engine.delta_days`` no es mayor que cero.
            Exception: Propaga fallos del pipeline o del commit para evitar
                confirmar ticks corruptos.
        """
        total_days = float(self.config.engine.total_days)
        delta_days = float(self.config.engine.delta_days)

        if delta_days <= 0:
            raise ValueError("engine.delta_days debe ser mayor que cero.")

        total_ticks = math.ceil(total_days / delta_days)

        self.logger.info(
            "Iniciando simulación: %s días, %s días/tick, %s ticks.",
            total_days,
            delta_days,
            total_ticks,
        )

        for tick in range(1, total_ticks + 1):
            current_day = min(tick * delta_days, total_days)

            self.logger.debug(
                "Ejecutando tick %s/%s en el día %.2f.",
                tick,
                total_ticks,
                current_day,
            )

            pending = self.pipeline.execute_tick(
                state=self.state,
                delta_days=delta_days,
                current_tick=tick,
                current_day=current_day,
                event_bus=self.event_bus,
            )

            self.state.apply_commit(
                pending,
                event_bus=self.event_bus,
                current_tick=tick,
            )

            if hasattr(self.state, "world_days_elapsed"):
                self.state.world_days_elapsed = current_day

        self.logger.info("Simulación finalizada correctamente.")

    @staticmethod
    def _load_external_config(
        config: SimulationConfig,
        filepath: str,
    ) -> None:
        """Carga sobrescrituras de configuración desde un JSON externo.

        Args:
            config: Configuración que recibirá los cambios.
            filepath: Ruta al archivo JSON.

        Raises:
            json.JSONDecodeError: Si el archivo no contiene JSON válido.
            OSError: Si el archivo no se puede leer.
        """
        logger = logging.getLogger("SimulationEngine")

        if not os.path.exists(filepath):
            logger.warning("Archivo de configuración no encontrado: %s.", filepath)
            return

        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        for category, params in data.items():
            if not isinstance(params, dict):
                logger.warning(
                    "Se ignora una sección de configuración inválida: %s.",
                    category,
                )
                continue

            for key, value in params.items():
                config.set_parameter(category, key, value)

    @staticmethod
    def _generate_founding_population(
        config: SimulationConfig,
        state: WorldState,
        size: int,
    ) -> None:
        """Crea la población inicial de la simulación de forma determinista.

        Args:
            config: Configuración compartida de la simulación.
            state: Estado del mundo donde se insertarán los agentes.
            size: Número de agentes fundadores.
        """
        logger = logging.getLogger("SimulationEngine")
        logger.info("Generando %s agentes fundadores.", size)

        for entity_id in range(1, size + 1):
            # 1. Generamos los valores fenotípicos base para el fundador
            base_fertility = random.uniform(0.5, 0.9)
            base_sociability = random.uniform(0.1, 0.9)
            base_temperament = random.uniform(0.1, 0.9)
            base_immunity = random.uniform(0.4, 0.8)

            # 2. Construimos los genes diploides (con 2 alelos cada uno)
            gene_fertility = Gene(
                allele_a=Allele.create_random(base_fertility, 0.1),
                allele_b=Allele.create_random(base_fertility, 0.1)
            )
            gene_sociability = Gene(
                allele_a=Allele.create_random(base_sociability, 0.1),
                allele_b=Allele.create_random(base_sociability, 0.1)
            )
            gene_temperament = Gene(
                allele_a=Allele.create_random(base_temperament, 0.1),
                allele_b=Allele.create_random(base_temperament, 0.1)
            )