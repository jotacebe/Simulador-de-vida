"""Motor temporal principal de la simulación.

``SimulationEngine`` contiene el bucle principal. El motor avanza ticks,
solicita al pipeline que ejecute las fases activas y consolida los cambios en
``WorldState``. Además, proporciona observabilidad visual y exportación de datos.
"""

from __future__ import annotations

import csv
import json
import logging
import math
import os
import random
from datetime import datetime
from typing import Any, Optional

from core.config.simulation_config import SimulationConfig
from core.engine.phase_scheduler import PhaseScheduler
from core.execution.execution_pipeline import ExecutionPipeline
from core.state.world_state import WorldState
from entities.person.allele import Allele, Gene
from entities.person.genome import Genome
from entities.person.person import Person


class SimulationEngine:
    """Controla el ciclo temporal completo y el registro analítico de la simulación."""

    def __init__(
        self,
        world_state: WorldState,
        config: SimulationConfig,
        pipeline: ExecutionPipeline,
        event_bus: Any = None,
    ) -> None:
        """Inicializa el motor y sus contadores históricos.

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
        
        # Contadores analíticos del motor
        self._total_deaths: int = 0
        self._total_births: int = 0
        self._total_infections: int = 0

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
            config_path: Archivo JSON opcional con sobrescrituras de configuración.
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
        """Ejecuta la simulación completa, documenta eventos y exporta resultados.

        Raises:
            ValueError: Si ``engine.delta_days`` no es mayor que cero.
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

        history: list[dict[str, Any]] = []

        for tick in range(1, total_ticks + 1):
            current_day = min(tick * delta_days, total_days)

            self.logger.debug(
                "Ejecutando tick %s/%s en el día %.2f.",
                tick,
                total_ticks,
                current_day,
            )

            # Fase 1: Cálculo del estado transaccional
            pending = self.pipeline.execute_tick(
                state=self.state,
                delta_days=delta_days,
                current_tick=tick,
                current_day=current_day,
                event_bus=self.event_bus,
            )
            
            # Fase 2: Observabilidad (Log visual y contadores)
            self._log_visual_events(pending, tick)
            self._total_deaths += len(pending.deaths)
            self._total_births += len(pending.births)
            self._total_infections += len(pending.infections)

            # Fase 3: Consolidación atómica
            self.state.apply_commit(
                pending,
                event_bus=self.event_bus,
                current_tick=tick,
            )

            if hasattr(self.state, "world_days_elapsed"):
                self.state.world_days_elapsed = current_day
                
            # Fase 4: Recolección de métricas para el CSV
            persons = self.state.get_all_persons()
            history.append({
                "tick": tick,
                "day": round(current_day, 2),
                "alive": len(persons),
                "sick": sum(1 for p in persons if getattr(p, "is_sick", False)),
                "cumulative_deaths": self._total_deaths,
                "cumulative_births": self._total_births
            })

        self._print_simulation_summary(total_ticks)
        self._export_to_csv(history)
        self.logger.info("Simulación finalizada correctamente.")

    def _log_visual_events(self, pending: Any, tick: int) -> None:
        """Escanea el búfer y emite logs visuales para los eventos críticos.

        Args:
            pending: Búfer transaccional `PendingChanges` de este tick.
            tick: Número del tick actual.
        """
        for data in pending.births:
            mother_id = data.get("mother_id", "Desconocida")
            self.logger.info("👶 [NACIMIENTO] Madre %s dio a luz (Tick: %s).", mother_id, tick)
            
        for entity_id, reason in pending.deaths.items():
            self.logger.info("⚰️ [MUERTE]     Agente %s falleció. Causa: %s", entity_id, reason)
            
        for entity_id, pathogen in pending.infections:
            pathogen_id = getattr(pathogen, "pathogen_id", "Desconocido")
            self.logger.info("🤒 [CONTAGIO]   Agente %s contrajo %s", entity_id, pathogen_id)

    def _print_simulation_summary(self, total_ticks: int) -> None:
        """Genera un reporte analítico final con formato de tabla.

        Args:
            total_ticks: Número total de ticks ejecutados.
        """
        persons = self.state.get_all_persons()
        total_alive = len(persons)
        
        sick_count = sum(1 for p in persons if getattr(p, "is_sick", False))
        avg_age_years = (sum(p.age for p in persons) / total_alive / 365.0) if total_alive > 0 else 0.0

        self.logger.info("\n" + "=" * 65)
        self.logger.info("📊 RESUMEN EJECUTIVO DE LA SIMULACIÓN")
        self.logger.info("=" * 65)
        self.logger.info(f"{'Métrica':<30} | {'Valor':<10}")
        self.logger.info("-" * 45)
        self.logger.info(f"{'Población Viva Final':<30} | {total_alive:<10}")
        self.logger.info(f"{'Edad Media (Años)':<30} | {avg_age_years:<10.1f}")
        self.logger.info(f"{'Total de Nacimientos Históricos':<30} | {self._total_births:<10}")
        self.logger.info(f"{'Total de Muertes Históricas':<30} | {self._total_deaths:<10}")
        self.logger.info(f"{'Infectados Activos (Fin)':<30} | {sick_count:<10}")
        self.logger.info(f"{'Total Contagios Históricos':<30} | {self._total_infections:<10}")
        self.logger.info("=" * 65 + "\n")

    def _export_to_csv(self, history: list[dict[str, Any]]) -> None:
        """Exporta el historial de la simulación a un archivo CSV.

        Args:
            history: Lista de diccionarios con las métricas por tick.
        """
        if not history:
            return
            
        filename = f"reporte_simulacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        keys = history[0].keys()
        
        try:
            with open(filename, "w", newline="", encoding="utf-8") as output_file:
                dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(history)
            self.logger.info("💾 Reporte de datos exportado a: %s", filename)
        except OSError as e:
            self.logger.error("Error al exportar el CSV: %s", e)

    @staticmethod
    def _load_external_config(
        config: SimulationConfig,
        filepath: str,
    ) -> None:
        """Carga sobrescrituras de configuración desde un JSON externo.

        Args:
            config: Configuración que recibirá los cambios.
            filepath: Ruta al archivo JSON.
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
            base_fertility = random.uniform(0.5, 0.9)
            base_sociability = random.uniform(0.1, 0.9)
            base_temperament = random.uniform(0.1, 0.9)
            base_immunity = random.uniform(0.4, 0.8)

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
            gene_immunity = Gene(
                allele_a=Allele.create_random(base_immunity, 0.1),
                allele_b=Allele.create_random(base_immunity, 0.1)
            )

            genome = Genome(
                fertility=gene_fertility,
                sociability=gene_sociability,
                temperament=gene_temperament,
                immunity=gene_immunity,
                species_baseline="human"
            )

            person = Person(
                config=config,
                entity_id=entity_id,
                x=random.randint(10, 90),
                y=random.randint(10, 90),
                age=random.uniform(6500.0, 11000.0),
                genome=genome,
            )

            person.set_health_state("sano")
            person.update_pregnancy(False, 0.0)

            partner_id = entity_id + 1 if entity_id % 2 else entity_id - 1
            person.register_marriage(partner_id)

            state.add_person(person)