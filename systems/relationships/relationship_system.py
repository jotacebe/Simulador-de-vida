"""Módulo responsable de las dinámicas sociales y mantenimiento de vínculos.

Se especializa en evaluar la tensión de las parejas existentes y registrar
rupturas o viudedades si el estrés y la incompatibilidad superan el amor.

Integra con:
- Sistema de memoria cognitiva para registrar recuerdos de divorcios y duelos
- Sistema de afinidad basado en recuerdos compartidos
- Sistema de motivaciones continuas para comportamiento emergente
- NUEVO: Registro de fechas de divorcio para cooldown de reconciliación

La afinidad considera:
- Rasgos dinámicos (sociabilidad, temperamento)
- Brecha de edad
- RECUERDOS COMPARTIDOS: experiencias positivas/negativas acumuladas

Todos los cambios se registran en el búfer transaccional y se aplican
atómicamente durante el commit, garantizando coherencia del estado.
"""

from __future__ import annotations

import logging
import random
from typing import Any, Optional

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
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
        """Calcula el índice de compatibilidad [0.0 - 1.0] basado en rasgos dinámicos Y recuerdos.
        
        La afinidad considera:
        1. Similitud en sociabilidad y temperamento (base)
        2. Penalización por brecha de edad
        3. Bias basado en recuerdos compartidos (experiencias positivas/negativas)
        
        Args:
            p1: Primera persona.
            p2: Segunda persona.
            
        Returns:
            Score de afinidad [0.0, 1.0].
        """
        # 1. AFINIDAD BASE (Rasgos dinámicos)
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
        base_affinity = max(0.01, min(1.0, base_affinity))

        # 2. BIAS BASADO EN RECUERDOS COMPARTIDOS
        # Obtener el bias de p1 hacia p2 basado en sus recuerdos
        bias_towards = CognitiveMemorySystem.get_bias_towards(p1, str(p2.entity_id))
        
        # El bias puede modificar la afinidad base hasta un ±40%
        memory_modifier = bias_towards * 0.4
        
        # Aplicar el modificador
        final_affinity = base_affinity + memory_modifier
        
        # Clampar el resultado final
        final_affinity = max(0.01, min(1.0, final_affinity))
        
        # Logging para debugging
        if abs(memory_modifier) > 0.1:
            self.logger.debug(
                "💭 Afinidad %s→%s: base=%.2f, bias=%.2f, final=%.2f",
                p1.entity_id,
                p2.entity_id,
                base_affinity,
                memory_modifier,
                final_affinity,
            )

        return final_affinity

    def _process_breakups(
        self, casados: list[Any], state: WorldState, pending: PendingChanges
    ) -> None:
        """Evalúa si el desgaste emocional o la viudedad rompen el vínculo.
        
        Args:
            casados: Lista de personas casadas.
            state: Estado autoritativo del mundo.
            pending: Búfer transaccional de cambios.
        """
        procesados = set()
        fw_cfg = self.config.free_will

        for person in casados:
            if person.entity_id in procesados or getattr(person, "partner_id", None) is None:
                continue

            partner = state.get_person_by_id(person.partner_id)

            # Gestión de viudedad diferida
            if not partner or partner.entity_id in pending.deaths:
                self._execute_breakup(person, partner, pending, is_death=True, state=state)
                procesados.add(person.entity_id)
                continue

            # Riesgo de ruptura por estrés relacional
            affinity = self._calculate_affinity(person, partner)
            
            p1_stress = getattr(person, "emotions", {}).get("stress", 0.0)
            p2_stress = getattr(partner, "emotions", {}).get("stress", 0.0)
            combined_stress = (p1_stress + p2_stress) / 2.0

            breakup_risk = max(0.0, combined_stress - affinity) * 0.1

            # MODULACIÓN POR MOTIVACIONES CONTINUAS
            # Las motivaciones del agente modifican la probabilidad de ruptura:
            # - 'partnership' alta → reduce el riesgo (deseo de mantener la relación)
            # - 'independence' alta → aumenta el riesgo (deseo de autonomía)
            # - 'rebellion' alta → aumenta el riesgo (tendencia a romper normas)
            
            if hasattr(person, 'get_motivation'):
                partnership = person.get_motivation("partnership")
                independence = person.get_motivation("independence")
                rebellion = person.get_motivation("rebellion")
                
                # partnership reduce el riesgo (hasta -50%)
                partnership_modifier = 1.0 - (partnership * 0.5)
                
                # independence y rebellion aumentan el riesgo (hasta +30% y +20%)
                independence_modifier = 1.0 + (independence * 0.3)
                rebellion_modifier = 1.0 + (rebellion * 0.2)
                
                # Aplicar modificadores
                breakup_risk *= partnership_modifier * independence_modifier * rebellion_modifier
                
                # Logging para debugging
                if partnership > 0.7 or independence > 0.7 or rebellion > 0.7:
                    self.logger.debug(
                        "💔 Agente %s: partnership=%.2f, independence=%.2f, rebellion=%.2f → breakup_risk=%.4f",
                        person.entity_id,
                        partnership,
                        independence,
                        rebellion,
                        breakup_risk,
                    )

            if random.random() < breakup_risk:
                self._execute_breakup(person, partner, pending, is_death=False, state=state)
                procesados.add(person.entity_id)
                procesados.add(partner.entity_id)

    def _execute_breakup(
        self,
        p1: Any,
        p2: Any,
        pending: PendingChanges,
        is_death: bool = False,
        state: Optional[WorldState] = None,
    ) -> None:
        """Registra el divorcio atómico y actualiza el historial sentimental.
        
        Args:
            p1: Primera persona de la ruptura.
            p2: Segunda persona de la ruptura (puede ser None si murió).
            pending: Búfer transaccional de cambios.
            is_death: True si la ruptura es por muerte (viudedad), False si es divorcio.
            state: Estado del mundo (para obtener el día actual).
        """
        # FIX: Se envían ambos IDs en la misma tupla transaccional
        if p2:
            pending.register_divorce(p1.entity_id, p2.entity_id)
        else:
            # Caso extremo de salvaguarda por si p2 ya no existe en memoria
            pending.register_divorce(p1.entity_id, p1.partner_id)

        # Día actual para los recuerdos
        current_day = getattr(state, 'world_days_elapsed', 0.0) if state else 0.0
        fw_cfg = self.config.free_will

        if not is_death and p2:
            # =================================================================
            # DIVORCIO: Registrar recuerdo negativo para ambos
            # =================================================================
            # Almacenamos al ex en la memoria cognitiva para evitar reconciliaciones inmediatas
            for p, ex_id in [(p1, p2.entity_id), (p2, p1.entity_id)]:
                if hasattr(p, "memory") and isinstance(p.memory, dict):
                    historial = p.memory.setdefault("ex_partners", [])
                    if ex_id not in historial:
                        historial.append(ex_id)
                    
                    # =================================================================
                    # NUEVO: REGISTRAR FECHA DEL DIVORCIO PARA COOLDOWN
                    # =================================================================
                    # Guardamos la fecha del divorcio con cada ex para verificar cooldown
                    # Esto permite que marriage_system.py verifique cuánto tiempo ha pasado
                    divorce_dates = p.memory.setdefault("divorce_dates", {})
                    divorce_dates[str(ex_id)] = current_day
                
                # NUEVO: Registrar recuerdo del divorcio (transaccional)
                # Intensidad alta (0.9) porque es un evento vital traumático
                # Valencia muy negativa (-1) porque el divorcio es doloroso
                # Contexto específico para análisis futuro
                CognitiveMemorySystem.add_memory(
                    person=p,
                    mem_type=CognitiveMemorySystem.TYPE_DIVORCE,
                    target_id=str(ex_id),
                    intensity=0.9,
                    valence=-1,
                    context="divorcio",
                    current_day=current_day,
                    pending=pending,
                )
                
                # =================================================================
                # APRENDIZAJE POST-RUPTURA: Ajustar motivaciones
                # =================================================================
                # Un divorcio refuerza 'independence' (aprendí a valerme por mí mismo)
                # y debilita 'partnership' (las relaciones son dolorosas)
                if hasattr(p, 'get_motivation'):
                    # Reforzar independence (éxito en autonomía)
                    pending.register_motivation_update(
                        p.entity_id, "independence", fw_cfg.success_reinforcement_rate * 0.5
                    )
                    
                    # Debilitar partnership (experiencia negativa)
                    pending.register_motivation_update(
                        p.entity_id, "partnership", -fw_cfg.failure_punishment_rate * 0.7
                    )
                    
                    self.logger.debug(
                        "🎓 Agente %s ajustó motivaciones tras divorcio: independence +%.2f, partnership -%.2f",
                        p.entity_id,
                        fw_cfg.success_reinforcement_rate * 0.5,
                        fw_cfg.failure_punishment_rate * 0.7,
                    )

            self.logger.debug(
                "💔 Ruptura elaborada: %s y %s se han separado (recuerdos registrados).",
                p1.entity_id,
                p2.entity_id,
            )
        
        elif is_death:
            # =================================================================
            # VIUDEDAD: Registrar recuerdo de duelo intenso
            # =================================================================
            # La persona que sobrevive recuerda la muerte de su pareja
            # Intensidad máxima (1.0) porque es el evento más traumático
            # Valencia muy negativa (-1) porque es una pérdida irreparable
            # Contexto específico para análisis de duelo
            partner_id = p2.entity_id if p2 else p1.partner_id
            
            CognitiveMemorySystem.add_memory(
                person=p1,
                mem_type=CognitiveMemorySystem.TYPE_DEATH,
                target_id=str(partner_id),
                intensity=1.0,
                valence=-1,
                context="muerte_pareja",
                current_day=current_day,
                pending=pending,
            )
            
            self.logger.debug(
                "🕊️ Viudedad registrada: %s ha perdido a su pareja %s (recuerdo de duelo registrado).",
                p1.entity_id,
                partner_id,
            )