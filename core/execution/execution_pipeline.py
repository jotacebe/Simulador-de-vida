"""
Ruta: core/execution/execution_pipeline.py
Responsabilidad: Orquestar el bucle de simulación con integridad transaccional estricta.
"""
import logging
import json
from typing import List, Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

# Importamos los jueces (Resolvers) de la Fase de Arbitraje
from systems.movement.movement_resolver import MovementResolver
from systems.mortality.death_resolver import DeathResolver
from systems.environment.environment_context import EnvironmentContext

logger = logging.getLogger("ExecutionPipeline")

class ExecutionPipeline:
    def __init__(self, systems: List[Any], event_bus: Any = None):
        self.systems = systems
        self.event_bus = event_bus
        self.metrics_system = next((s for s in systems if s.__class__.__name__ == "MetricsSystem"), None)
        self.pending = PendingChanges()

        # Filtramos para no ejecutar las métricas doblemente si están en la lista
        self.systems = [s for s in self.systems if s.__class__.__name__ != "MetricsSystem"]
    
    def export_simulation_data(self, filename: str):
        """Exporta los datos actuales del pipeline o de los sistemas."""
        logger.info(f"--- Exportando datos de simulación a {filename} ---")
        
        data_to_export = {
            "pipeline_state": "finalized",
            "active_systems": [s.__class__.__name__ for s in self.systems]
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data_to_export, f, indent=4)
            logger.info("Exportación completada con éxito.")
        except Exception as e:
            logger.error(f"Error al exportar datos: {e}")

    # UNIFICACIÓN TEMPORAL: delta_days ahora es float para soportar escalas continuas
    def execute_tick(self, state: WorldState, current_tick: int, delta_days: float) -> None:
        """Orquesta un ciclo completo de simulación previniendo asimetrías y zombis."""
        try:
            # 1. OPTIMIZACIÓN: El contexto se crea UNA SOLA VEZ
            context = EnvironmentContext(state)

            # 2. FASE DE EVALUACIÓN (Proposición)
            # Todos los sistemas proponen acciones y las guardan en el buffer (self.pending)
            for system in self.systems:
                system.process(state, self.pending, delta_days, context)

            # 3. FASE DE ARBITRAJE (Validación y Filtrado)
            # ¡ELIMINACIÓN DE ZOMBIS!
            # El DeathResolver analiza quién ha muerto y borra cualquier otra propuesta 
            # (movimientos, matrimonios, concepciones) hecha por esos agentes en este tick.
            DeathResolver.resolve(self.pending, state)
            
            # Una vez purgados los muertos, resolvemos colisiones físicas de los vivos
            MovementResolver.resolve(self.pending, state)

            # 4. COMMIT TRANSACCIONAL (Aplicación)
            # Solo la información limpia y verificada altera el mundo real
            state.apply_commit(self.pending, self.event_bus, current_tick)

            # 5. MÉTRICAS
            if self.metrics_system:
                self.metrics_system.process(state, self.pending, delta_days, context)

        except Exception as e:
            logger.critical(f"Falla catastrófica en el ciclo de simulación: {str(e)}", exc_info=True)
            raise e
        finally:
            self.pending.clear()