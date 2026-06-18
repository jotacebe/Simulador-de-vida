"""Módulo responsable de gestionar el cortejo y los matrimonios de forma transaccional.

Evita duplicados de forma matemática y calcula compatibilidades basándose en
los rasgos fenotípicos dinámicos (emociones) en lugar del genoma estático.
"""

import logging
import math
import random
from typing import Any, Set

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext


class MarriageSystem:
    """Gestiona el mercado de solteros, rechazos y matrimonios espontáneos."""

    def __init__(self, config: SimulationConfig, ancestry_queries: Any) -> None:
        self.config = config
        self.ancestry_queries = ancestry_queries
        self.logger = logging.getLogger(self.__class__.__name__)

    def _calcular_compatibilidad(self, p1: Any, p2: Any) -> float:
        """Evalúa la afinidad demográfica y el estado emocional actual."""
        
        # FIX: Usamos el fenotipo dinámico (influye el estrés, trauma y felicidad)
        soc1, soc2 = p1.effective_sociability, p2.effective_sociability
        temp1, temp2 = p1.effective_temperament, p2.effective_temperament
        
        afinidad = 1.0 - ((abs(soc1 - soc2) + abs(temp1 - temp2)) / 2.0)
        
        dif_edad_dias = abs(p1.age - p2.age)
        dif_edad_anios = dif_edad_dias / 365.0
        
        factor_edad = max(0.2, 1.0 - (dif_edad_anios * 0.02)) if dif_edad_anios > 15.0 else 1.0
        return afinidad * factor_edad

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa las intenciones de emparejamiento evaluando afinidad y rechazos."""
        rel_cfg = self.config.relationships
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

        for hombre in solteros_m:
            if hombre.entity_id in comprometidos_hoy:
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
                if score > mejor_score:
                    mejor_score, mejor_candidata = score, mujer

            if mejor_candidata:
                # Sistema de Reconciliación (¿Es un ex?)
                historial = hombre.memory.get("ex_partners", [])
                es_ex = mejor_candidata.entity_id in historial
                
                # Si es un ex, requieren mucha más afinidad para volver
                umbral_requerido = 0.6 if es_ex else 0.4
                chance = 1.0 if flechazo else (total_marriage_chance * mejor_score)
                
                if mejor_score >= umbral_requerido and random.random() < chance:
                    pending.register_marriage(hombre.entity_id, mejor_candidata.entity_id)
                    comprometidos_hoy.add(hombre.entity_id)
                    comprometidos_hoy.add(mejor_candidata.entity_id)
                    
                    estado = "Reconciliación" if es_ex else "Nuevo cortejo"
                    self.logger.debug(f"❤️ {estado} transaccional: {hombre.entity_id} y {mejor_candidata.entity_id}")
                else:
                    # Mecánica de rechazo: Aumenta el estrés del rechazado
                    if hasattr(hombre, 'update_emotion'):
                        hombre.update_emotion("stress", 0.05)