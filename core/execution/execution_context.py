"""Contexto de ejecución para un tick de simulación.

El contexto agrupa los objetos que necesitan los ejecutores durante un tick.
Su uso evita pasar muchos argumentos sueltos entre pipeline, fases y sistemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Datos compartidos durante la ejecución de un tick.

    Attributes:
        state: Estado autoritativo del mundo.
        pending: Búfer transaccional de cambios pendientes.
        environment: Contexto ambiental y espacial del tick.
        config: Configuración compartida de la simulación.
        delta_days: Duración del tick en días simulados.
        current_tick: Número de tick actual, empezando en 1.
        current_day: Día simulado actual.
        event_bus: Bus de eventos opcional.
    """

    state: WorldState
    pending: PendingChanges
    environment: EnvironmentContext
    config: SimulationConfig
    delta_days: float
    current_tick: int
    current_day: float
    event_bus: Any = None