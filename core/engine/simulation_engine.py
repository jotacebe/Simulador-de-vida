"""Motor central de la simulación.

Ruta: core/engine/simulation_engine.py

Responsabilidad: Controlar el bucle principal de tiempo, instanciar el contexto
transaccional en cada iteración (tick), ejecutar secuencialmente todos los
sistemas inyectados y delegar la consolidación atómica en el WorldState.
"""

import logging
import math
from typing import List, Any, Optional

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig


class SimulationEngine:
    """Ejecuta el pipeline de sistemas biológicos y sociales sobre el estado del mundo."""

    def __init__(self, world_state: WorldState, systems: List[Any], config: SimulationConfig, event_bus: Optional[Any] = None) -> None:
        """Inicializa el motor con el estado centralizado y la lista de sistemas.

        Args:
            world_state (WorldState): Fuente de verdad de las entidades de la simulación.
            systems (List[Any]): Lista de sistemas ordenados topológicamente.
            config (SimulationConfig): Configuración centralizada de la simulación.
            event_bus (Optional[Any]): Bus de eventos para la notificación de cambios.
        """
        self.state = world_state
        self.systems = systems
        self.config = config
        self.event_bus = event_bus
        self.logger = logging.getLogger("SimulationEngine")

    def run(self) -> None:
        """Ejecuta el bucle principal de la simulación (fase transaccional por tick)."""
        total_days = self.config.engine.total_days
        delta_days = self.config.engine.delta_days

        self.logger.info(f"🚀 Iniciando bucle de simulación: {total_days} días ({delta_days} días/tick).")
        
        current_day = 0.0
        total_ticks = math.ceil(total_days / delta_days)
        
        for tick in range(1, total_ticks + 1):
            current_day += delta_days
            self.logger.debug(f"--- Tick {tick}/{total_ticks} | Día {current_day:.2f} ---")
            
            # 1. Instanciación del buffer limpio y el contexto espacial real
            pending = PendingChanges()
            context = EnvironmentContext(state=self.state)
            
            # 2. Pipeline transaccional: Los sistemas acumulan intenciones de cambio
            for system in self.systems:
                try:
                    system.process(self.state, pending, delta_days, context)
                except Exception as e:
                    self.logger.error(
                        f"Fallo crítico en {system.__class__.__name__} durante el tick {tick}: {e}"
                    )
                    raise  # Fail-fast para evitar la corrupción del estado global

            # 3. Fase de Consolidación Atómica utilizando la API nativa de WorldState
            self.state.apply_commit(pending, event_bus=self.event_bus, current_tick=tick)
            
        self.logger.info("🏁 Simulación finalizada con éxito.")