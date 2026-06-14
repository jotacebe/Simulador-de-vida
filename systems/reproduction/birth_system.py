"""Módulo responsable de la lógica demográfica de natalidad y creación de entidades."""

import random
import math
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from entities.person.person import Person
from core.config.simulation_config import SimulationConfig

class BirthSystem:
    """Motor estocástico de reproducción biológica.
    
    Evalúa las condiciones de fertilidad de las parejas establecidas y
    genera nuevas entidades poblacionales integrando la presión del tiempo.
    """

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema reproductivo vinculándolo a la configuración."""
        self.config = config
        self.logger = logging.getLogger("BirthSystem")

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Procesa los eventos reproductivos de la población fértil."""
        
        rep_cfg = self.config.reproduction
        
        # Probabilidad acumulada en el tiempo (Poisson)
        total_birth_chance = 1.0 - math.exp(-rep_cfg.daily_birth_rate * delta_days)

        for person in state.get_all_persons():
            # Filtro 1: Integridad y género biológico
            if person.entity_id in pending.deaths or getattr(person, 'gender', '') != "F":
                continue
                
            # Filtro 2: Requisito de pareja
            if not getattr(person, 'partner_id', None):
                continue
                
            # Filtro 3: Ventana de fertilidad corregida (evaluada en DÍAS)
            if not (rep_cfg.min_fertility_age_days <= person.age <= rep_cfg.max_fertility_age_days):
                continue

            # Resolución estocástica del embarazo
            if random.random() < total_birth_chance:
                partner = state.get_person_by_id(person.partner_id)
                
                # Verificamos que la pareja exista y siga viva en este tick
                if partner and partner.entity_id not in pending.deaths:
                    self._register_birth_intent(person, partner, state, pending)

    def _register_birth_intent(self, mother: Person, father: Person, 
                               state: WorldState, pending: PendingChanges) -> None:
        """Instancia la nueva entidad y la registra en el búfer transaccional."""
        
        new_id = state.get_next_entity_id()
        
        # El recién nacido aparece en las coordenadas de la madre
        child = Person(
            entity_id=new_id, 
            age=0.0, 
            x=mother.x, 
            y=mother.y, 
            father_id=father.entity_id, 
            mother_id=mother.entity_id
        )
        
        # TODO (Arquitectura): Mutar el estado de los padres directamente aquí rompe 
        # ligeramente la regla de no-mutación. En el futuro, estos contadores 
        # deberían actualizarse en una fase de "Commit" dentro de PendingChanges.
        mother.children_count += 1
        father.children_count += 1
        
        # Delegamos la persistencia al motor transaccional.
        # Nota: El GenealogySystem detectará automáticamente a este individuo en el 
        # siguiente tick gracias a la sincronización de censo (desacoplamiento exitoso).
        pending.register_birth(child)
        
        self.logger.debug(f"Nacimiento registrado: ID {new_id} (Madre: {mother.entity_id}, Padre: {father.entity_id})")