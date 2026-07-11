"""Módulo responsable de la integridad transaccional tras eventos de mortalidad."""

import logging
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig


class DeathResolver:
    """Filtro de contingencia para purgar intenciones de entidades fallecidas."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el resolutor cumpliendo el contrato de la arquitectura."""
        self.config = config
        self.logger = logging.getLogger("DeathResolver")

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Ejecuta la purga de acciones en cascada sobre el búfer transaccional."""
        if not pending.deaths:
            return

        muertos_set = set(pending.deaths)

        # 1. Cancelar desplazamientos espaciales
        pending.movements = {
            e_id: coords
            for e_id, coords in pending.movements.items()
            if e_id not in muertos_set
        }

        # 2. Cancelar envejecimiento
        pending.age_increments = {
            e_id: inc
            for e_id, inc in pending.age_increments.items()
            if e_id not in muertos_set
        }

        # 3. Cancelar infecciones recientes (desempaquetando tuplas)
        pending.infections = [
            (e_id, pathogen)
            for e_id, pathogen in pending.infections
            if e_id not in muertos_set
        ]

        # 4. Cancelar recuperaciones de enfermedades
        pending.recoveries = [
            (e_id, pathogen_id)
            for e_id, pathogen_id in pending.recoveries
            if e_id not in muertos_set
        ]

        # 5. Cancelar trámites de nupcias
        pending.marriages = {
            p_a: p_b
            for p_a, p_b in pending.marriages.items()
            if p_a not in muertos_set and p_b not in muertos_set
        }

        # 6. Cancelar trámites de divorcio
        pending.divorces = [
            (pa, pb)
            for pa, pb in pending.divorces
            if pa not in muertos_set and pb not in muertos_set
        ]

        # 7. Cancelar procesos de adopción
        if hasattr(pending, "adoptions"):
            pending.adoptions = [
                adop
                for adop in pending.adoptions
                if adop.get("child_id") not in muertos_set
                and adop.get("parent_a") not in muertos_set
                and adop.get("parent_b") not in muertos_set
            ]

        # 8. Cancelar actualizaciones de embarazo
        pending.pregnancy_updates = {
            e_id: data
            for e_id, data in pending.pregnancy_updates.items()
            if e_id not in muertos_set
        }

        # 9. Cancelar actualizaciones emocionales
        if hasattr(pending, "emotion_updates"):
            pending.emotion_updates = {
                e_id: updates
                for e_id, updates in pending.emotion_updates.items()
                if e_id not in muertos_set
            }

        # 10. Cancelar actualizaciones de memoria
        if hasattr(pending, "memory_updates"):
            pending.memory_updates = {
                e_id: updates
                for e_id, updates in pending.memory_updates.items()
                if e_id not in muertos_set
            }

        # 11. NUEVO: Cancelar actualizaciones de libre albedrío
        if hasattr(pending, "free_will_flags_updates"):
            pending.free_will_flags_updates = {
                e_id: flags
                for e_id, flags in pending.free_will_flags_updates.items()
                if e_id not in muertos_set
            }

        self.logger.debug(
            "DeathResolver: Purgadas %d entidades fallecidas del búfer transaccional",
            len(muertos_set),
        )