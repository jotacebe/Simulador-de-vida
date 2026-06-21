"""Módulo responsable de la memoria explícita (episódica) e implícita (traumas)."""

import math
import logging
from typing import Any, Dict
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class CognitiveMemorySystem:
    """Procesa la impronta cognitiva, recuerdos específicos y desgaste psicológico.

    Combina el condicionamiento ambiental (traumas por hacinamiento) con la memoria 
    episódica (recordar compañeros o conflictos) para alterar el comportamiento.
    """

    # Tipos de memoria episódica
    TYPE_COMPANION = "companion"   
    TYPE_CONFLICT = "conflict"     
    TYPE_EXPERIENCE = "experience" 
    TYPE_EVENT = "event"           

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Actualiza el estado mental de todos los agentes vivos."""
        cog_cfg = self.config.cognition

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue

            # 1. ACCESO A LA MEMORIA (Diccionario base)
            mem = person.memory

            # =========================================================
            # PARTE A: MEMORIA IMPLÍCITA (Tus Traumas y Preferencias)
            # =========================================================
            temperament = getattr(person.genome, 'temperament', 0.5) if hasattr(person, 'genome') else 0.5
            adjusted_lambda = cog_cfg.base_forgetting_rate * (temperament + cog_cfg.temperament_modifier)
            decay_factor = math.exp(-adjusted_lambda * delta_days)

            local_pressure = context.get_local_pressure(person.x, person.y)
            
            trauma_overcrowding = mem.get("trauma_overcrowding", 0.0) * decay_factor
            if local_pressure > cog_cfg.overcrowding_threshold:
                trauma_overcrowding += (cog_cfg.overcrowding_impact * delta_days)

            trauma_sickness = mem.get("trauma_sickness", 0.0) * decay_factor
            if getattr(person, 'is_sick', False):
                trauma_sickness += (cog_cfg.sickness_impact * delta_days)

            preferred_sector = mem.get("preferred_sector", None)
            is_adult = getattr(person, 'is_adult', False)
            is_sick = getattr(person, 'is_sick', False)
            has_children = getattr(person, 'children_count', 0) > 0
            
            if is_adult and not is_sick and has_children:
                preferred_sector = (person.x // context.sector_size, person.y // context.sector_size)

            mem["trauma_overcrowding"] = min(cog_cfg.max_trauma_cap, trauma_overcrowding)
            mem["trauma_sickness"] = min(cog_cfg.max_trauma_cap, trauma_sickness)
            mem["rebellion_cooldown"] = max(0.0, mem.get("rebellion_cooldown", 0.0) - delta_days)
            mem["preferred_sector"] = preferred_sector

            # =========================================================
            # PARTE B: MEMORIA EXPLÍCITA (Recuerdos de personas/eventos)
            # =========================================================
            if "episodic" not in mem or not isinstance(mem["episodic"], dict):
                mem["episodic"] = {}
                
            episodic = mem["episodic"]
            keys_to_delete = []
            total_trauma_episodic = 0.0
            total_nostalgia = 0.0
            
            for mem_key, mem_data in episodic.items():
                # Aplicamos un olvido lineal a los recuerdos concretos
                mem_data['intensity'] -= 0.02 * delta_days
                
                if mem_data['intensity'] <= 0.05:
                    keys_to_delete.append(mem_key)
                else:
                    if mem_data['valence'] < 0:
                        total_trauma_episodic += mem_data['intensity']
                    else:
                        total_nostalgia += mem_data['intensity']

            for k in keys_to_delete:
                del episodic[k]

            # El estrés cognitivo afecta al Libre Albedrío (Punto 11)
            trauma_penalty = min(0.8, total_trauma_episodic * 0.15)
            nostalgia_buff = min(0.5, total_nostalgia * 0.1)
            mem["cognitive_stress"] = max(0.0, trauma_penalty - nostalgia_buff)

    # =========================================================
    # MÉTODOS ESTÁTICOS PARA USAR DESDE OTROS SISTEMAS
    # =========================================================
    @staticmethod
    def add_memory(person: Any, mem_type: str, target_id: str, intensity: float, valence: int) -> None:
        """Graba un suceso en el cerebro del agente."""
        if not hasattr(person, 'memory') or not isinstance(person.memory, dict):
            return
            
        if "episodic" not in person.memory or not isinstance(person.memory["episodic"], dict):
            person.memory["episodic"] = {}
            
        key = f"{mem_type}_{target_id}"
        episodic = person.memory["episodic"]
        
        if key in episodic:
            episodic[key]['intensity'] = min(1.0, episodic[key]['intensity'] + intensity)
            episodic[key]['valence'] = (episodic[key]['valence'] + valence) / 2.0
        else:
            episodic[key] = {
                'intensity': min(1.0, intensity),
                'valence': valence
            }

    @staticmethod
    def get_bias_towards(person: Any, target_id: str) -> float:
        """Calcula la afinidad hacia una persona o lugar basada en recuerdos pasados."""
        if not hasattr(person, 'memory') or not isinstance(person.memory.get("episodic"), dict):
            return 0.0
            
        episodic = person.memory["episodic"]
        bias = 0.0
        
        for mem_type in [CognitiveMemorySystem.TYPE_COMPANION, CognitiveMemorySystem.TYPE_CONFLICT, CognitiveMemorySystem.TYPE_EXPERIENCE]:
            key = f"{mem_type}_{target_id}"
            if key in episodic:
                bias += episodic[key]['intensity'] * episodic[key]['valence']
                
        return max(-1.0, min(1.0, bias))