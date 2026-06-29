"""Módulo responsable de las dinámicas sociales y mantenimiento de vínculos.

Se especializa en evaluar la tensión de las parejas existentes y registrar
rupturas o viudedades si el estrés y la incompatibilidad superan el amor.
"""

from __future__ import annotations

import logging
import random
from typing import Any, Optional

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext


class RelationshipSystem:
    """Motor de vínculos sentimentales especializado en rupturas y memoria."""

    def __init__(self, config: SimulationConfig, ancestry_queries: Any = None) -> None:
        """Inicializa el sistema de relaciones.

        Args:
            config: Configuración compartida de la simulación.
            ancestry_queries: Sistema de consultas genealógicas (opcional).
        """
        self.config = config
        self.ancestry_queries = ancestry_queries
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Evalúa la tensión matrimonial en cada ciclo de la simulación.

        Args:
            state: Estado autoritativo del mundo.
            pending: Búfer transaccional de cambios.
            delta_days: Fracción de tiempo simulado.
            context: Contexto del entorno actual.
        """
        vivos = [p for p in state.get_all_persons() if p.entity_id not in pending.deaths]
        casados = [p for p in vivos if getattr(p, "marital_status", "") == "casado"]

        self._process_breakups(casados, state, pending)

    def get_social_anchor(self, person: Any, state: WorldState) -> Optional[Any]:
        """Obtiene la entidad que sirve como centro de gravedad social para el agente.

        Actualmente prioriza a la pareja sentimental (cónyuge) si existe en la simulación.

        Args:
            person: La entidad que busca su ancla social.
            state: El estado actual del mundo para recuperar a la pareja.

        Returns:
            El objeto de la persona ancla si existe y está viva, None en caso contrario.
        """
        partner_id = getattr(person, "partner_id", None)
        if partner_id is not None:
            return state.get_person_by_id(partner_id)
        return None

    def _calculate_affinity(self, p1: Any, p2: Any) -> float:
        """Calcula el índice de compatibilidad [0.0 - 1.0] basado en rasgos dinámicos."""
        # Similitud en Sociabilidad
        soc_diff = abs(p1.effective_sociability - p2.effective_sociability)
        soc_score = max(0.0, 1.0 - (soc_diff / 2.0))

        # Complementariedad en Temperamento
        temp_diff = abs(p1.effective_temperament - p2.effective_temperament)
        temp_score = min(1.0, temp_diff / 1.5)

        # Penalización por brecha de edad
        age_diff = abs(p1.age - p2.age)
        age_penalty = min(0.5, age_diff / 10000.0)

        base_affinity = (soc_score * 0.5) + (temp_score * 0.5) - age_penalty
        return max(0.01, min(1.0, base_affinity))

    def _process_breakups(
        self, casados: list[Any], state: WorldState, pending: PendingChanges
    ) -> None:
        """Evalúa si el desgaste emocional o la viudedad rompen el vínculo."""
        procesados = set()

        for person in casados:
            if person.entity_id in procesados or getattr(person, "partner_id", None) is None:
                continue

            partner = state.get_person_by_id(person.partner_id)

            # Gestión de viudedad diferida
            if not partner or partner.entity_id in pending.deaths:
                self._execute_breakup(person, partner, pending, is_death=True)
                procesados.add(person.entity_id)
                continue

            # Riesgo de ruptura por estrés relacional
            affinity = self._calculate_affinity(person, partner)
            
            p1_stress = getattr(person, "emotions", {}).get("stress", 0.0)
            p2_stress = getattr(partner, "emotions", {}).get("stress", 0.0)
            combined_stress = (p1_stress + p2_stress) / 2.0

            breakup_risk = max(0.0, combined_stress - affinity) * 0.1

            if random.random() < breakup_risk:
                self._execute_breakup(person, partner, pending)
                procesados.add(person.entity_id)
                procesados.add(partner.entity_id)

    def _execute_breakup(
        self, p1: Any, p2: Any, pending: PendingChanges, is_death: bool = False
    ) -> None:
        """Registra el divorcio atómico y actualiza el historial sentimental."""
        # FIX: Se envían ambos IDs en la misma tupla transaccional
        if p2:
            pending.register_divorce(p1.entity_id, p2.entity_id)
        else:
            # Caso extremo de salvaguarda por si p2 ya no existe en memoria
            pending.register_divorce(p1.entity_id, p1.partner_id)

        if not is_death and p2:
            # Almacenamos al ex en la memoria cognitiva para evitar reconciliaciones inmediatas
            for p, ex_id in [(p1, p2.entity_id), (p2, p1.entity_id)]:
                if hasattr(p, "memory") and isinstance(p.memory, dict):
                    historial = p.memory.setdefault("ex_partners", [])
                    if ex_id not in historial:
                        historial.append(ex_id)

            self.logger.debug(
                "💔 Ruptura elaborada: %s y %s se han separado.",
                p1.entity_id,
                p2.entity_id,
            )