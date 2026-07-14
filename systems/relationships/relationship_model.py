"""Modelo de datos para relaciones sociales y orientaciones.

Define el espectro Kinsey, estados relacionales progresivos/recesivos,
y la clase Relationship que reemplaza arquitectónicamente a partner_id.

NUEVA ARQUITECTURA:
- Las relaciones ya no son una máquina de estados finitos lineal.
- El estado es una CONSECUENCIA de las variables emocionales.
- Las variables cambian por INTERACCIONES y por la HISTORIA COMPARTIDA (drift).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Tuple


class SexualOrientation(IntEnum):
    """Espectro Kinsey (0-6) para orientación sexual."""
    HETEROSEXUAL = 0
    MOSTLY_HETERO = 1
    BISEXUAL_HETERO = 2
    BISEXUAL = 3
    BISEXUAL_HOMO = 4
    MOSTLY_HOMO = 5
    HOMOSEXUAL = 6


class RelationshipStatus(Enum):
    """Estados relacionales. Son una etiqueta derivada de las variables emocionales."""
    UNKNOWN = "desconocido"
    ACQUAINTANCE = "conocido"
    FRIENDSHIP = "amistad"
    ROMANTIC_INTEREST = "interes_romantico"
    CASUAL = "relacion_esporadica"
    DATING = "noviazgo"
    COHABITATION = "convivencia"
    CONSOLIDATED = "relacion_larga_duracion"
    EX_PARTNER = "ex_pareja"


class RelationshipType(Enum):
    """Tipo de vínculo contractual/social entre dos agentes."""
    EXCLUSIVE = "exclusiva"
    CASUAL = "esporadica"
    OPEN = "abierta"


class RelationshipEventType(Enum):
    """Catálogo de experiencias relacionales significativas (Capa 1: Eventos)."""
    CARE = "care"                    # Un agente cuida a otro
    COOPERATION = "cooperation"      # Trabajo conjunto, defensa mutua
    SHARE_RESOURCE = "share_resource"# Donación o intercambio voluntario
    INTIMACY = "intimacy"            # Tiempo de calidad, cercanía prolongada
    RECONCILIATION = "reconciliation"# Resolución de un conflicto previo
    COMPETITION = "competition"      # Competencia por un recurso limitado
    BETRAYAL = "betrayal"            # Robo, abandono, infidelidad
    CONFLICT = "conflict"            # Pelea física o discusión verbal
    NEGLECT = "neglect"              # Ignorar necesidades básicas del otro
    BIRTH = "birth"                  # Nacimiento de un hijo en común
    CHILD_DEATH = "child_death"      # Muerte de un hijo en común
    PARTNER_DEATH = "partner_death"  # Muerte de la pareja
    COHABITATION_START = "cohabitation_start"
    COHABITATION_END = "cohabitation_end"


@dataclass
class RelationshipEvent:
    """Representa una experiencia compartida entre dos agentes.
    
    Atributos:
        event_type: El tipo de experiencia (del Enum RelationshipEventType).
        agent_a_id: El agente que inicia o es el sujeto principal de la acción.
        agent_b_id: El agente que recibe la acción o es el objeto (puede ser None para eventos grupales).
        intensity: La magnitud emocional del evento [0.0, 1.0]. 
                   Ej: Cuidar una gripe leve = 0.2, salvar la vida = 0.95.
        context: Información adicional específica del evento. 
                 Ej: "Influenza_000001", "comida", "hijo_id_123".
        day: El día de la simulación en que ocurrió el evento.
        metadata: Diccionario opcional para datos adicionales específicos del sistema emisor.
    """
    event_type: RelationshipEventType
    agent_a_id: int
    agent_b_id: int
    intensity: float
    context: str
    day: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validación básica de los rangos de los atributos."""
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError(f"La intensidad debe estar entre 0.0 y 1.0, recibido: {self.intensity}")
        if self.intensity < 0.0:
            self.intensity = 0.0
        elif self.intensity > 1.0:
            self.intensity = 1.0


