"""Modelo de datos para relaciones sociales y orientaciones.

Define el espectro Kinsey, estados relacionales progresivos/recesivos,
y la clase Relationship que reemplaza arquitectónicamente a partner_id.

Los estados son recesivos: una relación puede degradarse si no hay
interacción o si la afinidad cae por debajo de umbrales críticos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, List, Optional, Tuple


class SexualOrientation(IntEnum):
    """Espectro Kinsey (0-6) para orientación sexual.
    
    0: Exclusivamente heterosexual
    1: Predominantemente heterosexual, ocasionalmente homosexual
    2: Predominantemente heterosexual, más que ocasionalmente homosexual
    3: Bisexual equilibrado
    4: Predominantemente homosexual, más que ocasionalmente heterosexual
    5: Predominantemente homosexual, ocasionalmente heterosexual
    6: Exclusivamente homosexual
    """
    HETEROSEXUAL = 0
    MOSTLY_HETERO = 1
    BISEXUAL_HETERO = 2
    BISEXUAL = 3
    BISEXUAL_HOMO = 4
    MOSTLY_HOMO = 5
    HOMOSEXUAL = 6


class RelationshipStatus(Enum):
    """Estados relacionales progresivos Y recesivos.
    
    Las transiciones pueden avanzar o retroceder según:
    - Afinidad entre los agentes
    - Tiempo sin interacción (decaimiento)
    - Eventos vitales (ruptura, reconciliación)
    - Impulsos de libre albedrío
    """
    UNKNOWN = "desconocido"
    ACQUAINTANCE = "conocido"
    FRIENDSHIP = "amistad"
    ROMANTIC_INTEREST = "interes_romantico"
    CASUAL = "relacion_esporadica"
    DATING = "noviazgo"
    COHABITATION = "convivencia"
    CONSOLIDATED = "relacion_larga_duracion"
    EX_PARTNER = "ex_pareja"  # Estado recesivo post-ruptura


class RelationshipType(Enum):
    """Tipo de vínculo contractual/social entre dos agentes."""
    EXCLUSIVE = "exclusiva"
    CASUAL = "esporadica"
    OPEN = "abierta"


@dataclass
class Relationship:
    """Registro de una relación activa o histórica entre dos agentes.
    
    Atributos:
        partner_id: ID del otro agente.
        status: Estado actual de la relación.
        start_date: Día simulado en que comenzó.
        last_interaction: Día simulado de la última interacción significativa.
        affinity: Compatibilidad emocional/genética [0.0, 1.0].
        shared_children: Hijos en común.
        crises_survived: Número de crisis superadas (fortalece el vínculo).
        relationship_type: Tipo de relación (exclusiva, esporádica, etc.).
        history: Lista de tuplas (fecha, evento) para trazabilidad.
    """
    partner_id: int
    status: RelationshipStatus
    start_date: float
    last_interaction: float = 0.0
    affinity: float = 0.5
    shared_children: int = 0
    crises_survived: int = 0
    relationship_type: RelationshipType = RelationshipType.EXCLUSIVE
    history: List[Tuple[float, str]] = field(default_factory=list)

    def add_event(self, current_day: float, event: str) -> None:
        """Registra un evento en el historial de la relación."""
        self.history.append((current_day, event))
        self.last_interaction = current_day

    def days_active(self, current_day: float) -> float:
        """Días transcurridos desde el inicio de la relación."""
        return max(0.0, current_day - self.start_date)

    def days_since_interaction(self, current_day: float) -> float:
        """Días transcurridos desde la última interacción."""
        return max(0.0, current_day - self.last_interaction)


def is_orientation_compatible(
    o1: SexualOrientation,
    o2: SexualOrientation,
    tolerance: float = 1.5
) -> float:
    """Calcula probabilidad de atracción sexual entre dos orientaciones.
    
    Args:
        o1: Orientación del primer agente.
        o2: Orientación del segundo agente.
        tolerance: Tolerancia en escala Kinsey para considerar atracción.
        
    Returns:
        Score de compatibilidad [0.0, 1.0]. 0.0 = incompatibles.
    """
    diff = abs(o1.value - o2.value)
    
    # Heterosexual (0) con homosexual (6) y viceversa → incompatibles
    if (o1 == SexualOrientation.HETEROSEXUAL and o2 == SexualOrientation.HOMOSEXUAL) or \
       (o1 == SexualOrientation.HOMOSEXUAL and o2 == SexualOrientation.HETEROSEXUAL):
        return 0.0
    
    # Curva triangular suavizada centrada en diferencia 0
    max_diff = 6.0
    if diff > max_diff:
        return 0.0
    
    # Score lineal decreciente con la diferencia
    score = max(0.0, 1.0 - (diff / (tolerance + 3.0)))
    return score