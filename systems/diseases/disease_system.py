"""Módulo responsable de la gestión epidemiológica y evolución de patógenos.

Implementa un modelo de propagación espacial donde las cepas mutan intra-hospedador,
se contagian a vecinos basándose en hacinamiento, y son combatidas por la
inmunidad adquirida (historial de anticuerpos) de cada individuo.
"""

import random
import math
import logging
from collections import defaultdict
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig
from systems.diseases.pathogen import Pathogen

class DiseaseSystem:
    """Motor epidemiológico espacial (Variantes, Inmunidad y Contagio focal)."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        
        dis_cfg = self.config.diseases
        sector_size = self.config.environment.sector_size
        
        # Mapeo espacial de la carga viral en el tick actual
        # Sector (X, Y) -> Lista de patógenos presentes en el aire/ambiente
        pathogen_map = defaultdict(list)

        # =================================================================
        # FASE 1: DESARROLLO INTRA-HOSPEDADOR Y LIBERACIÓN AL ENTORNO
        # =================================================================
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths: continue
            
            for path_id, pathogen in list(person.active_pathogens.items()):
                # 1. Intento de Recuperación mediado por Inmunidad Adquirida
                total_immunity = person.get_specific_immunity(pathogen.family)
                
                # A mayor virulencia, menor es la tasa efectiva de recuperación
                daily_recovery_rate = (dis_cfg.base_recovery_chance * total_immunity) / pathogen.virulence
                recovery_chance = 1.0 - math.exp(-daily_recovery_rate * delta_days)
                
                if random.random() < recovery_chance:
                    pending.register_recovery(person.entity_id, path_id)
                else:
                    # 2. Persistencia y Propagación
                    # El agente sigue enfermo, así que contamina su sector
                    sector = (person.x // sector_size, person.y // sector_size)
                    pathogen_map[sector].append(pathogen)
                    
                    # 3. Riesgo de Mutación (Deriva genética de la cepa)
                    mutation_chance = 0.005 * delta_days # Probabilidad base de mutación
                    if random.random() < mutation_chance:
                        new_variant = pathogen.mutate()
                        # El huésped se auto-infecta con la variante que acaba de gestar
                        pending.register_infection(person.entity_id, new_variant)
                        self.logger.debug(f"🦠 Mutación detectada: {new_variant.pathogen_id} en Agente {person.entity_id}")

        # =================================================================
        # FASE 2: CONTAGIOS LOCALES (R0 Espacial) Y BROTES ESPONTÁNEOS
        # =================================================================
        for person in state.get_all_persons():
            if person.entity_id in pending.deaths: continue
            
            sector = (person.x // sector_size, person.y // sector_size)
            local_pathogens = pathogen_map.get(sector, [])
            
            # A. Contagio cruzado por contacto con la carga viral del sector
            for pathogen in local_pathogens:
                # Si ya tiene esta cepa exacta, el cuerpo no se reinfecta de lo mismo al momento
                if pathogen.pathogen_id in person.active_pathogens:
                    continue 
                    
                total_immunity = person.get_specific_immunity(pathogen.family)
                crowding_pressure = context.get_local_pressure(person.x, person.y)
                
                # Tasa emergente: R0 ajustado por hacinamiento y defensas del huésped
                daily_transmission_rate = (pathogen.transmission * max(1.0, crowding_pressure)) / max(0.1, total_immunity)
                infection_chance = 1.0 - math.exp(-daily_transmission_rate * delta_days)
                
                if random.random() < infection_chance:
                    pending.register_infection(person.entity_id, pathogen)
            
            # B. Zoonosis o Brote Espontáneo (Paciente Cero)
            # Para evitar que el mundo se quede sin virus si todos sanan
            outbreak_chance = 1.0 - math.exp(-(dis_cfg.base_outbreak_chance / 100.0) * delta_days)
            if random.random() < outbreak_chance:
                familia_random = random.choice(["Influenza", "Coronavirus", "Poxvirus", "Bacteriofago_X"])
                patient_zero_virus = Pathogen(familia_random, variant_id=1, virulence=1.0, transmission=0.15, lethality=0.1)
                
                pending.register_infection(person.entity_id, patient_zero_virus)
                self.logger.info(f"🚨 Brote Epidémico: {patient_zero_virus.pathogen_id} ha surgido en Agente {person.entity_id}")