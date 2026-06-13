"""
Ruta: systems/reproduction/gestation_system.py
Responsabilidad: Gestionar de forma determinista el avance del embarazo en el tiempo (días)
                 y culminar en el nacimiento cruzando los genomas de los padres.
"""
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from entities.person.genome import Genome
from systems.environment.environment_context import EnvironmentContext

class GestationSystem:
    def __init__(self, config, evolution_engine=None):
        self.logger = logging.getLogger("GestationSystem")
        self.config = config
        self.evolution_engine = evolution_engine
        
    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        """Hace avanzar los embarazos y ejecuta los partos."""
        
        cfg = getattr(self.config, 'reproduction', {})
        if isinstance(cfg, dict):
            pregnancy_duration = cfg.get("pregnancy_duration_days", 270.0)
            mutation_factor = cfg.get("mutation_factor", 0.05)
            min_genome_val = cfg.get("min_genome_value", 0.01)
        else:
            pregnancy_duration = getattr(cfg, "pregnancy_duration_days", 270.0)
            mutation_factor = getattr(cfg, "mutation_factor", 0.05)
            min_genome_val = getattr(cfg, "min_genome_value", 0.01)

        for person in state.get_all_persons():
            if person.entity_id in pending.deaths:
                continue

            # Este sistema SOLO procesa a personas que ya están embarazadas
            if not person.is_pregnant:
                continue

            # El avance temporal es lineal y puramente en días
            new_pregnancy_days = person.pregnancy_days + delta_days
            
            if new_pregnancy_days >= pregnancy_duration:
                # OBTENER ADN DEL PADRE (Manejo de seguridad en caso de viudedad/divorcio durante gestación)
                father_genome = Genome()
                if person.partner_id:
                    father = state.get_person_by_id(person.partner_id)
                    if father and hasattr(father, 'genome'):
                        father_genome = father.genome

                # CRUZAR GENOMAS (Ahora se delega de forma limpia a la entidad)
                baby_genome = person.genome.combine(father_genome)
                
                # NACE EL BEBÉ
                pending.register_birth(
                    mother_id=person.entity_id,
                    father_id=person.partner_id,
                    genome=baby_genome,
                    x=person.x,
                    y=person.y
                )
                
                # FIN DEL EMBARAZO (Reiniciamos a la madre)
                pending.register_pregnancy_update(person.entity_id, is_pregnant=False, pregnancy_days=0.0)
                self.logger.info(f"Nacimiento registrado: Madre {person.entity_id}")
                
            else:
                # El embarazo continúa, actualizamos los días en el búfer transaccional
                pending.register_pregnancy_update(person.entity_id, is_pregnant=True, pregnancy_days=new_pregnancy_days)