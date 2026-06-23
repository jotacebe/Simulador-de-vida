"""Módulo responsable del avance de la gestación y partos múltiples dentro de la simulación.

Este sistema controla los ciclos biológicos de preñez de las distintas especies,
evalúa el progreso temporal de los embarazos y ejecuta los partos consolidando
la herencia genética a través del motor evolutivo.
"""

from __future__ import annotations

import logging
from typing import Any

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext
from systems.evolution.evolution_engine import EvolutionEngine


class GestationSystem:
    """Gestiona el tiempo de gestación y la ejecución de partos múltiples (camadas)."""

    def __init__(
        self,
        config: SimulationConfig,
        evolution_engine: EvolutionEngine,
    ) -> None:
        """Inicializa el sistema de gestación orquestando sus dependencias.

        Args:
            config: Configuración compartida de la simulación.
            evolution_engine: Instancia del motor de evolución de la aplicación.
        """
        self.config = config
        self.evolution_engine = evolution_engine
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_species_traits(self, species: str) -> dict[str, float]:
        """Recupera el perfil reproductivo local y específico de una especie.

        Args:
            species: Identificador de la especie (e.g., 'human', 'elf').

        Returns:
            Un diccionario con las propiedades biológicas de la especie.
        """
        profiles = {
            "human": {"gestation_days": float(self.config.reproduction.pregnancy_duration_days)},
            "elf": {"gestation_days": 730.0},
            "goblin": {"gestation_days": 120.0},
            "dragon": {"gestation_days": 1200.0}
        }
        return profiles.get(species, profiles["human"])

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Avanza los embarazos activos y dispara los nacimientos múltiples (camadas).

        Args:
            state: Estado autoritativo y actual del mundo en memoria.
            pending: Búfer transaccional para registrar cambios antes del commit.
            delta_days: Fracción de tiempo en días que avanza la simulación.
            context: Contexto físico y de variables del entorno actual.
        """
        for person in state.get_all_persons():
            # Si el agente ha fallecido en este tick o no está encinta, se descarta
            if person.entity_id in pending.deaths or not getattr(person, "is_pregnant", False):
                continue

            traits = self._get_species_traits(person.species)
            current_days = getattr(person, "pregnancy_days", 0.0)
            new_days = current_days + delta_days

            if new_days >= traits["gestation_days"]:
                # Recuperamos el tamaño de la camada guardada en la concepción
                litter_size = getattr(person, "litter_size_gestating", 1)

                # Bucle de nacimientos simultáneos
                for _ in range(litter_size):
                    self._execute_birth(person, state, pending)

                # Saneamiento del estado biológico de la gestante tras el parto
                pending.register_pregnancy_update(
                    person.entity_id,
                    is_pregnant=False,
                    pregnancy_days=0.0,
                    failed_increment=0,
                    litter_size=1,
                )
            else:
                # El embarazo progresa un tick más de forma segura
                pending.register_pregnancy_update(
                    person.entity_id,
                    is_pregnant=True,
                    pregnancy_days=new_days,
                    failed_increment=0,
                    litter_size=person.litter_size_gestating,
                )

    def _execute_birth(
        self,
        mother: Any,
        state: WorldState,
        pending: PendingChanges,
    ) -> None:
        """Culmina la meiosis individual de una sola cría de la camada.

        Genera el genoma recombinado y encola la inserción del nuevo agente.

        Args:
            mother: Instancia de la entidad gestante que da a luz.
            state: Estado autoritativo del mundo.
            pending: Búfer transaccional de cambios pendientes.
        """
        partner = state.get_person_by_id(mother.partner_id) if mother.partner_id else None

        # Si no hay partner, Genome.combine() aplicará Partenogénesis automáticamente
        father_genome = partner.genome if partner else None
        baby_genome = mother.genome.combine(father_genome)

        pending.register_birth(
            mother_id=mother.entity_id,
            father_id=mother.partner_id,  # Puede ser None (Legalmente es correcto)
            genome=baby_genome,
            x=mother.x,
            y=mother.y,
        )
        self.logger.info(
            "Cría nacida: Madre %s (Especie: %s)",
            mother.entity_id,
            mother.species,
        )