"""
Ruta: systems/reproduction/conception_system.py
Responsabilidad: Evaluar exclusivamente la "chispa" inicial. Revisa parejas fértiles 
                 y calcula la probabilidad de concepción normalizada por delta_days.
"""
import random
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext

class ConceptionSystem:
    def __init__(self, config):
        self.logger = logging.getLogger("ConceptionSystem")
        self.config = config

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        """Procesa concepciones utilizando únicamente días como métrica temporal continua."""
        
        cfg = getattr(self.config, 'reproduction', {})
        if isinstance(cfg, dict):
            base_conception = cfg.get("base_conception_chance", 0.15)
        else:
            base_conception = getattr(cfg, "base_conception_chance", 0.15)
        
        # Obtenemos la tasa diaria matemática
        daily_base_conception_chance = base_conception / 365.0

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue

            # Si ya está embarazada, de la gestación se encarga otro sistema
            if person.is_pregnant:
                continue

            # CONCEPCIÓN
            if person.can_reproduce() and person.partner_id:
                partner = state.get_person_by_id(person.partner_id)
                
                if partner and partner.can_reproduce():
                    # Probabilidad según los días transcurridos
                    conception_chance_for_period = daily_base_conception_chance * delta_days
                    
                    # Modificador por ADN fértil
                    fertility_modifier = (person.genome.fertility + partner.genome.fertility) / 2.0
                    final_chance = conception_chance_for_period * fertility_modifier

                    if random.random() < final_chance:
                        # Concepción exitosa, lanzamos la señal al búfer
                        pending.register_pregnancy_update(person.entity_id, is_pregnant=True, pregnancy_days=0.0)
                        self.logger.debug(f"Concepción exitosa: {person.entity_id}")