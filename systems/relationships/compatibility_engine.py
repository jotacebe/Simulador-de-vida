"""Motor de compatibilidad multifactorial para relaciones sociales.

Integra orientación Kinsey, afinidad genética/emocional, distancia,
edad, recuerdos compartidos y modificadores de libre albedrío.

Este motor es el núcleo del sistema de relaciones: calcula la puntuación
de compatibilidad entre dos agentes, que determina si pueden iniciar
una relación y cómo evoluciona con el tiempo.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext
from systems.relationships.relationship_model import (
    RelationshipStatus,
    is_orientation_compatible,
)


class CompatibilityEngine:
    """Calcula puntuaciones de compatibilidad entre dos agentes.
    
    Este sistema se ejecuta en cada tick para precalcular afinidades
    entre agentes cercanos, que luego usa RelationshipManager para
    decidir transiciones de estado.
    """

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.rel_cfg = config.relationships
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Fase de precalculación de compatibilidades.
        
        En esta fase no se modifican relaciones, solo se precalculan
        afinidades para que RelationshipManager las use después.
        """
        # Este sistema actúa como helper de RelationshipManager
        # No necesita lógica propia en process()
        pass

    def calculate_compatibility(
        self,
        p1: Any,
        p2: Any,
        free_will_boost: float = 0.0,
    ) -> float:
        """Calcula compatibilidad [0.0, 1.0] entre dos personas.
        
        Factores considerados:
        1. Alineación de orientación sexual (filtro duro)
        2. Proximidad de edad (preferencia)
        3. Distancia física (oportunidad)
        4. Afinidad base (personalidad + emociones + recuerdos)
        5. Boost de libre albedrío (impulsos anómalos)
        
        Args:
            p1: Primera persona.
            p2: Segunda persona.
            free_will_boost: Modificador por libre albedrío [0.0, 1.0].
            
        Returns:
            Puntuación de compatibilidad [0.0, 1.0].
        """
        cfg = self.rel_cfg
        
        # 1. Alineación de orientación (filtro duro)
        orientation_score = is_orientation_compatible(
            p1.sexual_orientation,
            p2.sexual_orientation,
            tolerance=cfg.orientation_tolerance,
        )
        if orientation_score <= 0.0:
            return 0.0
        
        # 2. Proximidad de edad
        age_diff_years = abs(p1.age - p2.age) / 365.0
        age_score = max(0.0, 1.0 - (age_diff_years / 20.0))
        
        # 3. Distancia física
        distance = math.hypot(p1.x - p2.x, p1.y - p2.y)
        distance_score = max(0.0, 1.0 - (distance / 50.0))
        
        # 4. Afinidad base (personalidad + emociones + recuerdos)
        affinity = self._calculate_base_affinity(p1, p2)
        
        # Combinar con pesos configurables
        raw_score = (
            affinity * cfg.affinity_weight +
            age_score * cfg.age_weight +
            distance_score * cfg.distance_weight
        )
        
        # Aplicar filtro de orientación
        base_compatibility = raw_score * orientation_score
        
        # Aplicar libre albedrío (puede generar relaciones "no establecidas")
        final_score = min(1.0, base_compatibility + free_will_boost)
        
        return max(0.0, final_score)

    def _calculate_base_affinity(self, p1: Any, p2: Any) -> float:
        """Afinidad basada en rasgos dinámicos y memoria compartida.
        
        Factores:
        - Similitud en sociabilidad
        - Complementariedad en temperamento
        - Bonus por recuerdos positivos compartidos
        - Penalización por recuerdos negativos
        """
        # Similitud en sociabilidad
        soc_diff = abs(p1.effective_sociability - p2.effective_sociability)
        soc_score = max(0.0, 1.0 - (soc_diff / 2.0))
        
        # Complementariedad en temperamento
        temp_diff = abs(p1.effective_temperament - p2.effective_temperament)
        temp_score = min(1.0, temp_diff / 1.5)
        
        base = (soc_score * 0.5) + (temp_score * 0.5)
        
        # Bonus/penalización por recuerdos compartidos
        if hasattr(p1, 'memory') and isinstance(p1.memory, dict):
            episodic = p1.memory.get('episodic', {})
            if isinstance(episodic, dict):
                shared_positive = 0
                shared_negative = 0
                for key, mem in episodic.items():
                    if str(p2.entity_id) in key:
                        valence = mem.get('valence', 0)
                        intensity = mem.get('intensity', 0)
                        if valence > 0:
                            shared_positive += intensity
                        elif valence < 0:
                            shared_negative += intensity
                
                base += min(0.3, shared_positive * 0.05)
                base -= min(0.3, shared_negative * 0.08)
        
        return max(0.0, min(1.0, base))