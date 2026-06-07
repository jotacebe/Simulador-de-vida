"""
Ruta: core/config/simulation_config.py
Responsabilidad: Almacenar, centralizar y permitir la mutación en tiempo real 
                 de todos los parámetros biológicos, sociales y ambientales del mundo.
"""
import logging

class SimulationConfig:
    def __init__(self):
        self.logger = logging.getLogger("SimulationConfig")

        # ==========================================
        # EL RELOJ MAESTRO (Resolución temporal)
        # ==========================================
        # Define cuántos días transcurren en el mundo por cada iteración del motor.
        # El usuario final puede modificar esto para acelerar o detallar la simulación.
        self.time = {
            "days_per_tick": 30.0  # Fuente de verdad temporal
        }
        
        # ---------------------------------------------------------
        # CATEGORÍA: REPRODUCCIÓN Y ADOPCIONES
        # ---------------------------------------------------------
        self.reproduction = {
            "base_conception_chance": 0.22,
            "single_mother_conception_chance": 0.03,
            "miscarriage_chance_sick": 0.25,
            "min_age_days": 6570.0,   # 18 años
            "max_age_days": 16425.0,  # 45 años
            "pregnancy_duration_days": 270.0 
        }
        
        # ---------------------------------------------------------
        # CATEGORÍA: ENFERMEDADES (EPIDEMIOLOGÍA)
        # ---------------------------------------------------------
        self.diseases = {
            "base_outbreak_chance": 0.02,       # Probabilidad de paciente cero
            "base_transmission_chance": 0.18,   # Probabilidad base de contagio
            "base_recovery_chance": 0.15,       # Probabilidad de cura por tick
            "base_lethality_rate": 0.06,        # Letalidad base de la enfermedad
            "transmission_radius": 2            # Distancia de contagio espacial
        }
        
        # ---------------------------------------------------------
        # CATEGORÍA: MORTALIDAD BIOLÓGICA
        # ---------------------------------------------------------
        self.mortality = {
            "base_life_expectancy_days": 25550.0, # 70 años
            "infant_threshold_days": 1095.0,      # 3 años (para cálculo de riesgo infantil)
            "infant_mortality_rate": 0.02,      
            "hard_cap_age_days": 41975.0,         # 115 años (Límite biológico absoluto)
            "density_penalty_threshold": 1.2,     # Densidad a partir de la cual sufren estrés
            "density_penalty_multiplier": 1.5     # Multiplicador de muerte por hacinamiento
        }
        
        # ---------------------------------------------------------
        # CATEGORÍA: RELACIONES Y MATRIMONIOS
        # ---------------------------------------------------------
        self.marriage = {
            "min_marriage_age_days": 6570.0,      # 18 años
            "courtship_radius": 3,
            "base_marriage_chance": 0.15,
            "love_at_first_sight_chance": 0.03    # Requisito 12: Libre albedrío puro
        }

    def set_parameter(self, category: str, key: str, value: float) -> bool:
        """
        Modifica un parámetro en tiempo real a mitad de la simulación.
        Permite simular eventos como mutaciones de virus, vacunas o crisis climáticas.
        """
        if not hasattr(self, category):
            self.logger.warning(self.missing_category_msg(category))
            return False
            
        target_dict = getattr(self, category)
        if key not in target_dict:
            self.logger.warning(self.missing_key_msg(category, key))
            return False
            
        old_value = target_dict[key]
        target_dict[key] = value
        self.logger.info(self.param_update_msg(category, key, old_value, value))
        return True

    def get_parameter(self, category: str, key: str) -> float:
        """Recupera de forma segura un parámetro dinámico."""
        return getattr(self, category)[key]

    # Métodos auxiliares para los mensajes de log
    def missing_category_msg(self, cat): return f"Categoría de configuración inexistente: '{cat}'"
    def missing_key_msg(self, cat, k): return f"El parámetro '{k}' no existe en la categoría '{cat}'"
    def param_update_msg(self, cat, k, old, new): return f"[CONFIG DINÁMICA] {cat}.{k} cambiado de {old} a {new}"