@dataclass
class RelationshipMemory:
    """Representa un recuerdo específico de una experiencia compartida."""
    event_type: str          # Ej: "CARE", "BIRTH", "BETRAYAL"
    intensity: float         # Magnitud del evento [0.0, 1.0]
    day: float               # Día en que ocurrió
    valence: int             # 1 (positivo), -1 (negativo), 0 (neutro)
    context: str             # Detalles adicionales (ej: "Influenza_000001")
    
    def get_decay_factor(self, current_day: float, half_life_days: float = 365.0) -> float:
        """Calcula cuánto 'peso' tiene este recuerdo hoy (decaimiento exponencial)."""
        days_ago = current_day - self.day
        return math.exp(-days_ago / half_life_days)


@dataclass
class Relationship:
    """Registro de una relación activa o histórica entre dos agentes."""
    partner_id: int
    status: RelationshipStatus
    start_date: float
    last_interaction: float = 0.0
    affinity: float = 0.5
    shared_children: int = 0
    crises_survived: int = 0
    relationship_type: RelationshipType = RelationshipType.EXCLUSIVE
    history: List[Tuple[float, str]] = field(default_factory=list)
    
    # NUEVO: Variables emocionales (0-100)
    trust: float = 0.0
    attraction: float = 0.0
    commitment: float = 0.0
    attachment: float = 0.0
    conflict: float = 0.0
    respect: float = 0.0
    intimacy: float = 0.0
    familiarity: float = 0.0
    
    # NUEVO: Historial de recuerdos estructurados
    memories: List[RelationshipMemory] = field(default_factory=list)

    def add_event(self, current_day: float, event: str) -> None:
        """Registra un evento en el historial de la relación (compatibilidad legacy)."""
        self.history.append((current_day, event))
        self.last_interaction = current_day

    def days_active(self, current_day: float) -> float:
        """Días transcurridos desde el inicio de la relación."""
        return max(0.0, current_day - self.start_date)

    def days_since_interaction(self, current_day: float) -> float:
        """Días transcurridos desde la última interacción."""
        return max(0.0, current_day - self.last_interaction)

    def _calculate_history_drift(self, current_day: float) -> Dict[str, float]:
        """Calcula variaciones diarias basadas en el historial acumulado (Capa 2: Interpretación).
        
        Traduce la historia compartida en pequeños ajustes diarios que modifican 
        las variables emocionales de forma acumulativa pero controlada.
        """
        drift: Dict[str, float] = {
            'trust': 0.0,
            'respect': 0.0,
            'attachment': 0.0,
            'conflict': 0.0
        }
        
        days = self.days_active(current_day)
        
        # 1. Duración de la relación (amistad/relación larga → +respeto, +confianza)
        if days > 180:  # A partir de ~6 meses
            years = days / 365.0
            drift['respect'] += min(0.05, years * 0.015)
            drift['trust'] += min(0.03, years * 0.008)
            drift['attachment'] += min(0.02, years * 0.005)
            
        # 2. Crisis superadas (fortalecen confianza y apego)
        if self.crises_survived > 0:
            drift['trust'] += self.crises_survived * 0.025
            drift['attachment'] += self.crises_survived * 0.018
            
        # 3. Hijos en común (aumentan apego y compromiso)
        if self.shared_children > 0:
            drift['attachment'] += self.shared_children * 0.035
            # El compromiso recibe un empuje directo (no drift)
            self.commitment = min(100.0, self.commitment + (self.shared_children * 0.8))
            
        # 4. Historial de rupturas/abandonos (erosionan confianza, aumentan conflicto)
        breakup_count = sum(
            1 for _, e in self.history 
            if any(k in e.lower() for k in ['breakup', 'ex_pareja', 'abandon', 'divorce'])
        )
        if breakup_count > 0:
            penalty = breakup_count * 0.045
            drift['trust'] -= penalty
            drift['conflict'] += penalty * 0.6
            drift['respect'] -= penalty * 0.3
            
        # 5. Eventos positivos históricos
        positive_events = sum(
            1 for _, e in self.history
            if any(k in e.lower() for k in ['met', 'friend', 'dating', 'cohabitation', 'consolidated', 'reconcil'])
        )
        if positive_events > breakup_count:
            drift['respect'] += min(0.02, (positive_events - breakup_count) * 0.005)
            
        return drift

    def update_emotional_variables(
        self,
        delta_days: float,
        interaction_quality: float = 0.0,
        proximity: float = 0.0,
        current_day: float = 0.0,
    ) -> None:
        """Actualiza las variables emocionales basado en interacciones e historial."""
        decay_rate = 0.001 * delta_days
        
        if interaction_quality == 0.0:
            # Sin interacción: decaimiento lento
            self.trust = max(0.0, self.trust - (decay_rate * 0.5))
            self.attraction = max(0.0, self.attraction - (decay_rate * 0.3))
            self.commitment = max(0.0, self.commitment - (decay_rate * 0.2))
            self.attachment = max(0.0, self.attachment - (decay_rate * 0.4))
            self.intimacy = max(0.0, self.intimacy - (decay_rate * 0.6))
            self.familiarity = max(0.0, self.familiarity - (decay_rate * 0.1))
        else:
            # Con interacción: cambios basados en calidad (TASAS AUMENTADAS ×10 para evolución natural)
            if interaction_quality > 0:
                self.trust = min(100.0, self.trust + (interaction_quality * 10.0 * delta_days))
                self.respect = min(100.0, self.respect + (interaction_quality * 7.5 * delta_days))
                self.attachment = min(100.0, self.attachment + (interaction_quality * 5.0 * delta_days))
                self.intimacy = min(100.0, self.intimacy + (interaction_quality * 6.0 * delta_days))
                self.familiarity = min(100.0, self.familiarity + (5.0 * delta_days))
                
                # Atracción crece si hay proximidad
                if proximity > 0.2:
                    self.attraction = min(100.0, self.attraction + (proximity * 2.5 * delta_days))
            else:
                # Interacción negativa
                self.conflict = min(100.0, self.conflict + (abs(interaction_quality) * 3.0 * delta_days))
                self.trust = max(0.0, self.trust - (abs(interaction_quality) * 2.0 * delta_days))
                self.respect = max(0.0, self.respect - (abs(interaction_quality) * 1.5 * delta_days))
            
            # Compromiso crece con tiempo y confianza (TASAS AUMENTADAS)
            if self.trust > 20 and self.attachment > 15:
                self.commitment = min(100.0, self.commitment + (5.0 * delta_days))
            
            # Conflicto decae naturalmente
            self.conflict = max(0.0, self.conflict - (0.5 * delta_days))

        # Aplicar deriva histórica (impacto acumulativo del pasado)
        hist_drift = self._calculate_history_drift(current_day)
        self.trust = max(0.0, min(100.0, self.trust + (hist_drift['trust'] * delta_days)))
        self.respect = max(0.0, min(100.0, self.respect + (hist_drift['respect'] * delta_days)))
        self.attachment = max(0.0, min(100.0, self.attachment + (hist_drift['attachment'] * delta_days)))
        self.conflict = max(0.0, min(100.0, self.conflict + (hist_drift['conflict'] * delta_days)))

    def get_emotional_profile(self) -> dict:
        """Retorna el perfil emocional actual de la relación."""
        return {
            'trust': self.trust,
            'attraction': self.attraction,
            'commitment': self.commitment,
            'attachment': self.attachment,
            'conflict': self.conflict,
            'respect': self.respect,
            'intimacy': self.intimacy,
            'familiarity': self.familiarity,
        }


