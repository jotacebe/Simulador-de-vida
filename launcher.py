"""
Ruta: launcher.py
Responsabilidad: Punto de entrada principal del simulador. Orquesta todos los 
                 sistemas biológicos (concepción, gestación, mortalidad), espaciales
                 y conductuales en un ecosistema de tiempo continuo.
"""
import logging
import random
from typing import Any

# Importaciones de tu arquitectura de estados
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from entities.person.person import Person
from entities.person.genome import Genome

# Importaciones de Sistemas
from systems.environment.environment_context import EnvironmentContext
from systems.evolution.evolution_engine import EvolutionEngine
from systems.movement.movement_system import MovementSystem
from systems.movement.movement_resolver import MovementResolver
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
from systems.mortality.mortality_system import MortalitySystem
from systems.reproduction.conception_system import ConceptionSystem
from systems.reproduction.gestation_system import GestationSystem

# Configuración de logging para observar el ecosistema
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class MockRelationshipSystem:
    """Mock temporal para el anclaje social del sistema de movimiento."""
    def get_social_anchor(self, person: Any, state: Any) -> Any:
        return None

class SimulationLauncher:
    """Motor de orquestación principal de la simulación evolutiva."""

    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("SimulationLauncher")
        
        # 1. OBJETO DE CONFIGURACIÓN
        class Config:
            class evolution:
                snapshot_interval_days: float = 30.0  # Reportes evolutivos mensuales
            class movement:
                movement_speed: float = 2.0
            class reproduction:
                base_conception_chance: float = 0.15
                pregnancy_duration_days: float = 270.0
                base_daily_miscarriage_rate: float = 0.0005
            class mortality:
                hard_cap_age_days: float = 30000.0  # ~82 años límite celular base
                global_carrying_capacity: int = 150
        
        self.config: Any = Config()
        
        # 2. INSTANCIACIÓN DE TODOS LOS SISTEMAS
        self.memory_system: CognitiveMemorySystem = CognitiveMemorySystem(self.config)
        self.movement_system: MovementSystem = MovementSystem(self.config, density_system=None, relationship_system=MockRelationshipSystem())
        self.evolution_engine: EvolutionEngine = EvolutionEngine(self.config, ancestry_queries=None)
        self.mortality_system: MortalitySystem = MortalitySystem(self.config)
        self.conception_system: ConceptionSystem = ConceptionSystem(self.config)
        self.gestation_system: GestationSystem = GestationSystem(self.config, evolution_engine=self.evolution_engine)
        
        self.logger.info("🚀 Todos los sistemas integrados. El motor ecosistémico está listo.")

    def run(self, total_days: float, delta_days: float) -> None:
        """Ejecuta el bucle cronológico principal."""
        state: WorldState = WorldState(config=self.config, width=100, height=100)
        
        # ─── POBLACIÓN FUNDADORA (GENERACIÓN 0) ───
        self.logger.info("🧬 Generando 50 individuos fundadores de la Generación 0...")
        for i in range(1, 51):
            gen = Genome()
            
            # Inicialización robusta (soporta diccionarios y propiedades directas)
            stress_val = random.uniform(0.3, 0.8)
            fert_val = random.uniform(0.5, 0.9)
            imm_val = random.uniform(0.4, 0.8)
            long_val = random.uniform(0.4, 0.8)
            
            # 1. Como atributos directos (requerido por Person)
            gen.stress_resistance = stress_val
            gen.fertility = fert_val
            gen.immunity = imm_val
            gen.longevity = long_val
            
            # 2. Como diccionario interno (si tu clase Genome lo expone)
            if hasattr(gen, 'genes') and isinstance(gen.genes, dict):
                gen.genes['stress_resistance'] = stress_val
                gen.genes['fertility'] = fert_val
                gen.genes['immunity'] = imm_val
                gen.genes['longevity'] = long_val
            
            p = Person(
                entity_id=i, 
                age=random.uniform(6500.0, 11000.0),  # Tienen entre 17 y 30 años en días biológicos
                x=random.randint(10, 90), 
                y=random.randint(10, 90), 
                genome=gen
            )
            
            p.set_health_state("sano")
            p._is_adult = True
            p.update_pregnancy(False, 0.0)
            
            partner = i + 1 if i % 2 != 0 else i - 1
            p.register_marriage(partner)
            
            state.add_person(p)

        current_day: float = 0.0
        self.logger.info(f"🟢 Iniciando simulación de {total_days} días (Tick Δt = {delta_days} días).")

        # ─── BUCLE EVOLUTIVO CONTINUO ───
        while current_day < total_days:
            state.world_days_elapsed = current_day
            pending: PendingChanges = PendingChanges()
            context: EnvironmentContext = EnvironmentContext(state, sector_size=10, carrying_capacity=200)

            # 1. Conducta y Libre Albedrío
            self.memory_system.process(state, pending, delta_days, context)
            self.movement_system.process(state, pending, delta_days, context)

            # 2. Ciclo de Vida (Reproducción)
            self.conception_system.process(state, pending, delta_days, context)
            self.gestation_system.process(state, pending, delta_days, context)

            # 3. Criba de Selección (Mortalidad)
            self.mortality_system.process(state, pending, delta_days, context)

            # 4. Física y Colisiones de Posición
            MovementResolver.resolve(pending, state)

            # 5. El tiempo avanza inevitablemente
            # Registramos el incremento de edad en el buffer ANTES del commit
            for person in state.get_all_persons():
                pending.register_age_increment(person.entity_id, delta_days)

            # 6. UNICO COMMIT ATÓMICO
            # Tu world_state procesa secuencialmente todo el buffer limpio y ordenado
            state.apply_commit(pending)

            # 7. Telemetría Darwiniana
            self.evolution_engine.process(state, pending, delta_days, context)

            current_day += delta_days

        self.logger.info("🏁 Simulación de un año completada. Exportando datos históricos...")
        self.evolution_engine.export_to_json(state, "historico_evolucion.json")

if __name__ == "__main__":
    launcher = SimulationLauncher()
    # Ejecutamos 365 días (1 año completo)
    launcher.run(total_days=365.0, delta_days=1.0)