"""
Ruta: systems/diseases/disease_system.py
Responsabilidad: Gestionar contagios y recuperaciones de forma probabilística 
                 y transaccional, utilizando tasas diarias continuas y aplicando
                 presión de selección epidemiológica (Inmunidad).
"""
import random
import math
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext

class DiseaseSystem:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("DiseaseSystem")

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        # Extraemos de 'diseases' según la configuración centralizada
        cfg = getattr(state.config, 'diseases', {})
        
        # Transformamos las probabilidades base a tasas diarias puras
        base_transmission_rate = cfg.get("base_transmission_chance", 0.18) / 30.0
        base_recovery_rate = cfg.get("base_recovery_chance", 0.15) / 30.0

        for person in state.get_all_persons():
            # Si la entidad ya está marcada para morir en este tick, no gastamos ciclos en ella
            if person.entity_id in pending.deaths:
                continue

            # Extracción del gen de inmunidad del individuo
            immunity = person.genome.immunity

            if person.is_sick:
                # 1. SELECCIÓN NATURAL (Recuperación): 
                # A mayor inmunidad genética, mayor es la tasa diaria de recuperación.
                daily_recovery_rate = base_recovery_rate * immunity
                
                # Probabilidad exacta acumulada en el periodo delta_days (Modelo Poisson/Exponencial)
                # Protege al sistema de errores de precisión con floats en ticks parciales.
                total_recovery_chance = 1.0 - math.exp(-daily_recovery_rate * delta_days)

                if random.random() < total_recovery_chance:
                    pending.register_recovery(person.entity_id)
            
            else:
                # 2. SELECCIÓN NATURAL (Contagio):
                # La tasa de contagio es inversamente proporcional a la inmunidad.
                # Ponemos un suelo de 0.1 para evitar una división por cero si la genética colapsa.
                daily_contagion_rate = base_transmission_rate / max(0.1, immunity)
                
                # Probabilidad exacta acumulada en el periodo delta_days
                total_contagion_chance = 1.0 - math.exp(-daily_contagion_rate * delta_days)
                
                if random.random() < total_contagion_chance:
                    pending.register_infection(person.entity_id)