"""Módulo responsable de gestionar el cortejo y los matrimonios de forma transaccional.

Evita duplicados de forma matemática y calcula compatibilidades basándose en:
- Orientación sexual (espectro Kinsey)
- Rasgos fenotípicos dinámicos (emociones)
- Distancia espacial
- Historial de relaciones

Integra con:
- Sistema de memoria cognitiva para registrar recuerdos de matrimonios
- Sistema de motivaciones continuas para comportamiento emergente
- Cooldown de reconciliación para evitar divorcio/reconciliación en bucle

Todos los cambios se registran en el búfer transaccional y se aplican
atómicamente durante el commit, garantizando coherencia del estado.
"""

import logging
import math
import random
from typing import Any, Set, List, Tuple

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
from systems.environment.environment_context import EnvironmentContext
from systems.relationships.relationship_model import (
    SexualOrientation,
    is_orientation_compatible,
)


class MarriageSystem:
    """Gestiona el mercado de solteros, rechazos y matrimonios espontáneos."""

    def __init__(self, config: SimulationConfig, ancestry_queries: Any) -> None:
        """Inicializa el sistema vinculándolo a la configuración y consultas genealógicas.
        
        Args:
            config: Configuración maestra de la simulación.
            ancestry_queries: Sistema de consultas genealógicas para evitar incesto.
        """
        self.config = config
        self.ancestry_queries = ancestry_queries
        self.logger = logging.getLogger(self.__class__.__name__)

    def _calcular_compatibilidad(self, p1: Any, p2: Any) -> float:
        """Evalúa la afinidad considerando orientación sexual y rasgos dinámicos.
        
        Args:
            p1: Primera persona.
            p2: Segunda persona.
            
        Returns:
            Score de compatibilidad [0.0, 1.0].
        """
        # 1. Compatibilidad de orientación sexual (factor crítico)
        orientation_score = is_orientation_compatible(
            p1.sexual_orientation,
            p2.sexual_orientation,
            tolerance=self.config.relationships.orientation_tolerance
        )
        
        # Si no son compatibles sexualmente, retornar 0
        if orientation_score <= 0.0:
            return 0.0
        
        # 2. Afinidad demográfica (sociabilidad + temperamento)
        soc1, soc2 = p1.effective_sociability, p2.effective_sociability
        temp1, temp2 = p1.effective_temperament, p2.effective_temperament
        
        afinidad = 1.0 - ((abs(soc1 - soc2) + abs(temp1 - temp2)) / 2.0)
        
        # 3. Factor de edad
        dif_edad_dias = abs(p1.age - p2.age)
        dif_edad_anios = dif_edad_dias / 365.0
        
        factor_edad = max(0.2, 1.0 - (dif_edad_anios * 0.02)) if dif_edad_anios > 15.0 else 1.0
        
        # Combinar todos los factores
        return afinidad * factor_edad * orientation_score

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Procesa las intenciones de emparejamiento evaluando afinidad y rechazos.
        
        Args:
            state: Estado autoritativo del mundo.
            pending: Búfer transaccional de cambios.
            delta_days: Fracción de tiempo simulado.
            context: Contexto del entorno actual.
        """
        rel_cfg = self.config.relationships
        fw_cfg = self.config.free_will
        all_persons = state.get_all_persons()
        
        # Filtrar solteros (sin distinción de género)
        solteros = [
            p for p in all_persons 
            if p.age >= rel_cfg.min_marriage_age_days 
            and p.partner_id is None 
            and getattr(p, 'marital_status', 'soltero') != "casado" 
            and p.entity_id not in pending.deaths
        ]
        
        if len(solteros) < 2: 
            return
        
        total_marriage_chance = 1.0 - math.exp(-rel_cfg.base_marriage_chance * delta_days)
        total_flechazo = 1.0 - math.exp(-rel_cfg.love_at_first_sight_chance * delta_days)
        
        random.shuffle(solteros)
        comprometidos_hoy: Set[int] = set()

        current_day = getattr(state, 'world_days_elapsed', 0.0)

        for persona in solteros:
            if persona.entity_id in comprometidos_hoy:
                continue

            # FILTRADO POR MOTIVACIÓN 'independence'
            if hasattr(persona, 'get_motivation'):
                independence = persona.get_motivation("independence")
                if independence > 0.8 and random.random() > 0.2:
                    continue

            mejor_candidato, mejor_score, flechazo = None, -1.0, False

            for candidato in solteros:
                if candidato.entity_id == persona.entity_id:
                    continue
                if candidato.entity_id in comprometidos_hoy: 
                    continue
                    
                if abs(persona.x - candidato.x) > rel_cfg.courtship_radius or \
                   abs(persona.y - candidato.y) > rel_cfg.courtship_radius: 
                    continue
                    
                if self.ancestry_queries.is_forbidden_marriage(persona.entity_id, candidato.entity_id):
                    continue

                if random.random() < total_flechazo:
                    mejor_candidato, flechazo = candidato, True
                    break

                score = self._calcular_compatibilidad(persona, candidato)
                
                # Si no son compatibles, saltar
                if score <= 0.0:
                    continue
                
                # MODULACIÓN POR MOTIVACIÓN 'partnership'
                if hasattr(persona, 'get_motivation'):
                    partnership = persona.get_motivation("partnership")
                    score += partnership * 0.2
                
                if score > mejor_score:
                    mejor_score, mejor_candidato = score, candidato

            if mejor_candidato:
                # Sistema de Reconciliación (¿Es un ex?)
                historial = persona.memory.get("ex_partners", [])
                es_ex = mejor_candidato.entity_id in historial
                
                # VERIFICAR COOLDOWN DE RECONCILIACIÓN
                reconciliation_cooldown = getattr(fw_cfg, 'reconciliation_cooldown_days', 180.0)
                can_reconcile = True
                
                if es_ex:
                    divorce_dates = persona.memory.get("divorce_dates", {})
                    last_divorce_day = divorce_dates.get(str(mejor_candidato.entity_id), 0.0)
                    days_since_divorce = current_day - last_divorce_day
                    
                    if days_since_divorce < reconciliation_cooldown:
                        can_reconcile = False
                        self.logger.debug(
                            "⏳ Agente %s no puede reconciliar con %s (cooldown: %.0f/%.0f días)",
                            persona.entity_id,
                            mejor_candidato.entity_id,
                            days_since_divorce,
                            reconciliation_cooldown,
                        )
                
                # Si es un ex Y no puede reconciliar, saltar
                if es_ex and not can_reconcile:
                    continue
                
                # Si es un ex Y puede reconciliar, requieren mucha más afinidad
                umbral_requerido = 0.6 if es_ex else 0.4
                chance = 1.0 if flechazo else (total_marriage_chance * mejor_score)
                
                if mejor_score >= umbral_requerido and random.random() < chance:
                    # REGISTRO TRANSACCIONAL DEL MATRIMONIO
                    pending.register_marriage(persona.entity_id, mejor_candidato.entity_id)
                    comprometidos_hoy.add(persona.entity_id)
                    comprometidos_hoy.add(mejor_candidato.entity_id)
                    
                    context_type = "flechazo" if flechazo else ("reconciliacion" if es_ex else "cortejo")
                    
                    # La primera persona recuerda el matrimonio
                    CognitiveMemorySystem.add_memory(
                        person=persona,
                        mem_type=CognitiveMemorySystem.TYPE_MARRIAGE,
                        target_id=str(mejor_candidato.entity_id),
                        intensity=0.8,
                        valence=1,
                        context=context_type,
                        current_day=current_day,
                        pending=pending,
                    )
                    
                    # La segunda persona recuerda el matrimonio
                    CognitiveMemorySystem.add_memory(
                        person=mejor_candidato,
                        mem_type=CognitiveMemorySystem.TYPE_MARRIAGE,
                        target_id=str(persona.entity_id),
                        intensity=0.8,
                        valence=1,
                        context=context_type,
                        current_day=current_day,
                        pending=pending,
                    )
                    
                    # Aprendizaje post-matrimonio
                    for persona_inv in [persona, mejor_candidato]:
                        if hasattr(persona_inv, 'get_motivation'):
                            pending.register_motivation_update(
                                persona_inv.entity_id, "partnership", fw_cfg.success_reinforcement_rate
                            )
                            pending.register_motivation_update(
                                persona_inv.entity_id, "independence", -fw_cfg.success_reinforcement_rate * 0.3
                            )
                    
                    estado = "Reconciliación" if es_ex else ("Flechazo" if flechazo else "Nuevo cortejo")
                    self.logger.debug(
                        "❤️ %s transaccional: %s y %s (recuerdos registrados, motivaciones ajustadas)",
                        estado,
                        persona.entity_id,
                        mejor_candidato.entity_id,
                    )
                else:
                    # Mecánica de rechazo: Aumenta el estrés del rechazado
                    if hasattr(persona, 'update_emotion'):
                        persona.update_emotion("stress", 0.05)