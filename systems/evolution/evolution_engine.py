"""
Ruta: systems/evolution/evolution_engine.py
Responsabilidad: Monitorear la población, calcular métricas macroevolutivas avanzadas,
                 explicar las presiones de selección (Diferenciales de Selección)
                 y rastrear linajes dominantes o genes en vías de extinción.
"""
import logging
import json
from typing import Optional, Dict, Any, List

class EvolutionEngine:
    def __init__(self, config, ancestry_queries=None):
        self.config = config
        self.ancestry_queries = ancestry_queries
        self.logger = logging.getLogger("EvolutionEngine")
        
        evo_cfg = getattr(config, 'evolution', None)
        self.snapshot_interval_days = getattr(evo_cfg, 'snapshot_interval_days', 30.0)
        self.last_snapshot_time = 0.0

    def normalize_genome(self, genome_obj) -> None:
        """
        Límite artificial eliminado. El control se ejerce por presión selectiva real.
        """
        pass

    def process(self, state: Any, pending: Any, delta_days: float, context: Optional[Any] = None) -> None:
        muertos = set(pending.deaths)
        vivos = [p for p in state.get_all_persons() if p.entity_id not in muertos]
        
        if not vivos:
            return

        if not hasattr(state, 'evolution_history'):
            state.evolution_history = []

        current_time = getattr(state, 'world_days_elapsed', 0.0)
        generaciones = [getattr(p, 'generation', 0) for p in vivos]
        avg_generation = sum(generaciones) / len(generaciones) if generaciones else 0
        max_generation = max(generaciones) if generaciones else 0
        min_generation = min(generaciones) if generaciones else 0

        if current_time == 0.0 or (current_time - self.last_snapshot_time) >= self.snapshot_interval_days:
            snapshot = self._compute_genetic_snapshot(state, vivos, avg_generation, max_generation, min_generation, current_time)
            state.evolution_history.append(snapshot)
            self.last_snapshot_time = current_time
            
            # Log explicativo en consola para saber QUÉ está pasando en este tick
            self._log_evolutionary_insights(snapshot)

    def _compute_genetic_snapshot(self, state: Any, vivos: List[Any], avg_gen: float, max_gen: int, min_gen: int, current_time: float) -> Dict[str, Any]:
        snapshot = {
            "time_days": current_time,
            "population_size": len(vivos),
            "generation_avg": avg_gen,
            "generation_max": max_gen,
            "generation_min": min_gen,
            "gene_averages": {},
            "gene_variances": {},
            "selection_differentials": {},  # EXPLICA: ¿Qué rasgos premia el entorno?
            "genes_in_extinction_risk": [], # EXPLICA: ¿Qué genes se están perdiendo?
            "dominant_lineages": []
        }

        # 1. Extraer los nombres de los genes disponibles en la población
        primer_agente = vivos[0]
        genome_obj = getattr(primer_agente, 'genome', None)
        if not (genome_obj and hasattr(genome_obj, 'genes')):
            return snapshot
            
        nombres_genes = list(genome_obj.genes.keys())
        padres_exitosos = [p for p in vivos if p.children_count > 0]

        # 2. Análisis Genético Profundo y Explicabilidad de Selección
        for nombre_gen in nombres_genes:
            # Valores de toda la población viva
            valores_poblacion = [float(p.genome.genes.get(nombre_gen, 0)) for p in vivos if hasattr(p, 'genome') and hasattr(p.genome, 'genes')]
            
            if valores_poblacion:
                mean_val = sum(valores_poblacion) / len(valores_poblacion)
                variance_val = sum((x - mean_val) ** 2 for x in valores_poblacion) / len(valores_poblacion)
                
                snapshot["gene_averages"][nombre_gen] = mean_val
                snapshot["gene_variances"][nombre_gen] = variance_val

                # Alerta de extinción genómica: si la variabilidad cae cerca de cero, el gen se ha homogeneizado o está muriendo
                if variance_val < 0.01 and mean_val < 0.2:
                    snapshot["genes_in_extinction_risk"].append(nombre_gen)

                # Cálculo del Diferencial de Selección (Fitness Real)
                if padres_exitosos:
                    valores_padres = [float(p.genome.genes.get(nombre_gen, 0)) for p in padres_exitosos]
                    mean_padres = sum(valores_padres) / len(valores_padres)
                    # Diferencial = Media de los reproductores - Media de la población
                    snapshot["selection_differentials"][nombre_gen] = mean_padres - mean_val
                else:
                    snapshot["selection_differentials"][nombre_gen] = 0.0

        # 3. Supervivencia y Éxito de Linajes Históricos
        if self.ancestry_queries:
            vivos_ids = set(p.entity_id for p in vivos)
            fundadores = [p for p in state.get_all_persons() if getattr(p, 'generation', 0) == 0]
            
            top_lineages = []
            for fundador in fundadores:
                metricas = self.ancestry_queries.calculate_lineage_success(fundador.entity_id, vivos_ids)
                if metricas["total_descendencia_viva"] > 0:
                    f_genome = getattr(fundador, 'genome', None)
                    founder_genes = getattr(f_genome, 'genes', {}) if f_genome else {}
                    
                    # Guardamos rendimiento del linaje
                    top_lineages.append({
                        "founder_id": fundador.entity_id,
                        "descendants_alive": metricas["total_descendencia_viva"],
                        "reproductive_efficiency": metricas["total_descendencia_viva"] / max(1, fundador.children_count),
                        "founder_genes": founder_genes
                    })
            
            top_lineages.sort(key=lambda x: x["descendants_alive"], reverse=True)
            snapshot["dominant_lineages"] = top_lineages[:5]

        return snapshot

    def _log_evolutionary_insights(self, snapshot: Dict[str, Any]) -> None:
        """Imprime en los logs una radiografía explicativa clara de la evolución actual."""
        t = snapshot["time_days"]
        self.logger.info(f"=== INFORME EVOLUTIVO (Día {t:.1f}) ===")
        self.logger.info(f" Población Viva: {snapshot['population_size']} | Gen Promedio: {snapshot['generation_avg']:.2f}")
        
        # Explicar presiones del entorno
        diffs = snapshot["selection_differentials"]
        insights_seleccion = [f"{gen}: {'⬆️ Selección Positiva' if val > 0.005 else '⬇️ Selección Negativa' if val < -0.005 else '⚖️ Estable'} ({val:+.4f})" 
                              for gen, val in diffs.items()]
        self.logger.info(f" Presiones de Selección Activas: {', '.join(insights_seleccion)}")
        
        # Alertas de extinción
        if snapshot["genes_in_extinction_risk"]:
            self.logger.warning(f" ⚠️ Rasgos en Peligro Crítico de Extinción: {snapshot['genes_in_extinction_risk']}")
            
        # Linaje ganador
        if snapshot["dominant_lineages"]:
            ganador = snapshot["dominant_lineages"][0]
            self.logger.info(f" 👑 Linaje Dominante: Fundador {ganador['founder_id']} con {ganador['descendants_alive']} descendientes vivos.")

    def export_to_json(self, state: Any, filename: str = "evolution_data.json") -> None:
        history = getattr(state, 'evolution_history', [])
        if not history: return
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)