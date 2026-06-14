"""Módulo responsable de la transición de estado hacia la gestación biológica."""

import random
import math
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class ConceptionSystem:
    """Gestiona la iniciación de la gestación basándose en probabilidad continua."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el motor de concepción vinculando la configuración central."""
        self.config = config
        self.logger = logging.getLogger("ConceptionSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa intentos de concepción utilizando el modelo exponencial continuo."""
        
        rep_cfg = self.config.reproduction
        
        # Transformamos la probabilidad base (anual) a tasa diaria pura
        daily_rate = rep_cfg.base_conception_chance / 365.0
        
        # Probabilidad base acumulada para el periodo delta_days (Integración de Poisson)
        base_prob_period = 1.0 - math.exp(-daily_rate * delta_days)

        for person in state.get_all_persons():
            # 1. Filtros de integridad referencial y de estado biológico
            if person.entity_id in pending.deaths or getattr(person, 'is_pregnant', False):
                continue

            # 2. Verificación de capacidad reproductiva y existencia de pareja
            if getattr(person, 'partner_id', None) and person.can_reproduce():
                partner = state.get_person_by_id(person.partner_id)
                
                # Blindaje: Garantizamos que la pareja existe, está viva y es fértil
                if partner and partner.entity_id not in pending.deaths and partner.can_reproduce():
                    
                    # 3. Modificador genético de fertilidad
                    # Promediamos la expresión del gen de fertilidad de ambos progenitores
                    fertility_modifier = (person.genome.fertility + partner.genome.fertility) / 2.0
                    
                    # Probabilidad final ajustada fenotípicamente
                    final_chance = base_prob_period * fertility_modifier
                    
                    if random.random() < final_chance:
                        # 4. Registro transaccional del nuevo estado en el búfer
                        pending.register_pregnancy_update(
                            person.entity_id, 
                            is_pregnant=True, 
                            pregnancy_days=0.0
                        )
                        self.logger.debug(f"Concepción iniciada para agente: {person.entity_id}")