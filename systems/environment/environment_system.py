"""Módulo responsable de evaluar y calcular el estrés ambiental por hacinamiento."""

from systems.environment.environment_context import EnvironmentContext
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from core.config.simulation_config import SimulationConfig

class EnvironmentSystem:
    """Calcula la presión espacial de los sectores y actualiza el contexto del ecosistema."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración central."""
        self.config = config

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Evalúa la densidad de población y genera el mapa de presión ambiental.
        
        No muta el estado de los agentes directamente. Su función es informar 
        al EnvironmentContext para que sistemas como Mortality o CognitiveMemory 
        puedan leer la presión local y reaccionar en consecuencia.
        """
        env_cfg = self.config.environment
        
        # Limpiamos el mapa de presión del tick anterior
        context.pressure_map.clear()

        # Iteramos sobre los clústeres espaciales ya precalculados en el contexto
        for sector_coords, agents_in_sector in context.sector_map.items():
            current_sector_pop = len(agents_in_sector)
            
            # Si la población está por debajo del límite, la presión es 1.0 (Normal)
            if current_sector_pop <= env_cfg.max_agents_per_sector:
                pressure = 1.0
            else:
                # Si hay hacinamiento, la presión aumenta proporcionalmente
                excess_ratio = (current_sector_pop - env_cfg.max_agents_per_sector) / env_cfg.max_agents_per_sector
                pressure = 1.0 + excess_ratio

            # Aplicamos esta presión calculada a las coordenadas exactas de cada agente del sector
            for person in agents_in_sector:
                context.pressure_map[(person.x, person.y)] = pressure