"""Planificador de fases del motor de simulación.

DOCUMENTACIÓN DEL CICLO DE VIDA (TICK):
-------------------------------------------------------------------------------
La simulación opera en una arquitectura de Tiempo Discreto con Búfer Transaccional.
Cada tick completo procesa las siguientes fases en estricto orden secuencial:

1. Fase Temporal ('temporal'):
   - Actualiza los relojes internos de la simulación.
   - Incrementa la edad biológica de las entidades en el búfer transaccional.

2. Fase Ambiental ('environment'):
   - Propaga variables físicas (cargas virales, degradación de recursos).
   - Calcula el mapa de densidad poblacional.
   - Actualiza la memoria cognitiva de los agentes según el estrés del entorno.

3. Fase de Movimiento y Conducta ('behavior_and_movement'):
   - Evalúa decisiones autónomas y rebeldía (FreeWillSystem).
   - Calcula vectores de migración masiva (MigrationSystem).
   - Genera vectores de desplazamiento para el tick (MovementSystem).
   - Resuelve colisiones espaciales físicas (MovementResolver).

4. Fase Social ('relationships'):
   - Purga relaciones inválidas y declara viudedades.
   - Genera nuevos compromisos y cortejos simétricos.
   - Procesa reasignaciones familiares legales (Adopciones).

5. Fase de Salud ('health'):
   - Resuelve interacciones inmunológicas y calcula contagios/recuperaciones.

6. Fase Reproductiva ('reproduction'):
   - Verifica las ventanas de fertilidad e inicia concepciones.
   - Procesa los embarazos en curso y encola nacimientos con mutaciones genéticas.

7. Fase de Mortalidad ('mortality'):
   - Calcula las curvas de supervivencia (Gompertz) y decreta fallecimientos.
   - Purga las acciones de los recién fallecidos del búfer (DeathResolver) 
     para evitar que existan acciones de 'fantasmas' pendientes de commit.

8. Fase Observacional ('observers'):
   - Sincroniza el árbol genealógico.
   - Actualiza métricas poblacionales macroscópicas y el motor evolutivo.

[COMMIT]: Al terminar el pipeline, `WorldState.apply_commit()` consolida el 
búfer y altera los objetos de memoria.
-------------------------------------------------------------------------------
"""

from __future__ import annotations

import logging

from core.config.simulation_config import SimulationConfig
from core.execution.phase_executor import PhaseDefinition

# Importaciones de los subsistemas del motor
from systems.adoptions.adoption_system import AdoptionSystem
from systems.aging.aging_system import AgingSystem
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
from systems.diseases.disease_system import DiseaseSystem
from systems.environment.density_system import DensitySystem
from systems.environment.environment_system import EnvironmentSystem
from systems.environment.epidemiological_system import EpidemiologicalSystem
from systems.evolution.evolution_engine import EvolutionEngine
from systems.free_will.free_will_system import FreeWillSystem
from systems.genealogy.ancestry_queries import AncestryQueries
from systems.genealogy.genealogy_system import GenealogySystem
from systems.metrics.metrics_system import MetricsSystem
from systems.mortality.death_resolver import DeathResolver
from systems.mortality.mortality_system import MortalitySystem
from systems.movement.migration_system import MigrationSystem
from systems.movement.movement_resolver import MovementResolver
from systems.movement.movement_system import MovementSystem
from systems.relationships.marriage_system import MarriageSystem
from systems.relationships.relationship_system import RelationshipSystem
from systems.reproduction.conception_system import ConceptionSystem
from systems.reproduction.gestation_system import GestationSystem
from systems.temporal.temporal_system import TemporalSystem


