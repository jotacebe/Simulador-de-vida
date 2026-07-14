"""Motor de experiencias relacionales.

Traduce eventos del mundo (cuidado, nacimiento, competencia, traición) 
en cambios de variables emocionales, modulados por la personalidad de los agentes.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, Optional

from core.config.simulation_config import SimulationConfig
from systems.relationships.relationship_model import (
    Relationship,
    RelationshipStatus,
    RelationshipEvent,
    RelationshipEventType,
    RelationshipMemory,
)


class RelationshipExperienceEngine:
    """Procesa eventos relacionales y actualiza las variables emocionales."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configuración base de impacto por tipo de evento
        # Formato: {EventType: {'trust': X, 'attraction': Y, 'conflict': Z, ...}}
        self.base_impacts: Dict[RelationshipEventType, Dict[str, float]] = {
            RelationshipEventType.CARE: {
                'trust': 0.15, 'attachment': 0.10, 'respect': 0.05, 'conflict': -0.05
            },
            RelationshipEventType.COOPERATION: {
                'trust': 0.10, 'respect': 0.10, 'attachment': 0.05
            },
            RelationshipEventType.SHARE_RESOURCE: {
                'trust': 0.08, 'respect': 0.05, 'attachment': 0.03
            },
            RelationshipEventType.INTIMACY: {
                'attraction': 0.15, 'intimacy': 0.20, 'attachment': 0.10, 'trust': 0.05
            },
            RelationshipEventType.RECONCILIATION: {
                'trust': 0.10, 'conflict': -0.20, 'respect': 0.05
            },
            RelationshipEventType.COMPETITION: {
                'conflict': 0.15, 'trust': -0.10, 'respect': -0.05
            },
            RelationshipEventType.BETRAYAL: {
                'trust': -0.30, 'conflict': 0.25, 'respect': -0.20, 'attachment': -0.10
            },
            RelationshipEventType.CONFLICT: {
                'conflict': 0.20, 'trust': -0.15, 'respect': -0.10
            },
            RelationshipEventType.NEGLECT: {
                'trust': -0.10, 'attachment': -0.10, 'conflict': 0.05
            },
            RelationshipEventType.BIRTH: {
                'attachment': 0.25, 'commitment': 0.20, 'trust': 0.10
            },
            RelationshipEventType.CHILD_DEATH: {
                'conflict': 0.15, 'attachment': 0.10, 'trust': -0.05  # Estrés compartido, posible culpa
            },
            RelationshipEventType.PARTNER_DEATH: {
                'attachment': 0.30, 'conflict': 0.0  # El apego se congela o se idealiza
            },
            RelationshipEventType.COHABITATION_START: {
                'commitment': 0.15, 'intimacy': 0.10, 'attachment': 0.10
            },
            RelationshipEventType.COHABITATION_END: {
                'commitment': -0.20, 'conflict': 0.10, 'trust': -0.10
            }
        }

    def process_event(
        self,
        event: RelationshipEvent,
        agent_a: Any,
        agent_b: Optional[Any],
        current_day: float,
    ) -> None:
        """Procesa un evento relacional y actualiza la relación entre A y B."""
        if agent_b is None:
            return  # Eventos unarios no modifican relaciones (por ahora)

        # 1. Obtener o crear la relación
        rel = agent_a.get_relationship_with(agent_b.entity_id)
        if not rel:
            # Crear relación inicial si no existe
            rel = Relationship(
                partner_id=agent_b.entity_id,
                status=RelationshipStatus.UNKNOWN,
                start_date=current_day,
                last_interaction=current_day,
                affinity=0.5,
            )
            agent_a._relationships.append(rel)
            
            # Crear relación inversa
            rel_reverse = Relationship(
                partner_id=agent_a.entity_id,
                status=RelationshipStatus.UNKNOWN,
                start_date=current_day,
                last_interaction=current_day,
                affinity=0.5,
            )
            agent_b._relationships.append(rel_reverse)

        # 2. Calcular impactos modulados por personalidad
        impacts = self._calculate_modulated_impacts(event, agent_a, agent_b)

        # 3. Aplicar cambios a las variables emocionales (clamp 0-100)
        for var, delta in impacts.items():
            if hasattr(rel, var):
                current_val = getattr(rel, var)
                new_val = max(0.0, min(100.0, current_val + (delta * 100.0))) # Escalamos a 0-100
                setattr(rel, var, new_val)

        # 4. Registrar el recuerdo en el historial
        valence = 1 if event.event_type in [
            RelationshipEventType.CARE, RelationshipEventType.COOPERATION,
            RelationshipEventType.SHARE_RESOURCE, RelationshipEventType.INTIMACY,
            RelationshipEventType.RECONCILIATION, RelationshipEventType.BIRTH
        ] else -1 if event.event_type in [
            RelationshipEventType.BETRAYAL, RelationshipEventType.CONFLICT,
            RelationshipEventType.NEGLECT, RelationshipEventType.CHILD_DEATH
        ] else 0

        memory = RelationshipMemory(
            event_type=event.event_type.value,
            intensity=event.intensity,
            day=current_day,
            valence=valence,
            context=event.context
        )
        rel.memories.append(memory)
        rel.last_interaction = current_day
        
        # También añadir al historial legacy para compatibilidad
        rel.add_event(current_day, f"EVENT:{event.event_type.value} (int:{event.intensity:.2f})")

        self.logger.debug(
            "🧠 Experiencia: Agente %s y %s | Evento: %s | Impacto: %s",
            agent_a.entity_id, agent_b.entity_id, event.event_type.value, 
            {k: f"{v:+.2f}" for k, v in impacts.items() if abs(v) > 0.01}
        )

    def _calculate_modulated_impacts(
        self,
        event: RelationshipEvent,
        agent_a: Any,
        agent_b: Any,
    ) -> Dict[str, float]:
        """Calcula el impacto final de un evento, modulado por rasgos de personalidad."""
        base = self.base_impacts.get(event.event_type, {})
        if not base:
            return {}

        impacts = {}
        
        # Obtener rasgos (con valores por defecto si no existen)
        # Asumimos que el Genome o las motivaciones tienen estos valores entre 0.0 y 1.0 (o 0-2.0)
        sociability_a = getattr(agent_a.genome, 'sociability', 1.0) / 2.0
        independence_a = getattr(agent_a, 'motivations', {}).get('independence', 0.5)
        temperament_a = getattr(agent_a.genome, 'temperament', 1.0) / 2.0
        
        # Para el agente B (el que recibe la acción, ej: el cuidado)
        sociability_b = getattr(agent_b.genome, 'sociability', 1.0) / 2.0
        independence_b = getattr(agent_b, 'motivations', {}).get('independence', 0.5)

        for var, base_delta in base.items():
            delta = base_delta * event.intensity
            
            # --- MODULADORES ESPECÍFICOS POR TIPO DE EVENTO ---
            
            if event.event_type == RelationshipEventType.CARE:
                # Si el receptor (B) es muy independiente, valora menos el cuidado
                delta *= (1.0 - (independence_b * 0.5))
                # Si el dador (A) es sociable, el cuidado es más genuino/efectivo
                delta *= (1.0 + (sociability_a * 0.3))
            
            elif event.event_type == RelationshipEventType.COMPETITION:
                # Temperamento alto = más conflicto generado
                if var == 'conflict':
                    delta *= (1.0 + (temperament_a * 0.5))
            
            elif event.event_type == RelationshipEventType.BETRAYAL:
                # La traición duele más si la sociabilidad/confianza base era alta
                if var == 'trust':
                    delta *= 1.5 
            
            elif event.event_type == RelationshipEventType.BIRTH:
                # El nacimiento une más a personas con baja independencia (más familiares)
                if var in ['attachment', 'commitment']:
                    delta *= (1.0 + ((1.0 - independence_a) * 0.4))

            impacts[var] = delta

        return impacts