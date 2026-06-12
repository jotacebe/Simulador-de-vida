"""
Ruta: systems/behavior/cognitive_memory_system.py
Responsabilidad: Gestionar los mapas de memoria a corto/largo plazo y las 
                 preferencias individuales de los agentes. Modula los impulsos
                 de libre albedrío basándose en experiencias pasadas.
"""
import math
import logging
from typing import Any, Dict, List, Set, Tuple
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

class CognitiveMemorySystem:
    """
    Sistema que procesa la impronta cognitiva y el desgaste psicológico de los agentes.
    
    Permite que los individuos recuerden traumas (hacinamiento, enfermedades) y 
    desarrollen preferencias geográficas o sociales. Estos recuerdos alteran
    las utilidades de sus acciones de libre albedrío, evitando la estasis conductual.
    """

    def __init__(self, config: Any):
        """
        Inicializa el sistema cognitivo configurando la velocidad de olvido sistémica.
        
        Args:
            config (Any): Configuración global del simulador.
        """
        self.config: Any = config
        self.logger: logging.Logger = logging.getLogger("CognitiveMemorySystem")
        
        # Tasa de olvido base (lambda). Un valor de 0.2 significa que un trauma pierde 
        # aproximadamente el 18% de su fuerza cada día de simulación.
        self.base_forgetting_rate: float = 0.2

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: Any) -> None:
        """
        Actualiza el estado mental de todos los agentes vivos, aplicando el decaimiento 
        exponencial a sus memorias y registrando nuevos eventos del entorno.
        
        Args:
            state (WorldState): Estado actual con el censo de agentes.
            pending (PendingChanges): Búfer transaccional de cambios.
            delta_days (float): Tiempo transcurrido en este tick (fracción de días).
            context (EnvironmentContext): El analizador del entorno del tick actual.
        """
        all_persons: List[Any] = state.get_all_persons()
        vivos: List[Any] = [p for p in all_persons if p.entity_id not in pending.deaths]

        for person in vivos:
            # 1. INICIALIZACIÓN DE LA ESTRUCTURA COGNITIVA (Lazy Loading)
            # Si el agente es nuevo o no tiene el componente de memoria, se lo inyectamos de forma dinámica.
            if not hasattr(person, 'memory'):
                person.memory = {
                    "trauma_overcrowding": 0.0,  # Recuerdos de estrés por hacinamiento espacial
                    "trauma_sickness": 0.0,      # Secuelas psicológicas de haber estado enfermo
                    "preferred_sector": None,    # Coordenada del sector donde ha prosperado
                    "rebellion_cooldown": 0.0     # Tiempo de espera para volver a cometer una transgresión
                }

            # 2. PROCESAMIENTO DEL DECAIMIENTO EXPONENCIAL DE MEMORIA
            # Aplicamos de forma estricta la fórmula M(t) = M0 * e^(-lambda * dt)
            # Los agentes con genes de alta tolerancia al estrés disipan el trauma más rápido.
            stress_tolerance: float = getattr(person.genome, 'stress_resistance', 0.5)
            adjusted_lambda: float = self.base_forgetting_rate * (stress_tolerance + 0.5)
            decay_factor: float = math.exp(-adjusted_lambda * delta_days)

            person.memory["trauma_overcrowding"] *= decay_factor
            person.memory["trauma_sickness"] *= decay_factor
            person.memory["rebellion_cooldown"] = max(0.0, person.memory["rebellion_cooldown"] - delta_days)

            # 3. REGISTRO DE NUEVAS EXPERIENCIAS (Impronta del Tick Actual)
            # Consultamos la presión local que sufre el agente a través del contexto malthusiano.
            presion_local: float = context.get_local_pressure(person.x, person.y)
            if presion_local > 1.3:
                # Si la presión supera el umbral de confort, añadimos carga al trauma por hacinamiento
                # El impacto emocional máximo está topado en 1.0 para evitar desbordamientos logarítmicos
                person.memory["trauma_overcrowding"] = min(1.0, person.memory["trauma_overcrowding"] + (0.1 * delta_days))

            if getattr(person, 'is_sick', False):
                # El miedo a la enfermedad se graba en la memoria del agente mientras sufre los síntomas
                person.memory["trauma_sickness"] = min(1.0, person.memory["trauma_sickness"] + (0.15 * delta_days))

            # 4. FIJACIÓN DE PREFERENCIAS GEOGRÁFICAS (Anclaje de éxito)
            # Si un agente es adulto, está sano y tiene hijos vivos en su sector actual, 
            # memoriza esta coordenada como su "lugar seguro" o sector preferido.
            if person.is_adult and not person.is_sick and getattr(person, 'children_count', 0) > 0:
                sector_actual: Tuple[int, int] = (person.x // context.sector_size, person.y // context.sector_size)
                person.memory["preferred_sector"] = sector_actual