"""Módulo responsable de la memoria explícita (episódica) e implícita (traumas).

Implementa un sistema de memoria transaccional avanzado que:
- Procesa traumas implícitos (hacinamiento, enfermedad, abandono, adopción)
- Gestiona memoria episódica con metadatos completos (fecha, refuerzos, contexto)
- Calcula estrés cognitivo basado en traumas y nostalgia
- Desarrolla preferencias espaciales
- Usa arquitectura transaccional (PendingChanges) para todas las modificaciones
- Se integra con todos los sistemas para generar recuerdos automáticamente

Todos los cambios se registran en el búfer transaccional y se aplican
atómicamente durante el commit, garantizando coherencia del estado.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, Optional

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext


class CognitiveMemorySystem:
    """Procesa la impronta cognitiva, recuerdos específicos y desgaste psicológico.

    Combina el condicionamiento ambiental (traumas) con la memoria episódica
    para alterar el comportamiento de forma transaccional y coherente.
    """

    # Tipos de memoria episódica
    TYPE_COMPANION = "companion"
    TYPE_CONFLICT = "conflict"
    TYPE_EXPERIENCE = "experience"
    TYPE_EVENT = "event"
    TYPE_MARRIAGE = "marriage"
    TYPE_CHILD = "child"
    TYPE_DEATH = "death"
    TYPE_ADOPTION = "adoption"
    TYPE_DIVORCE = "divorce"
    TYPE_DISEASE = "disease"
    TYPE_MIGRATION = "migration"

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema vinculándolo a la configuración centralizada.
        
        Args:
            config: Configuración maestra de la simulación.
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Actualiza el estado mental de todos los agentes vivos de forma transaccional.
        
        Args:
            state: Estado autoritativo del mundo.
            pending: Búfer transaccional donde se registran los cambios.
            delta_days: Duración del tick en días simulados.
            context: Contexto ambiental del tick.
        """
        cog_cfg = self.config.cognition

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue

            # =================================================================
            # PARTE A: MEMORIA IMPLÍCITA (Traumas y Preferencias)
            # =================================================================
            
            temperament = getattr(person.genome, 'temperament', 0.5) if hasattr(person, 'genome') else 0.5
            adjusted_lambda = cog_cfg.base_forgetting_rate * (temperament + cog_cfg.temperament_modifier)
            decay_factor = math.exp(-adjusted_lambda * delta_days)

            local_pressure = context.get_local_pressure(person.x, person.y)
            
            # TRAUMA POR HACINAMIENTO
            if person.entity_id in pending.memory_updates:
                old_trauma_overcrowding = pending.memory_updates[person.entity_id].get(
                    "trauma_overcrowding", person.memory.get("trauma_overcrowding", 0.0)
                )
            else:
                old_trauma_overcrowding = person.memory.get("trauma_overcrowding", 0.0)
            
            trauma_overcrowding = old_trauma_overcrowding * decay_factor
            if local_pressure > cog_cfg.overcrowding_threshold:
                trauma_overcrowding += (cog_cfg.overcrowding_impact * delta_days)
            
            # TRAUMA POR ENFERMEDAD
            if person.entity_id in pending.memory_updates:
                old_trauma_sickness = pending.memory_updates[person.entity_id].get(
                    "trauma_sickness", person.memory.get("trauma_sickness", 0.0)
                )
            else:
                old_trauma_sickness = person.memory.get("trauma_sickness", 0.0)
            
            trauma_sickness = old_trauma_sickness * decay_factor
            if getattr(person, 'is_sick', False):
                trauma_sickness += (cog_cfg.sickness_impact * delta_days)
            
            # TRAUMA POR ADOPCIÓN
            if person.entity_id in pending.memory_updates:
                old_trauma_adoption = pending.memory_updates[person.entity_id].get(
                    "trauma_adoption", person.memory.get("trauma_adoption", 0.0)
                )
            else:
                old_trauma_adoption = person.memory.get("trauma_adoption", 0.0)
            
            trauma_adoption = old_trauma_adoption * decay_factor
            
            if old_trauma_adoption > 0.0:
                delta_trauma = old_trauma_adoption - trauma_adoption
                pending.register_emotion_update(person.entity_id, "stress", -delta_trauma * 0.6)
                pending.register_emotion_update(person.entity_id, "happiness", delta_trauma * 0.5)
            
            # TRAUMA POR ABANDONO
            if person.entity_id in pending.memory_updates:
                old_trauma_abandonment = pending.memory_updates[person.entity_id].get(
                    "trauma_abandonment", person.memory.get("trauma_abandonment", 0.0)
                )
            else:
                old_trauma_abandonment = person.memory.get("trauma_abandonment", 0.0)
            
            trauma_abandonment = old_trauma_abandonment * decay_factor
            
            # PREFERENCIA ESPACIAL
            preferred_sector = person.memory.get("preferred_sector", None)
            is_adult = getattr(person, 'is_adult', False)
            is_sick = getattr(person, 'is_sick', False)
            has_children = getattr(person, 'children_count', 0) > 0
            is_senior = getattr(person, 'is_senior', False)
            
            if (is_adult and not is_sick and has_children) or is_senior:
                preferred_sector = (person.x // context.sector_size, person.y // context.sector_size)
            
            rebellion_cooldown = max(0.0, person.memory.get("rebellion_cooldown", 0.0) - delta_days)
            
            # REGISTRAR CAMBIOS DE MEMORIA IMPLÍCITA
            pending.register_memory_update(person.entity_id, "trauma_overcrowding", min(cog_cfg.max_trauma_cap, trauma_overcrowding))
            pending.register_memory_update(person.entity_id, "trauma_sickness", min(cog_cfg.max_trauma_cap, trauma_sickness))
            pending.register_memory_update(person.entity_id, "trauma_adoption", min(cog_cfg.max_trauma_cap, trauma_adoption))
            pending.register_memory_update(person.entity_id, "trauma_abandonment", min(cog_cfg.max_trauma_cap, trauma_abandonment))
            pending.register_memory_update(person.entity_id, "rebellion_cooldown", rebellion_cooldown)
            pending.register_memory_update(person.entity_id, "preferred_sector", preferred_sector)

            # =================================================================
            # PARTE B: MEMORIA EXPLÍCITA (Recuerdos episódicos con metadatos)
            # =================================================================
            if "episodic" not in person.memory or not isinstance(person.memory["episodic"], dict):
                episodic = {}
            else:
                episodic = person.memory["episodic"].copy()
                
            keys_to_delete = []
            total_trauma_episodic = 0.0
            total_nostalgia = 0.0
            
            current_day = getattr(state, 'world_days_elapsed', 0.0)
            
            for mem_key, mem_data in episodic.items():
                # Asegurar que el recuerdo tiene todos los metadatos (compatibilidad hacia atrás)
                if 'created_day' not in mem_data:
                    mem_data['created_day'] = current_day
                if 'last_reinforced_day' not in mem_data:
                    mem_data['last_reinforced_day'] = current_day
                if 'times_reinforced' not in mem_data:
                    mem_data['times_reinforced'] = 1
                if 'context' not in mem_data:
                    mem_data['context'] = "general"
                
                # Decaimiento exponencial con consolidación
                # Eventos repetidos o traumáticos se olvidan más lento
                emotional_importance = abs(mem_data.get('valence', 0)) * cog_cfg.emotional_importance_factor
                reinforcement_bonus = min(0.5, mem_data.get('times_reinforced', 1) * 0.05)
                effective_forgetting_rate = cog_cfg.episodic_forgetting_rate * (1.0 - emotional_importance - reinforcement_bonus)
                decay = math.exp(-effective_forgetting_rate * delta_days)
                
                mem_data['intensity'] *= decay
                
                if mem_data['intensity'] <= cog_cfg.episodic_min_intensity:
                    keys_to_delete.append(mem_key)
                else:
                    if mem_data.get('valence', 0) < 0:
                        total_trauma_episodic += mem_data['intensity']
                    else:
                        total_nostalgia += mem_data['intensity']

            for k in keys_to_delete:
                del episodic[k]
            
            if len(episodic) > cog_cfg.max_episodic_memories:
                sorted_memories = sorted(episodic.items(), key=lambda x: x[1]['intensity'])
                to_remove = len(episodic) - cog_cfg.max_episodic_memories
                for i in range(to_remove):
                    del episodic[sorted_memories[i][0]]
            
            pending.register_memory_update(person.entity_id, "episodic", episodic)

            trauma_penalty = min(cog_cfg.max_cognitive_stress, total_trauma_episodic * cog_cfg.trauma_to_stress_factor)
            nostalgia_buff = min(cog_cfg.max_cognitive_stress, total_nostalgia * cog_cfg.nostalgia_buffer_factor)
            cognitive_stress = max(0.0, trauma_penalty - nostalgia_buff)
            
            pending.register_memory_update(person.entity_id, "cognitive_stress", cognitive_stress)

    # =====================================================================
    # MÉTODOS ESTÁTICOS PARA USAR DESDE OTROS SISTEMAS
    # =====================================================================
    @staticmethod
    def add_memory(
        person: Any,
        mem_type: str,
        target_id: str,
        intensity: float,
        valence: int,
        context: str = "general",
        current_day: float = 0.0,
        pending: Optional[PendingChanges] = None,
    ) -> None:
        """Graba un suceso en el cerebro del agente con metadatos completos.
        
        Args:
            person: Entidad que recordará el suceso.
            mem_type: Tipo de memoria (TYPE_COMPANION, TYPE_CONFLICT, etc.).
            target_id: ID del objetivo del recuerdo.
            intensity: Intensidad inicial del recuerdo [0.0, 1.0].
            valence: Valor emocional (-1 negativo, 0 neutro, 1 positivo).
            context: Contexto del recuerdo (ej: "infancia", "matrimonio", "guerra").
            current_day: Día simulado en que ocurre el evento.
            pending: Búfer transaccional (si es None, se muta directamente - legacy).
        """
        if not hasattr(person, 'memory') or not isinstance(person.memory, dict):
            return
            
        if "episodic" not in person.memory or not isinstance(person.memory["episodic"], dict):
            person.memory["episodic"] = {}
            
        key = f"{mem_type}_{target_id}"
        episodic = person.memory["episodic"]
        
        if key in episodic:
            # Reforzar recuerdo existente
            episodic[key]['intensity'] = min(1.0, episodic[key]['intensity'] + intensity)
            episodic[key]['valence'] = (episodic[key]['valence'] + valence) / 2.0
            episodic[key]['last_reinforced_day'] = current_day
            episodic[key]['times_reinforced'] += 1
        else:
            # Crear nuevo recuerdo con metadatos completos
            episodic[key] = {
                'intensity': min(1.0, intensity),
                'valence': valence,
                'created_day': current_day,
                'last_reinforced_day': current_day,
                'times_reinforced': 1,
                'context': context,
            }
        
        if pending is not None:
            pending.register_memory_update(person.entity_id, "episodic", episodic)

    @staticmethod
    def get_bias_towards(person: Any, target_id: str) -> float:
        """Calcula la afinidad hacia una persona o lugar basada en recuerdos pasados.
        
        Args:
            person: Entidad cuyo sesgo se calcula.
            target_id: ID del objetivo.
            
        Returns:
            Sesgo en rango [-1.0, 1.0] (negativo = aversión, positivo = afinidad).
        """
        if not hasattr(person, 'memory') or not isinstance(person.memory.get("episodic"), dict):
            return 0.0
            
        episodic = person.memory["episodic"]
        bias = 0.0
        
        for mem_type in [
            CognitiveMemorySystem.TYPE_COMPANION,
            CognitiveMemorySystem.TYPE_CONFLICT,
            CognitiveMemorySystem.TYPE_EXPERIENCE,
            CognitiveMemorySystem.TYPE_MARRIAGE,
            CognitiveMemorySystem.TYPE_CHILD,
            CognitiveMemorySystem.TYPE_DEATH,
            CognitiveMemorySystem.TYPE_ADOPTION,
            CognitiveMemorySystem.TYPE_DIVORCE,
            CognitiveMemorySystem.TYPE_DISEASE,
            CognitiveMemorySystem.TYPE_MIGRATION,
        ]:
            key = f"{mem_type}_{target_id}"
            if key in episodic:
                bias += episodic[key]['intensity'] * episodic[key]['valence']
                
        return max(-1.0, min(1.0, bias))