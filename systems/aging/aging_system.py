"""Módulo responsable de la progresión temporal y desgaste biológico multifactorial.

Implementa un modelo de envejecimiento que considera múltiples factores:
- Desgaste reproductivo (solo hijos biológicos, con límite máximo)
- Carga del embarazo (solo para la madre)
- Estrés crónico (acelera el envejecimiento celular)
- Enfermedades activas (desgaste del sistema inmunológico)
- Baja energía (desnutrición, pobreza)
- Factor genético (longevidad heredada)

Todos los parámetros son configurables para permitir simular diferentes
condiciones de vida y características de diversas sociedades.
"""

from __future__ import annotations

import logging

from core.config.simulation_config import SimulationConfig
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState
from systems.environment.environment_context import EnvironmentContext


class AgingSystem:
    """Calcula el envejecimiento biológico basado en múltiples factores de desgaste."""

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
        """Aplica el desgaste biológico multifactorial a todas las entidades activas.
        
        Calcula el envejecimiento considerando:
        - Hijos biológicos (no adoptivos, con límite máximo)
        - Embarazo activo (solo madres)
        - Estrés crónico
        - Enfermedades activas
        - Nivel de energía
        - Genética de longevidad
        
        Args:
            state: Estado autoritativo del mundo.
            pending: Búfer transaccional donde se registran los cambios.
            delta_days: Duración del tick en días simulados.
            context: Contexto ambiental del tick.
        """
        aging_cfg = self.config.aging
        
        for person in state.get_all_persons():
            # Filtro de integridad: Ya fallecido en este tick
            if person.entity_id in pending.deaths:
                continue
            
            # =================================================================
            # CÁLCULO DE FACTORES DE DESGASTE
            # =================================================================
            
            # 1. DESGASTE REPRODUCTIVO (Solo hijos biológicos, CON LÍMITE)
            # Las madres sufren el desgaste completo, los padres solo una fracción
            biological_children = getattr(person, 'biological_children_count', 0)
            is_female = getattr(person, 'gender', 'M') == 'F'
            
            # Aplicar límite de hijos para el cálculo del desgaste
            # Más allá de max_children_for_aging, no hay desgaste adicional
            effective_children = min(biological_children, aging_cfg.max_children_for_aging)
            
            if is_female:
                # Madre: desgaste completo por hijos biológicos
                reproductive_wear = 1.0 + (effective_children * aging_cfg.reproductive_wear_per_child)
            else:
                # Padre: desgaste reducido (no gestó ni parió)
                reproductive_wear = 1.0 + (
                    effective_children * aging_cfg.reproductive_wear_per_child * aging_cfg.father_reproductive_wear_ratio
                )
            
            # Aplicar tope absoluto al desgaste reproductivo
            reproductive_wear = min(reproductive_wear, aging_cfg.max_reproductive_wear_multiplier)
            
            # 2. CARGA DEL EMBARAZO (Solo para la madre)
            # El embarazo activo acelera el envejecimiento durante la gestación
            is_pregnant = getattr(person, 'is_pregnant', False)
            pregnancy_burden = aging_cfg.pregnancy_burden_multiplier if is_pregnant else 1.0
            
            # 3. DESGASTE POR ESTRÉS CRÓNICO
            # El estrés acelera el envejecimiento celular (telómeros)
            stress_level = person.emotions.get("stress", 0.0)
            stress_aging = 1.0 + (stress_level * aging_cfg.stress_aging_factor)
            
            # 4. DESGASTE POR ENFERMEDAD
            # Las enfermedades activas aceleran el envejecimiento
            is_sick = getattr(person, 'is_sick', False)
            sickness_aging = 1.0 + (aging_cfg.sickness_aging_factor if is_sick else 0.0)
            
            # 5. DESGASTE POR BAJA ENERGÍA
            # La falta de energía (desnutrición, pobreza) acelera el envejecimiento
            energy_level = person.emotions.get("energy", 1.0)
            # Energía baja (cerca de 0) aumenta el desgaste, energía alta (cerca de 1) no afecta
            low_energy_aging = 1.0 + ((1.0 - energy_level) * aging_cfg.low_energy_aging_factor)
            
            # 6. FACTOR GENÉTICO (Longevidad)
            # Las personas con genes de longevidad envejecen más lento
            # El gen de longevidad va de 0.1 a 3.0, normalizamos para usarlo como divisor
            genetic_longevity = person.genome.longevity
            # Normalizamos: longevidad 1.0 = factor 1.0, longevidad 2.0 = factor 0.5 (envejece más lento)
            genetic_factor = aging_cfg.longevity_genetic_factor / max(0.1, genetic_longevity)
            
            # =================================================================
            # CÁLCULO FINAL DEL ENVEJECIMIENTO
            # =================================================================
            # Multiplicamos todos los factores y dividimos por el factor genético
            total_aging_multiplier = (
                reproductive_wear *
                pregnancy_burden *
                stress_aging *
                sickness_aging *
                low_energy_aging *
                genetic_factor
            )
            
            # Aplicamos el multiplicador al delta_days base
            biological_increment = delta_days * total_aging_multiplier
            
            # Registramos la mutación de estado temporal en el búfer transaccional
            pending.register_age_increment(person.entity_id, biological_increment)
            
            # Logging detallado para debugging (solo si el envejecimiento es significativo)
            if total_aging_multiplier > 1.5 or total_aging_multiplier < 0.7:
                self.logger.debug(
                    "Envejecimiento %s: %.2f días (multiplicador: %.2f) "
                    "[repro: %.2f, preg: %.2f, stress: %.2f, sick: %.2f, energy: %.2f, gen: %.2f]",
                    person.entity_id,
                    biological_increment,
                    total_aging_multiplier,
                    reproductive_wear,
                    pregnancy_burden,
                    stress_aging,
                    sickness_aging,
                    low_energy_aging,
                    genetic_factor,
                )