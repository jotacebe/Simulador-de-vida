"""Punto de entrada principal del simulador evolutivo.

Ruta: launcher.py

Responsabilidad: Inyectar dependencias, cargar archivos de configuración externos,
instanciar todos los sistemas biológicos/sociales, crear la población fundadora
y transferir el control al SimulationEngine.
"""

import logging
import random
import json
import os
from typing import Optional

# Arquitectura Base
from core.state.world_state import WorldState
from core.config.simulation_config import SimulationConfig
from core.engine.simulation_engine import SimulationEngine
from entities.person.person import Person
from entities.person.genome import Genome

# Sistemas e Inyecciones
from systems.adoptions.adoption_system import AdoptionSystem
from systems.aging.aging_system import AgingSystem
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
from systems.diseases.disease_system import DiseaseSystem
from systems.environment.density_system import DensitySystem
from systems.environment.environment_system import EnvironmentSystem
from systems.environment.epidemiological_system import EpidemiologicalSystem
from systems.evolution.evolution_engine import EvolutionEngine
from systems.free_will.free_will_system import FreeWillSystem
from systems.genealogy.genealogy_system import GenealogySystem
from systems.genealogy.ancestry_queries import AncestryQueries
from systems.metrics.metrics_system import MetricsSystem
from systems.mortality.mortality_system import MortalitySystem
from systems.mortality.death_resolver import DeathResolver
from systems.movement.movement_system import MovementSystem
from systems.movement.movement_resolver import MovementResolver
from systems.relationships.relationship_system import RelationshipSystem
from systems.relationships.marriage_system import MarriageSystem
from systems.reproduction.conception_system import ConceptionSystem
from systems.reproduction.gestation_system import GestationSystem
from systems.reproduction.birth_system import BirthSystem
from systems.temporal.temporal_system import TemporalSystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class SimulationLauncher:
    """Clase ensambladora encargada de la inyección de dependencias y arranque."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.logger = logging.getLogger("SimulationLauncher")
        self.config = SimulationConfig()
        
        if config_path:
            self._load_external_config(config_path)

    def _load_external_config(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            self.logger.warning(f"No se encontró el archivo {filepath}.")
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for category, params in data.items():
                for key, val in params.items():
                    self.config.set_parameter(category, key, val)
        except Exception as e:
            self.logger.error(f"Error procesando la configuración externa: {e}")

    def _assemble_systems(self, state: WorldState) -> list:
        """Instancia y ordena topológicamente todos los sistemas del motor."""
        self.logger.info("Ensamblando y ordenando sistemas...")
        
        genealogy_sys = GenealogySystem(self.config)
        ancestry_queries_obj = AncestryQueries(genealogy_system=genealogy_sys)
        
        evo_engine = EvolutionEngine(self.config, ancestry_queries=ancestry_queries_obj)
        density_sys = DensitySystem(self.config)
        relationship_sys = RelationshipSystem(self.config)
        
        systems_pipeline = [
            TemporalSystem(self.config),
            AgingSystem(self.config),
            EnvironmentSystem(self.config),
            density_sys,
            EpidemiologicalSystem(self.config),
            CognitiveMemorySystem(self.config),
            FreeWillSystem(self.config),
            
            MovementSystem(
                config=self.config, 
                density_system=density_sys, 
                relationship_system=relationship_sys
            ),
            MovementResolver(self.config),
            
            relationship_sys,
            MarriageSystem(config=self.config, ancestry_queries=ancestry_queries_obj), 
            AdoptionSystem(self.config),
            
            DiseaseSystem(self.config),
            ConceptionSystem(self.config),
            GestationSystem(self.config, evolution_engine=evo_engine),
            BirthSystem(self.config),
            
            MortalitySystem(self.config),
            DeathResolver(self.config),
            
            genealogy_sys,
            MetricsSystem(self.config),
            evo_engine
        ]
        
        return systems_pipeline

    def _generate_founding_population(self, state: WorldState, size: int = 50) -> None:
        """Crea la población inicial 'Generación 0'."""
        self.logger.info(f"🧬 Generando {size} individuos fundadores de la Generación 0...")
        for i in range(1, size + 1):
            gen = Genome()
            gen.fertility = random.uniform(0.5, 0.9)
            gen.sociability = random.uniform(0.1, 0.9)
            gen.temperament = random.uniform(0.1, 0.9)
            gen.immunity = random.uniform(0.4, 0.8)
            
            # ¡AQUÍ ESTÁ EL CAMBIO! Inyectamos config=self.config para que la entidad 
            # pueda leer sus umbrales biológicos dinámicamente.
            p = Person(
                config=self.config,
                entity_id=i, 
                x=random.randint(10, 90), 
                y=random.randint(10, 90),
                age=random.uniform(6500.0, 11000.0), 
                genome=gen
            )
            
            p.set_health_state("sano")
            p.update_pregnancy(False, 0.0)
            
            partner = i + 1 if i % 2 != 0 else i - 1
            p.register_marriage(partner)
            
            state.add_person(p)

    def run(self) -> None:
        """Prepara el entorno, el estado inicial e inicia el bucle del motor."""
        state = WorldState(config=self.config, width=100, height=100)
        self._generate_founding_population(state, size=50)
        
        systems_list = self._assemble_systems(state)
        
        # El motor ahora toma el control absoluto de la simulación temporal
        engine = SimulationEngine(
            world_state=state, 
            systems=systems_list, 
            config=self.config, 
            event_bus=None
        )
        
        # Llamada limpia, sin "números mágicos" de tiempo
        engine.run()


if __name__ == "__main__":
    launcher = SimulationLauncher()
    launcher.run()