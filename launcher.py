"""
Ruta: launcher.py
"""
import random
import logging

# Núcleo y Estado
from core.state.world_state import WorldState
from core.engine.tick_manager import TickManager
from core.execution.execution_pipeline import ExecutionPipeline
from core.config.simulation_config import SimulationConfig
from events.event_bus import EventBus

# Sistemas
from systems.environment.density_system import DensitySystem
from systems.environment.environment_system import EnvironmentSystem
from systems.movement.movement_system import MovementSystem
from systems.diseases.disease_system import DiseaseSystem
from systems.mortality.mortality_system import MortalitySystem
from systems.reproduction.conception_system import ConceptionSystem
from systems.reproduction.gestation_system import GestationSystem
from systems.relationships.relationship_system import RelationshipSystem
from systems.adoptions.adoption_system import AdoptionSystem
from systems.metrics.metrics_system import MetricsSystem 
from systems.aging.aging_system import AgingSystem
from systems.genealogy.genealogy_system import GenealogySystem
from systems.genealogy.ancestry_queries import AncestryQueries
from systems.free_will.free_will_system import FreeWillSystem

from entities.person.person import Person

def inicializar_poblacion_test(state: WorldState, count: int, map_w: int, map_h: int) -> None:
    for i in range(1, count + 1):
        # Usamos valores iniciales seguros
        pos_x = random.randint(0, map_w - 1)
        pos_y = random.randint(0, map_h - 1)
        
        # CORRECCIÓN VITAL: La edad ahora se rige por la fuente única de verdad (días).
        # Multiplicamos por 365.0 para que se generen adultos funcionales y fértiles.
        edad_en_dias = float(random.randint(16, 40) * 365.0)
        
        individuo = Person(entity_id=i, age=edad_en_dias, x=pos_x, y=pos_y)
        state.add_person(individuo)

def bootstrap_engine():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("Launcher")
    
    # 1. FUENTE DE VERDAD: Configuración única
    config = SimulationConfig()
    
    ancho_mapa, alto_mapa = 40, 40
    poblacion_inicial = 50

    event_bus = EventBus()
    world_state = WorldState(config=config, width=ancho_mapa, height=alto_mapa)
    tick_manager = TickManager()

    # 2. SERVICIOS Y DEPENDENCIAS
    # Primero servicios que otros sistemas pueden necesitar
    genealogy_system = GenealogySystem(config)
    world_state.genealogy_system = genealogy_system
    ancestry_service = AncestryQueries(genealogy_system)

    # 3. INICIALIZACIÓN DE SISTEMAS (Patrón: config primero, dependencias después)
    # Sistemas simples
    density_system = DensitySystem(config)
    environment_system = EnvironmentSystem(config)
    disease_system = DiseaseSystem(config)
    mortality_system = MortalitySystem(config)
    
    # CORRECCIÓN: Instanciamos los dos sistemas de reproducción separados
    conception_system = ConceptionSystem(config)
    gestation_system = GestationSystem(config)
    
    adoption_system = AdoptionSystem(config)
    aging_system = AgingSystem(config)
    metrics_system = MetricsSystem(config)
    free_will_system = FreeWillSystem(config)

    # Sistemas con dependencias
    relationship_system = RelationshipSystem(config, ancestry_queries=ancestry_service)
    movement_system = MovementSystem(config, density_system=density_system, relationship_system=relationship_system)

    # 4. PIPELINE DE EJECUCIÓN
    pipeline_sistemas = [
        genealogy_system, 
        aging_system, 
        density_system, 
        environment_system, 
        movement_system,
        disease_system, 
        mortality_system, 
        conception_system,
        gestation_system,
        relationship_system, 
        adoption_system, 
        metrics_system,
        free_will_system
    ]

    execution_pipeline = ExecutionPipeline(systems=pipeline_sistemas, event_bus=event_bus)
    
    # Inicialización del estado
    inicializar_poblacion_test(world_state, poblacion_inicial, ancho_mapa, alto_mapa)

    logger.info("Motor inicializado. Arrancando simulación...")
    
    try:
        while tick_manager.current_tick < 200:
            delta_days = tick_manager.advance_tick()
            execution_pipeline.execute_tick(world_state, tick_manager.current_tick, delta_days)
            
            # Control de extinción
            if len(world_state.get_all_persons()) == 0:
                logger.warning(f"Extinción total en tick {tick_manager.current_tick}. Abortando.")
                break
            
            # Logs periódicos
            if tick_manager.current_tick % 10 == 0:
                stats = metrics_system.get_latest_metrics()
                logger.info(f"[Tick {tick_manager.current_tick:03d}] Población: {stats.get('population', 0)}")

    except Exception as e:
        logger.critical(f"Fallo catastrófico: {e}", exc_info=True)
    finally:
        metrics_system.export_to_json("simulation_metrics.json")
        execution_pipeline.export_simulation_data("data_historica.json")

if __name__ == "__main__":
    bootstrap_engine()