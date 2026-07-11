"""Módulo responsable de gestionar el cortejo y los matrimonios de forma transaccional.

Evita duplicados de forma matemática y calcula compatibilidades basándose en
los rasgos fenotípicos dinámicos (emociones) en lugar del genoma estático.

Integra con:
- Sistema de memoria cognitiva para registrar recuerdos de matrimonios
- Sistema de motivaciones continuas para comportamiento emergente
- NUEVO: Cooldown de reconciliación para evitar divorcio/reconciliación en bucle

Todos los cambios se registran en el búfer transaccional y se aplican
atómicamente durante el commit, garantizando coherencia del estado.
"""

import logging
import math
import random
from typing import Any, Set

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.behavior.cognitive_memory_system import CognitiveMemorySystem
from systems.environment.environment_context import EnvironmentContext


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
        """Evalúa la afinidad demográfica y el estado emocional actual.
        
        Args:
            p1: Primera persona.
            p2: Segunda persona.
            
        Returns:
            Score de compatibilidad [0.0, 1.0].
        """
        soc1, soc2 = p1.effective_sociability, p2.effective_sociability
        temp1, temp2 = p1.effective_temperament, p2.effective_temperament
        
        afinidad = 1.0 - ((abs(soc1 - soc2) + abs(temp1 - temp2)) / 2.0)
        
        dif_edad_dias = abs(p1.age - p2.age)
        dif_edad_anios = dif_edad_dias / 365.0
        
        factor_edad = max(0.2, 1.0 - (dif_edad_anios * 0.02)) if dif_edad_anios > 15.0 else 1.0
        return afinidad * factor_edad

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
        
        solteros = [
            p for p in all_persons 
            if p.age >= rel_cfg.min_marriage_age_days 
            and p.partner_id is None 
            and getattr(p, 'marital_status', 'soltero') != "casado" 
            and p.entity_id not in pending.deaths
        ]
        
        solteros_m = [p for p in solteros if getattr(p, 'gender', '') == "M"]
        solteros_f = [p for p in solteros if getattr(p, 'gender', '') == "F"]

        if not solteros_m or not solteros_f: 
            return
        
        total_marriage_chance = 1.0 - math.exp(-rel_cfg.base_marriage_chance * delta_days)
        total_flechazo = 1.0 - math.exp(-rel_cfg.love_at_first_sight_chance * delta_days)
        
        random.shuffle(solteros_m)
        comprometidos_hoy: Set[int] = set()

        current_day = getattr(state, 'world_days_elapsed', 0.0)

        for hombre in solteros_m:
            if hombre.entity_id in comprometidos_hoy:
                continue

            # FILTRADO POR MOTIVACIÓN 'independence'
            if hasattr(hombre, 'get_motivation'):
                independence = hombre.get_motivation("independence")
                if independence > 0.8 and random.random() > 0.2:
                    continue

            mejor_candidata, mejor_score, flechazo = None, -1.0, False

            for mujer in solteros_f:
                if mujer.entity_id in comprometidos_hoy: 
                    continue
                    
                if abs(hombre.x - mujer.x) > rel_cfg.courtship_radius or \
                   abs(hombre.y - mujer.y) > rel_cfg.courtship_radius: 
                    continue
                    
                if self.ancestry_queries.is_forbidden_marriage(hombre.entity_id, mujer.entity_id):
                    continue

                if random.random() < total_flechazo:
                    mejor_candidata, flechazo = mujer, True
                    break

                score = self._calcular_compatibilidad(hombre, mujer)
                
                # MODULACIÓN POR MOTIVACIÓN 'partnership'
                if hasattr(hombre, 'get_motivation'):
                    partnership = hombre.get_motivation("partnership")
                    score += partnership * 0.2
                
                if score > mejor_score:
                    mejor_score, mejor_candidata = score, mujer

            if mejor_candidata:
                # Sistema de Reconciliación (¿Es un ex?)
                historial = hombre.memory.get("ex_partners", [])
                es_ex = mejor_candidata.entity_id in historial
                
                # =================================================================
                # NUEVO: VERIFICAR COOLDOWN DE RECONCILIACIÓN
                # =================================================================
                reconciliation_cooldown = getattr(fw_cfg, 'reconciliation_cooldown_days', 180.0)
                can_reconcile = True
                
                if es_ex:
                    # Verificar cuánto tiempo pasó desde el divorcio
                    divorce_dates = hombre.memory.get("divorce_dates", {})
                    last_divorce_day = divorce_dates.get(str(mejor_candidata.entity_id), 0.0)
                    days_since_divorce = current_day - last_divorce_day
                    
                    if days_since_divorce < reconciliation_cooldown:
                        can_reconcile = False
                        self.logger.debug(
                            "⏳ Agente %s no puede reconciliar con %s (cooldown: %.0f/%.0f días)",
                            hombre.entity_id,
                            mejor_candidata.entity_id,
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
                    # =================================================================
                    # REGISTRO TRANSACCIONAL DEL MATRIMONIO
                    # =================================================================
                    pending.register_marriage(hombre.entity_id, mejor_candidata.entity_id)
                    comprometidos_hoy.add(hombre.entity_id)
                    comprometidos_hoy.add(mejor_candidata.entity_id)
                    
                    context_type = "flechazo" if flechazo else ("reconciliacion" if es_ex else "cortejo")
                    
                    # El hombre recuerda el matrimonio
                    CognitiveMemorySystem.add_memory(
                        person=hombre,
                        mem_type=CognitiveMemorySystem.TYPE_MARRIAGE,
                        target_id=str(mejor_candidata.entity_id),
                        intensity=0.8,
                        valence=1,
                        context=context_type,
                        current_day=current_day,
                        pending=pending,
                    )
                    
                    # La mujer recuerda el matrimonio
                    CognitiveMemorySystem.add_memory(
                        person=mejor_candidata,
                        mem_type=CognitiveMemorySystem.TYPE_MARRIAGE,
                        target_id=str(hombre.entity_id),
                        intensity=0.8,
                        valence=1,
                        context=context_type,
                        current_day=current_day,
                        pending=pending,
                    )
                    
                    # Aprendizaje post-matrimonio
                    for persona in [hombre, mejor_candidata]:
                        if hasattr(persona, 'get_motivation'):
                            pending.register_motivation_update(
                                persona.entity_id, "partnership", fw_cfg.success_reinforcement_rate
                            )
                            pending.register_motivation_update(
                                persona.entity_id, "independence", -fw_cfg.success_reinforcement_rate * 0.3
                            )
                    
                    estado = "Reconciliación" if es_ex else ("Flechazo" if flechazo else "Nuevo cortejo")
                    self.logger.debug(
                        "❤️ %s transaccional: %s y %s (recuerdos registrados, motivaciones ajustadas)",
                        estado,
                        hombre.entity_id,
                        mejor_candidata.entity_id,
                    )
                else:
                    # Mecánica de rechazo: Aumenta el estrés del rechazado
                    if hasattr(hombre, 'update_emotion'):
                        hombre.update_emotion("stress", 0.05)