class PhaseScheduler:
    """Construye la lista maestra de fases y sistemas activos del motor."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el planificador orquestando la inyección de dependencias.

        Args:
            config: Configuración compartida de la simulación.
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def build_phases(self) -> list[PhaseDefinition]:
        """Ensambla las fases de ejecución en el orden del ciclo principal.

        Se aplican inyecciones cruzadas seguras garantizando que se resuelvan
        las dependencias inter-sistema antes de la ejecución del pipeline.

        Returns:
            Lista ordenada de fases que serán ejecutadas por el pipeline.
        """
        # Construcción de dependencias compartidas inter-sistema
        genealogy_system = GenealogySystem(self.config)
        ancestry_queries = AncestryQueries(genealogy_system=genealogy_system)

        evolution_engine = EvolutionEngine(
            self.config,
            ancestry_queries=ancestry_queries,
        )

        density_system = DensitySystem(self.config)

        relationship_system = RelationshipSystem(
            config=self.config,
            ancestry_queries=ancestry_queries,
        )

        # Definición estructurada del ciclo biológico y físico
        # Nota: Se añade ignore[arg-type] para mitigar la invarianza estricta de listas en Python
        phases = [
            PhaseDefinition(
                name="temporal",
                systems=[
                    TemporalSystem(self.config),
                    AgingSystem(self.config),
                ],  # type: ignore[arg-type]
            ),
            PhaseDefinition(
                name="environment",
                systems=[
                    EnvironmentSystem(self.config),
                    density_system,
                    EpidemiologicalSystem(self.config),
                    CognitiveMemorySystem(self.config),
                ],  # type: ignore[arg-type]
            ),
            PhaseDefinition(
                name="behavior_and_movement",
                systems=[
                    FreeWillSystem(self.config),
                    MigrationSystem(self.config),
                    MovementSystem(
                        config=self.config,
                        density_system=density_system,
                        relationship_system=relationship_system,
                    ),
                    MovementResolver(self.config),
                ],  # type: ignore[arg-type]
            ),
            PhaseDefinition(
                name="relationships",
                systems=[
                    relationship_system,
                    MarriageSystem(
                        config=self.config,
                        ancestry_queries=ancestry_queries,
                    ),
                    # Se inyecta la dependencia genealógica para evaluar Kin Selection
                    AdoptionSystem(
                        config=self.config,
                        ancestry_queries=ancestry_queries,
                    ),
                ],  # type: ignore[arg-type]
            ),
            PhaseDefinition(
                name="health",
                systems=[
                    DiseaseSystem(self.config),
                ],  # type: ignore[arg-type]
            ),
            PhaseDefinition(
                name="reproduction",
                systems=[
                    ConceptionSystem(self.config),
                    GestationSystem(
                        config=self.config,
                        evolution_engine=evolution_engine,
                    ),
                ],  # type: ignore[arg-type]
            ),
            PhaseDefinition(
                name="mortality",
                systems=[
                    MortalitySystem(self.config),
                    DeathResolver(self.config),
                ],  # type: ignore[arg-type]
            ),
            PhaseDefinition(
                name="observers",
                systems=[
                    genealogy_system,
                    MetricsSystem(self.config),
                    evolution_engine,
                ],  # type: ignore[arg-type]
            ),
        ]

        self._validate_phases(phases)
        return phases

    def get_registered_system_names(self) -> list[str]:
        """Devuelve los nombres de los sistemas registrados para análisis y logging.

        Returns:
            Lista de nombres de clase de todos los sistemas activos.
        """
        names: list[str] = []
        for phase in self.build_phases():
            for system in phase.systems:
                names.append(system.__class__.__name__)
        return names

    def _validate_phases(self, phases: list[PhaseDefinition]) -> None:
        """Comprueba en tiempo de arranque que los sistemas cumplan el contrato Protocol.

        Args:
            phases: Fases a validar.

        Raises:
            TypeError: Si algún sistema no implementa el método `process`.
            ValueError: Si existe una fase anónima.
        """
        for phase in phases:
            if not phase.name:
                raise ValueError("Todas las fases deben tener un nombre estricto.")

            for system in phase.systems:
                process = getattr(system, "process", None)
                if not callable(process):
                    system_name = system.__class__.__name__
                    raise TypeError(
                        f"Fallo estructural: El sistema {system_name} no "
                        f"implementa el método requerido process(...)."
                    )