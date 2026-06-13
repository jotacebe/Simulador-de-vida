"""Módulo responsable de la recolección y exportación de datos demográficos."""

import json
import logging
from typing import Dict, List, Any
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class MetricsSystem:
    """Recolecta métricas demográficas normalizadas por el tiempo transcurrido."""

    def __init__(self, config: SimulationConfig) -> None:
        """Inicializa el sistema de métricas con la configuración central."""
        self.config = config
        self.history: List[Dict[str, Any]] = []
        self.total_days_elapsed = 0.0
        self.last_snapshot_time = -1.0  # Para forzar la primera captura en el día 0
        self.logger = logging.getLogger("MetricsSystem")

    def get_latest_metrics(self) -> Dict[str, Any]:
        """Devuelve el último snapshot de métricas si existe."""
        return self.history[-1] if self.history else {}

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Calcula las estadísticas globales de la población viva en el tick actual."""
        self.total_days_elapsed += delta_days
        
        # Acceso limpio a la configuración
        interval = getattr(self.config.metrics, 'snapshot_interval_days', 1.0)

        # Optimización de RAM: Solo tomamos métricas según el intervalo configurado
        if (self.total_days_elapsed - self.last_snapshot_time) < interval and self.total_days_elapsed > 0:
            return

        self.last_snapshot_time = self.total_days_elapsed

        # 1. FILTRADO (Integridad Referencial): Omitimos a las entidades recién fallecidas
        alive_persons = [p for p in state.get_all_persons() if p.entity_id not in pending.deaths]
        total_pop = len(alive_persons)
        
        # Snapshot base estructural
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
            total_age_days = 0.0
            total_longevity = 0.0
            sick_count = 0
            married_count = 0

            # 2. OPTIMIZACIÓN O(N): Bucle único para recolectar todas las métricas
            for p in alive_persons:
                total_age_days += getattr(p, 'age', 0.0)
                # Introspección segura para evitar cuelgues si un gen no existe
                total_longevity += getattr(getattr(p, 'genome', None), 'longevity', 0.0)
                
                if getattr(p, 'is_sick', False):
                    sick_count += 1
                if getattr(p, 'marital_status', "") == "casado":
                    married_count += 1
            
            # TRANSFORMACIÓN: Convertimos los días biológicos a años humanos
            avg_age_years = (total_age_days / total_pop) / 365.0

            snapshot.update({
                "avg_age": round(avg_age_years, 2),
                "avg_longevity_gene": round(total_longevity / total_pop, 4),
                "sick_count": sick_count,
                "marital_ratio": round(married_count / total_pop, 2)
            })

        self.history.append(snapshot)

    def export_to_json(self, filepath: str = "simulation_metrics.json") -> None:
        """Exporta la serie temporal de métricas a un archivo JSON en disco."""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=4, ensure_ascii=False)
        except IOError as e:
            self.logger.error(f"Error al exportar métricas a JSON: {e}")