"""
Ruta: systems/environment/epidemiological_system.py
Responsabilidad: Conectar el EpidemiologicalMap con los agentes.
"""
import random
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

# (Nota: Ya no necesitamos importar EpidemiologicalMap aquí porque solo usamos la instancia que viene en el WorldState)

class EpidemiologicalSystem:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("EpidemiologicalSystem")
        self.base_transmission_rate = 0.15 

    def process(self, state: WorldState, pending: PendingChanges, delta_days: int) -> None:
        
        # A) Acceso limpio y directo (WorldState ya garantiza su existencia)
        ep_map = state.epidemiological_map
        all_persons = state.get_all_persons()

        # B) PROPAGACIÓN: Los enfermos dejan rastro
        for person in all_persons:
            if person.entity_id in pending.deaths: 
                continue
            
            # Uso estricto de la API (adiós a los getattr)
            if person.is_sick:
                ep_map.add_viral_load(person.x, person.y, amount=0.5)

        # C) CONTAGIO: El mapa afecta a los sanos
        for person in all_persons:
            if person.entity_id in pending.deaths: 
                continue
            
            # Si ya está enfermo, lo ignoramos
            if person.is_sick: 
                continue 

            viral_load = ep_map.get_viral_load(person.x, person.y)
            
            if viral_load > 0.1:
                risk = viral_load * self.base_transmission_rate
                if random.random() < risk:
                    # Uso directo de la API del búfer de cambios
                    pending.register_infection(person.entity_id)
                    self.logger.debug(f"Agente {person.entity_id} registrado para infección por rastro viral ambiental.")

        # D) DECAIMIENTO: El virus no es eterno
        ep_map.decay_viral_load(factor=0.90)