class RelationshipClassifier:
    """Clasifica el estado de una relación basado en variables emocionales."""

    @staticmethod
    def classify(relationship: Relationship, current_day: float = 0.0) -> RelationshipStatus:
        """Determina el estado de la relación basado en sus variables emocionales."""
        trust = relationship.trust
        attraction = relationship.attraction
        commitment = relationship.commitment
        attachment = relationship.attachment
        conflict = relationship.conflict
        respect = relationship.respect
        intimacy = relationship.intimacy
        familiarity = relationship.familiarity
        
        # Protección para relaciones nuevas (menos de 30 días)
        days_active = relationship.days_active(current_day)
        if days_active < 30.0:
            if familiarity < 10:
                return RelationshipStatus.UNKNOWN
            if familiarity >= 10 and attraction < 20 and trust < 20:
                return RelationshipStatus.ACQUAINTANCE
            return relationship.status
        
        # EX_PARTNER más estricto (evita rupturas prematuras con trust alto)
        if commitment < 8 and (conflict > 25 or trust < 35):
            return RelationshipStatus.EX_PARTNER
        
        # UNKNOWN: Apenas se conocen
        if familiarity < 10:
            return RelationshipStatus.UNKNOWN
        
        # ACQUAINTANCE: Se conocen pero no hay conexión profunda
        if familiarity >= 10 and attraction < 20 and trust < 20:
            return RelationshipStatus.ACQUAINTANCE
        
        # FRIENDSHIP: Amistad establecida (umbrales MUY reducidos para fluidez)
        if trust >= 10 and attraction < 30 and conflict < 25 and respect >= 10:
            return RelationshipStatus.FRIENDSHIP
        
        # CASUAL: Relación esporádica sin compromiso
        if attraction >= 15 and commitment < 25 and intimacy >= 10:
            return RelationshipStatus.CASUAL
        
        # ROMANTIC_INTEREST: Interés romántico emergente
        if attraction >= 20 and trust >= 10 and commitment < 35:
            return RelationshipStatus.ROMANTIC_INTEREST
        
        # DATING: Noviazgo formal
        if attraction >= 25 and commitment >= 15 and trust >= 15:
            return RelationshipStatus.DATING
        
        # COHABITATION: Convivencia
        if commitment >= 30 and attachment >= 25 and trust >= 25:
            return RelationshipStatus.COHABITATION
        
        # CONSOLIDATED: Relación de larga duración consolidada
        if commitment >= 40 and attachment >= 35 and trust >= 35 and respect >= 25:
            return RelationshipStatus.CONSOLIDATED
        
        # Fallback: mantener el estado actual si no encaja en ningún patrón
        return relationship.status

    @staticmethod
    def get_relationship_description(relationship: Relationship) -> str:
        """Genera una descripción textual del estado de la relación."""
        status = RelationshipClassifier.classify(relationship)
        
        descriptions = {
            RelationshipStatus.UNKNOWN: "Desconocidos",
            RelationshipStatus.ACQUAINTANCE: "Conocidos",
            RelationshipStatus.FRIENDSHIP: "Amigos",
            RelationshipStatus.ROMANTIC_INTEREST: "Interés romántico",
            RelationshipStatus.CASUAL: "Relación casual",
            RelationshipStatus.DATING: "Novios",
            RelationshipStatus.COHABITATION: "Conviviendo",
            RelationshipStatus.CONSOLIDATED: "Relación consolidada",
            RelationshipStatus.EX_PARTNER: "Ex-pareja",
        }
        
        return descriptions.get(status, "Desconocido")


def is_orientation_compatible(
    o1: SexualOrientation,
    o2: SexualOrientation,
    tolerance: float = 1.5
) -> float:
    """Calcula probabilidad de atracción sexual entre dos orientaciones."""
    diff = abs(o1.value - o2.value)
    
    if (o1 == SexualOrientation.HETEROSEXUAL and o2 == SexualOrientation.HOMOSEXUAL) or \
       (o1 == SexualOrientation.HOMOSEXUAL and o2 == SexualOrientation.HETEROSEXUAL):
        return 0.0
    
    max_diff = 6.0
    if diff > max_diff:
        return 0.0
    
    score = max(0.0, 1.0 - (diff / (tolerance + 3.0)))
    return score