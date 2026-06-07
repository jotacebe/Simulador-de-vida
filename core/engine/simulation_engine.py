# Ruta: core/engine/simulation_engine.py

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
# Importamos el contexto para centralizar su ciclo de vida
from systems.environment.environment_context import EnvironmentContext 

class SimulationEngine:
    def __init__(self, world_state: WorldState, systems: list):
        self.state = world_state
        self.systems = systems 
        self.current_tick = 0

    def step(self) -> None:
        """Avanza la simulación un paso (tick) optimizando recursos."""
        self.current_tick += 1
        
        cfg = getattr(self.state, 'config', None)
        delta_days = getattr(cfg, 'tick_duration_days', 30) if cfg else 30
        
        # 1. OPTIMIZACIÓN CRÍTICA: Instanciar el contexto una sola vez por tick
        context = EnvironmentContext(self.state)
        
        # 2. Búfer transaccional limpio
        pending = PendingChanges()

        # 3. FASE DE LECTURA (Compartiendo el contexto precargado)
        for system in self.systems:
            # Pasamos 'context' como cuarto parámetro para evitar recreaciones costosas
            system.process(self.state, pending, delta_days, context)

        # 4. FASE DE COMMIT
        self.state.apply_commit(pending)