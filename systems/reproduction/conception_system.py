"""Módulo responsable de la transición de estado hacia la gestación biológica.

Implementa un modelo multifactorial de concepción que considera:
- Compatibilidad sexual (orientación Kinsey + género)
- Estado de la relación (modificador de probabilidad)
- Fertilidad biológica (edad + genética + salud)
- Deseo de engendrar (motivación continua)
- Épocas de celo (temporalidad por especie)

La concepción NO es binaria: incluso relaciones casuales pueden producir
embarazos (con baja probabilidad), y parejas estables tienen alta probabilidad.

Soporta estrategias reproductivas avanzadas:
- Partenogénesis (especies que la soporten)
- Camadas múltiples (litters)
- Selección de rasgos por especie
"""

import random
import math
import logging
from typing import Any, Dict, Optional, Tuple

from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig
from systems.relationships.relationship_model import (
    RelationshipStatus,
    SexualOrientation,
    is_orientation_compatible,
)


class ConceptionSystem:
    """Gestiona la iniciación de la gestación con modelo multifactorial."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # =====================================================================
        # MODIFICADORES POR ESTADO DE RELACIÓN
        # =====================================================================
        # Parejas estables tienen más probabilidad, pero incluso relaciones
        # casuales pueden producir embarazos (con baja probabilidad)
        self.relationship_modifiers: Dict[RelationshipStatus, float] = {
            RelationshipStatus.CONSOLIDATED: 1.0,      # Máxima probabilidad
            RelationshipStatus.COHABITATION: 0.85,     # Muy alta
            RelationshipStatus.DATING: 0.50,           # Alta (relación seria)
            RelationshipStatus.ROMANTIC_INTEREST: 0.25, # Moderada
            RelationshipStatus.CASUAL: 0.08,           # Baja (encuentros esporádicos)
            RelationshipStatus.FRIENDSHIP: 0.02,       # Muy baja (amigos con beneficios)
            RelationshipStatus.ACQUAINTANCE: 0.01,     # Mínima
            RelationshipStatus.UNKNOWN: 0.005,         # Casi imposible
        }
        
        # =====================================================================
        # CURVA DE FERTILIDAD POR EDAD (Humanos)
        # =====================================================================
        # Pico de fertilidad entre 20-30 años, decrece después
        self.age_fertility_curve: Dict[Tuple[float, float], float] = {
            (0, 5475): 0.0,       # 0-15 años: estéril
            (5475, 7300): 0.50,   # 15-20 años: fertilidad media
            (7300, 10950): 1.0,   # 20-30 años: máxima fertilidad
            (10950, 12775): 0.80, # 30-35 años: fertilidad alta
            (12775, 14600): 0.50, # 35-40 años: fertilidad media
            (14600, 16425): 0.20, # 40-45 años: fertilidad baja
            (16425, 99999): 0.0,  # 45+ años: estéril
        }
        
        # =====================================================================
        # PENALIZADORES POR ENFERMEDADES
        # =====================================================================
        # Enfermedades que reducen la fertilidad
        self.disease_fertility_penalties: Dict[str, float] = {
            "impotence": 0.0,              # Impotencia total
            "low_libido": 0.3,             # Libido baja
            "std_chlamydia": 0.4,          # Clamidia (reduce fertilidad)
            "std_gonorrhea": 0.3,          # Gonorrea
            "std_hiv": 0.2,                # VIH
            "pcos": 0.5,                   # Síndrome ovario poliquístico
            "endometriosis": 0.4,          # Endometriosis
            "genetic_infertility": 0.1,    # Infertilidad genética
        }
        
        # =====================================================================
        # ÉPOCAS DE CELO POR ESPECIE
        # =====================================================================
        # Estaciones donde la especie es más fértil
        self.mating_seasons: Dict[str, list] = {
            "human": ["SPRING", "SUMMER", "AUTUMN", "WINTER"],  # Todo el año
            "elf": ["SPRING"],                                    # Solo primavera
            "goblin": ["SUMMER", "AUTUMN"],                       # Verano y otoño
            "dragon": ["WINTER"],                                 # Solo invierno
        }
        
        # Multiplicador de fertilidad fuera de temporada
        self.off_season_multiplier: float = 0.3

    def _get_species_traits(self, species: str) -> dict:
        """Provee los perfiles reproductivos por especie."""
        profiles = {
            "human": {
                "parthenogenesis_chance": 0.0,
                "litter_size_min": 1,
                "litter_size_max": 1,
                "gestation_days": self.config.reproduction.pregnancy_duration_days
            },
            "elf": {
                "parthenogenesis_chance": 0.0,
                "litter_size_min": 1,
                "litter_size_max": 1,
                "gestation_days": 730.0
            },
            "goblin": {
                "parthenogenesis_chance": 0.05,
                "litter_size_min": 3,
                "litter_size_max": 6,
                "gestation_days": 120.0
            },
            "dragon": {
                "parthenogenesis_chance": 0.1,
                "litter_size_min": 1,
                "litter_size_max": 3,
                "gestation_days": 1200.0
            }
        }
        return profiles.get(species, profiles["human"])

    def _is_sexually_compatible(self, person1: Any, person2: Any) -> bool:
        """Verifica compatibilidad sexual (orientación + género)."""
        # 1. Compatibilidad de orientación (espectro Kinsey)
        orientation_score = is_orientation_compatible(
            person1.sexual_orientation,
            person2.sexual_orientation,
            tolerance=self.config.relationships.orientation_tolerance,
        )
        if orientation_score <= 0.0:
            return False
        
        # 2. Compatibilidad de género para reproducción biológica
        genders = {person1.gender, person2.gender}
        if genders == {"M", "F"} or genders == {"F", "M"}:
            return True
        
        # Mismo género: no pueden reproducirse sexualmente
        return False

    def _get_relationship_status(self, person: Any, partner_id: int) -> RelationshipStatus:
        """Obtiene el estado de la relación con un partner específico."""
        if not hasattr(person, 'get_relationship_with'):
            # Fallback para agentes legacy sin sistema de relaciones
            return RelationshipStatus.CONSOLIDATED
        
        rel = person.get_relationship_with(partner_id)
        if rel:
            return rel.status
        return RelationshipStatus.UNKNOWN

    def _get_age_fertility_modifier(self, age: float) -> float:
        """Calcula el modificador de fertilidad según la edad."""
        for (min_age, max_age), modifier in self.age_fertility_curve.items():
            if min_age <= age < max_age:
                return modifier
        return 0.0

    def _get_health_modifier(self, person: Any) -> float:
        """Calcula el modificador de fertilidad según la salud."""
        # Si no tiene enfermedades, fertilidad normal
        if not getattr(person, 'is_sick', False):
            return 1.0
        
        # Penalización por enfermedades
        penalty = 1.0
        for infection_id in person.active_infections.keys():
            # Extraer nombre de enfermedad del ID
            disease_name = infection_id.split('_')[0].lower()
            if disease_name in self.disease_fertility_penalties:
                penalty *= self.disease_fertility_penalties[disease_name]
        
        return max(0.0, penalty)

    def _get_fertility_desire(self, person: Any) -> float:
        """Obtiene el deseo de engendrar (motivación)."""
        # Intentar obtener de motivaciones
        if hasattr(person, 'get_motivation'):
            desire = person.get_motivation("fertility_desire")
            if desire > 0:
                return desire
        
        # Fallback: valor por defecto basado en edad
        age = person.age
        if 7300 <= age <= 14600:  # 20-40 años
            return 0.5
        elif 5475 <= age <= 7300 or 14600 < age <= 16425:  # 15-20 o 40-45
            return 0.3
        else:
            return 0.1

    def _get_seasonal_modifier(self, person: Any, current_season: str) -> float:
        """Calcula el modificador de fertilidad según la estación."""
        species = person.species
        mating_seasons = self.mating_seasons.get(species, [])
        
        if current_season in mating_seasons:
            return 1.0  # Temporada alta
        else:
            return self.off_season_multiplier  # Fuera de temporada

    def process(
        self,
        state: WorldState,
        pending: PendingChanges,
        delta_days: float,
        context: EnvironmentContext,
    ) -> None:
        """Evalúa posibilidades de concepción para todos los agentes fértiles."""
        rep_cfg = self.config.reproduction
        time_cfg = self.config.time
        
        # Probabilidad base por ciclo
        daily_rate = rep_cfg.base_conception_chance / time_cfg.days_per_year
        base_prob_period = 1.0 - math.exp(-daily_rate * delta_days)
        
        # Obtener estación actual
        current_season = getattr(context, 'current_season', 'SPRING')

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths or getattr(person, 'is_pregnant', False):
                continue

            traits = self._get_species_traits(person.species)
            
            # =================================================================
            # 1. REPRODUCCIÓN ASEXUAL (Partenogénesis)
            # =================================================================
            if traits["parthenogenesis_chance"] > 0:
                if random.random() < traits["parthenogenesis_chance"]:
                    litter_size = random.randint(traits["litter_size_min"], traits["litter_size_max"])
                    pending.register_pregnancy_update(
                        person.entity_id, True, 0.0, failed_increment=0, litter_size=litter_size
                    )
                    self.logger.debug(
                        "🧬 Concepción asexual: Agente %s (Camada: %d)",
                        person.entity_id, litter_size
                    )
                continue

            # =================================================================
            # 2. REPRODUCCIÓN SEXUAL (modelo multifactorial)
            # =================================================================
            
            # Verificar fertilidad biológica
            age_modifier = self._get_age_fertility_modifier(person.age)
            if age_modifier <= 0.0:
                continue  # Fuera de ventana fértil
            
            # Obtener deseo de engendrar
            fertility_desire = self._get_fertility_desire(person)
            if fertility_desire <= 0.0:
                continue
            
            # Buscar parejas potenciales (cualquier agente compatible cercano)
            potential_partners = []
            for other in state.get_all_persons():
                if other.entity_id == person.entity_id:
                    continue
                if other.entity_id in pending.deaths:
                    continue
                if not self._is_sexually_compatible(person, other):
                    continue
                
                # Verificar fertilidad de la pareja
                partner_age_modifier = self._get_age_fertility_modifier(other.age)
                if partner_age_modifier <= 0.0:
                    continue
                
                # Obtener estado de la relación
                rel_status = self._get_relationship_status(person, other.entity_id)
                rel_modifier = self.relationship_modifiers.get(rel_status, 0.01)
                
                # Si no hay relación y no hay atracción, saltar
                if rel_status == RelationshipStatus.UNKNOWN and rel_modifier < 0.01:
                    continue
                
                potential_partners.append((other, rel_status, rel_modifier))
            
            if not potential_partners:
                continue
            
            # Evaluar cada pareja potencial
            for partner, rel_status, rel_modifier in potential_partners:
                # Calcular modificadores
                health_modifier = self._get_health_modifier(person) * self._get_health_modifier(partner)
                seasonal_modifier = self._get_seasonal_modifier(person, current_season)
                
                # Fertilidad genética
                genetic_fertility = (person.genome.fertility + partner.genome.fertility) / 2.0
                
                # Energía (ambos deben tener energía)
                energy_multiplier = min(person.emotions["energy"], partner.emotions["energy"])
                
                # Fórmula final multifactorial
                final_chance = (
                    base_prob_period *
                    rel_modifier *           # Estado de la relación
                    age_modifier *           # Fertilidad por edad
                    genetic_fertility *      # Genética
                    health_modifier *        # Salud
                    fertility_desire *       # Deseo
                    seasonal_modifier *      # Época de celo
                    energy_multiplier        # Energía
                )
                
                # Clampar a [0, 1]
                final_chance = max(0.0, min(1.0, final_chance))
                
                if random.random() < final_chance:
                    litter_size = random.randint(traits["litter_size_min"], traits["litter_size_max"])
                    pending.register_pregnancy_update(
                        person.entity_id, True, 0.0, failed_increment=0, litter_size=litter_size
                    )
                    
                    self.logger.debug(
                        "👶 Concepción: %s y %s (relación: %s, prob: %.4f, camada: %d)",
                        person.entity_id, partner.entity_id,
                        rel_status.value, final_chance, litter_size
                    )
                    
                    # Solo una concepción por tick por agente
                    break