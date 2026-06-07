"""
Ruta: systems/metrics/metrics_system.py
Responsabilidad: Recolección y exportación de datos demográficos y biológicos 
                 normalizados por el tiempo transcurrido del mundo (conversión a años para reportes).
"""
import json
import logging
from typing import Dict, List, Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext

class MetricsSystem:
    def __init__(self, config):
        self.config = config
        self.history: List[Dict[str, Any]] = []
        self.total_days_elapsed = 0.0
        self.logger = logging.getLogger("MetricsSystem")
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Devuelve el último snapshot de métricas si existe, si no, devuelve un dict vacío."""
        return self.history[-1] if self.history else {}

    def process(self, state: WorldState, pending: PendingChanges, delta_days: float, context: EnvironmentContext) -> None:
        self.total_days_elapsed += delta_days
        persons = state.get_all_persons()
        total_pop = len(persons)
        
        # Snapshot básico con manejo de seguridad
        snapshot = {
            "day": round(self.total_days_elapsed, 2),
            "year": round(self.total_days_elapsed / 365.0, 2),
            "population": total_pop,
            "avg_age": 0.0,
            "avg_longevity_gene": 0.0,
            "sick_count": 0,
            "marital_ratio": 0.0
        }

        if total_pop > 0:
            total_age_days = sum(p.age for p in persons)
            total_longevity = sum(p.genome.longevity for p in persons)
            
            sick_count = sum(1 for p in persons if p.is_sick)
            married_count = sum(1 for p in persons if p.marital_status == "casado")
            
            # TRANSFORMAZIÓN: Calculamos la edad media convirtiendo los días biológicos a años humanos
            avg_age_years = (total_age_days / total_pop) / 365.0

            snapshot.update({
                "avg_age": round(avg_age_years, 2),
                "avg_longevity_gene": round(total_longevity / total_pop, 4),
                "sick_count": sick_count,
                "marital_ratio": round(married_count / total_pop, 2)
            })

        self.history.append(snapshot)

    def export_to_json(self, filepath: str = "simulation_metrics.json") -> None:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=4, ensure_ascii=False)
        except IOError as e:
            self.logger.error(f"Error al exportar métricas a JSON: {e}")