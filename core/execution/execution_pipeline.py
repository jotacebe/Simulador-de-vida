"""Pipeline único de ejecución de ticks.

El pipeline ejecuta todas las fases de un tick y devuelve los cambios
pendientes. No aplica el commit; esa responsabilidad pertenece a
``WorldState`` y se invoca desde ``SimulationEngine``.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from core.config.simulation_config import SimulationConfig
from core.execution.execution_context import ExecutionContext
from core.execution.phase_executor import PhaseDefinition, PhaseExecutor
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext


class ExecutionPipeline:
    """Ejecuta todas las fases configuradas para un tick."""

    def __init__(
        self,
        config: SimulationConfig,
        phases: Iterable[PhaseDefinition],
        phase_executor: PhaseExecutor | None = None,
    ) -> None:
        """Inicializa el pipeline.

        Args:
            config: Configuración compartida de la simulación.
            phases: Fases ordenadas que se ejecutarán en cada tick.
            phase_executor: Ejecutor opcional para cada fase.

        Raises:
            ValueError: Si no se proporciona ninguna fase.
        """

        self.config = config
        self.phases = list(phases)
        self.phase_executor = phase_executor or PhaseExecutor()
        self.logger = logging.getLogger(self.__class__.__name__)

        if not self.phases:
            raise ValueError("ExecutionPipeline necesita al menos una fase.")

    def execute_tick(
        self,
        state: WorldState,
        delta_days: float,
        current_tick: int,
        current_day: float,
        event_bus: Any = None,
    ) -> PendingChanges:
        """Ejecuta un tick completo de simulación.

        Args:
            state: Estado actual del mundo.
            delta_days: Duración del tick en días simulados.
            current_tick: Número de tick actual.
            current_day: Día simulado actual.
            event_bus: Bus de eventos opcional.

        Returns:
            Cambios pendientes acumulados durante el tick.
        """

        pending = PendingChanges()
        environment = EnvironmentContext(state=state)

        context = ExecutionContext(
            state=state,
            pending=pending,
            environment=environment,
            config=self.config,
            delta_days=delta_days,
            current_tick=current_tick,
            current_day=current_day,
            event_bus=event_bus,
        )

        for phase in self.phases:
            self.phase_executor.execute(phase, context)

        return pending