"""Módulo responsable de gestionar el cortejo y emparejamientos directos."""

import random
import math
import logging
from typing import Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class MarriageSystem:
    """Gestiona el cortejo y matrimonios espontáneos de forma transaccional."""

    def __init__(self, config: SimulationConfig, ancestry_queries: Any) -> None:
        """Inicializa el sistema vinculándolo a la genealogía y configuración."""
        self.config = config
        self.ancestry_queries = ancestry_queries
        self.logger = logging.getLogger("MarriageSystem")

    def _calcular_compatibilidad(self, p1: Any, p2: Any) -> float:
        """Evalúa la afinidad fenotípica y demográfica mediante genética."""
        soc1, soc2 = p1.genome.sociability, p2.genome.sociability
        temp1, temp2 = p1.genome.temperament, p2.genome.temperament
        
        afinidad = 1.0 - ((abs(soc1 - soc2) + abs(temp1 - temp2)) / 2.0)
        
        # Corrección de Bug: Transformamos la diferencia a años humanos para el cálculo
        dif_edad_dias = abs(p1.age - p2.age)
        dif_edad_anios = dif_edad_dias / 365.0
        
        factor_edad = max(0.2, 1.0 - (dif_edad_anios * 0.02)) if dif_edad_anios > 15.0 else 1.0
        return afinidad * factor_edad

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa las intenciones de emparejamiento de los solteros en el tick actual."""
        rel_cfg = self.config.relationships
        all_persons = state.get_all_persons()
        
        # Filtros de solteros vivos en edad de vinculación
        solteros = [p for p in all_persons if p.age >= rel_cfg.min_marriage_age_days 
                    and getattr(p, 'marital_status', 'soltero') != "casado" 
                    and p.entity_id not in pending.deaths]
        
        solteros_m = [p for p in solteros if getattr(p, 'gender', '') == "M"]
        solteros_f = [p for p in solteros if getattr(p, 'gender', '') == "F"]

        if not solteros_m or not solteros_f: 
            return
        
        # Integración continua para probabilidad utilizando el modelo de Poisson
        total_marriage_chance = 1.0 - math.exp(-rel_cfg.base_marriage_chance * delta_days)
        total_flechazo = 1.0 - math.exp(-rel_cfg.love_at_first_sight_chance * delta_days)
        
        random.shuffle(solteros_m)
        comprometidos_hoy = set()

        for hombre in solteros_m:
            mejor_candidata, mejor_score, flechazo = None, -1.0, False

            for mujer in solteros_f:
                if mujer.entity_id in comprometidos_hoy: 
                    continue
                    
                # Validación espacial
                if abs(hombre.x - mujer.x) > rel_cfg.courtship_radius or \
                   abs(hombre.y - mujer.y) > rel_cfg.courtship_radius: 
                    continue
                    
                # Integración Arquitectónica: Delegamos al subsistema de Genealogía
                if self.ancestry_queries.is_forbidden_marriage(hombre.entity_id, mujer.entity_id):
                    continue

                # Probabilidad estocástica de flechazo inmediato
                if random.random() < total_flechazo:
                    mejor_candidata, flechazo = mujer, True
                    break

                # Evaluación algorítmica de genotipos
                score = self._calcular_compatibilidad(hombre, mujer)
                if score > mejor_score:
                    mejor_score, mejor_candidata = score, mujer

            if mejor_candidata:
                chance = 1.0 if flechazo else (total_marriage_chance * mejor_score)
                if random.random() < chance:
                    pending.register_marriage(hombre.entity_id, mejor_candidata.entity_id)
                    comprometidos_hoy.add(mejor_candidata.entity_id)
                    self.logger.debug(f"Cortejo exitoso registrado: {hombre.entity_id} y {mejor_candidata.entity_id}")