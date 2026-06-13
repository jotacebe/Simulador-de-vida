"""Módulo analítico responsable de monitorear la macroevolución del ecosistema."""

import logging
import json
from typing import Dict, Any, List
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges
from systems.environment.environment_context import EnvironmentContext
from core.config.simulation_config import SimulationConfig

class EvolutionEngine:
    """Calcula métricas evolutivas avanzadas y rastrea las presiones de selección.
    
    Actúa como un observador puro (solo lectura). No modifica el estado de los
    agentes, sino que extrae instantáneas del genoma poblacional para su análisis.
    """

    def __init__(self, config: SimulationConfig, ancestry_queries: Any = None) -> None:
        """Inicializa el motor analítico con la configuración centralizada."""
        self.config = config
        self.ancestry_queries = ancestry_queries
        self.logger = logging.getLogger("EvolutionEngine")
        
        self.last_snapshot_time = 0.0
        
        # El motor es dueño de su propio historial, aislando la analítica del WorldState
        self.history: List[Dict[str, Any]] = []

    def process(self, state: WorldState, pending: PendingChanges, 
                delta_days: float, context: EnvironmentContext) -> None:
        """Recolecta instantáneas (snapshots) genéticas a intervalos regulares."""
        
        evo_cfg = self.config.evolution
        
        # Filtramos la población activa garantizando la integridad referencial
        vivos = [p for p in state.get_all_persons() if p.entity_id not in pending.deaths]
        if not vivos:
            return

        current_time = getattr(state, 'world_days_elapsed', 0.0)

        # Disparamos el análisis genético si ha transcurrido el intervalo configurado
        if current_time == 0.0 or (current_time - self.last_snapshot_time) >= evo_cfg.snapshot_interval_days:
            
            # Cálculos generacionales básicos
            generaciones = [getattr(p, 'generation', 0) for p in vivos]
            avg_generation = sum(generaciones) / len(generaciones) if generaciones else 0.0
            max_generation = max(generaciones) if generaciones else 0
            min_generation = min(generaciones) if generaciones else 0

            # Computamos la instantánea analítica
            snapshot = self._compute_genetic_snapshot(
                state=state, 
                vivos=vivos, 
                avg_gen=avg_generation, 
                max_gen=max_generation, 
                min_gen=min_generation, 
                current_time=current_time
            )
            
            # Guardamos la instantánea en el almacén local del motor
            self.history.append(snapshot)
            self.last_snapshot_time = current_time
            
            # Imprimimos el log para la consola
            self._log_evolutionary_insights(snapshot)

    def _get_tracked_genes(self, sample_genome: Any) -> List[str]:
        """Extrae dinámicamente los nombres de los rasgos genéticos disponibles.
        
        Inspecciona los atributos de la clase Genome evitando los métodos y 
        variables privadas, para adaptarse automáticamente si se añaden nuevos genes.
        """
        return [attr for attr, val in vars(sample_genome).items() 
                if isinstance(val, (float, int)) and not attr.startswith('_')]

    def _compute_genetic_snapshot(self, state: WorldState, vivos: List[Any], 
                                  avg_gen: float, max_gen: int, min_gen: int, 
                                  current_time: float) -> Dict[str, Any]:
        """Realiza un escaneo profundo de la diversidad genética y éxito reproductivo."""
        
        evo_cfg = self.config.evolution
        snapshot = {
            "time_days": current_time,
            "population_size": len(vivos),
            "generation_avg": avg_gen,
            "generation_max": max_gen,
            "generation_min": min_gen,
            "gene_averages": {},
            "gene_variances": {},
            "selection_differentials": {},  # Indica la presión del entorno sobre los genes
            "genes_in_extinction_risk": [], # Alerta de pérdida de diversidad
            "dominant_lineages": []
        }

        # Extraemos los genes a rastrear a partir de un espécimen vivo
        primer_agente = vivos[0]
        if not hasattr(primer_agente, 'genome'):
            return snapshot
            
        nombres_genes = self._get_tracked_genes(primer_agente.genome)
        
        # Filtramos a la subpoblación con éxito evolutivo (han dejado descendencia)
        padres_exitosos = [p for p in vivos if getattr(p, 'children_count', 0) > 0]

        # 1. ANÁLISIS GENÉTICO PROFUNDO
        for gen in nombres_genes:
            # Extraemos los valores fenotípicos mediante introspección
            valores_poblacion = [float(getattr(p.genome, gen, 0.0)) for p in vivos]
            
            if valores_poblacion:
                mean_val = sum(valores_poblacion) / len(valores_poblacion)
                variance_val = sum((x - mean_val) ** 2 for x in valores_poblacion) / len(valores_poblacion)
                
                snapshot["gene_averages"][gen] = mean_val
                snapshot["gene_variances"][gen] = variance_val

                # Alerta de homogeneización: Si la varianza colapsa, el rasgo está en peligro
                if variance_val < evo_cfg.variance_extinction_threshold and mean_val < evo_cfg.mean_extinction_threshold:
                    snapshot["genes_in_extinction_risk"].append(gen)

                # Cálculo del Diferencial de Selección (Fitness Real vs Poblacional)
                if padres_exitosos:
                    valores_padres = [float(getattr(p.genome, gen, 0.0)) for p in padres_exitosos]
                    mean_padres = sum(valores_padres) / len(valores_padres)
                    # Diferencial positivo = El rasgo aumenta la probabilidad de reproducirse
                    snapshot["selection_differentials"][gen] = mean_padres - mean_val
                else:
                    snapshot["selection_differentials"][gen] = 0.0

        # 2. SUPERVIVENCIA Y ÉXITO DE LINAJES
        if self.ancestry_queries:
            vivos_ids = {p.entity_id for p in vivos}
            # Identificamos a los "Evas y Adanes" del ecosistema (Generación 0)
            fundadores = [p for p in state.get_all_persons() if getattr(p, 'generation', 0) == 0]
            
            top_lineages = []
            for fundador in fundadores:
                metricas = self.ancestry_queries.calculate_lineage_success(fundador.entity_id, vivos_ids)
                
                if metricas["total_descendencia_viva"] > 0:
                    f_genome = getattr(fundador, 'genome', None)
                    # Serializamos de forma segura el genoma del fundador histórico
                    founder_genes = {g: getattr(f_genome, g, 0.0) for g in nombres_genes} if f_genome else {}
                    
                    top_lineages.append({
                        "founder_id": fundador.entity_id,
                        "descendants_alive": metricas["total_descendencia_viva"],
                        "reproductive_efficiency": metricas["total_descendencia_viva"] / max(1, getattr(fundador, 'children_count', 1)),
                        "founder_genes": founder_genes
                    })
            
            # Ordenamos por éxito demográfico para guardar el Top 5
            top_lineages.sort(key=lambda x: x["descendants_alive"], reverse=True)
            snapshot["dominant_lineages"] = top_lineages[:5]

        return snapshot

    def _log_evolutionary_insights(self, snapshot: Dict[str, Any]) -> None:
        """Imprime una radiografía explicativa clara de las dinámicas evolutivas actuales."""
        t = snapshot["time_days"]
        self.logger.info(f"=== INFORME EVOLUTIVO (Día {t:.1f}) ===")
        self.logger.info(f" Población Viva: {snapshot['population_size']} | Generación Media: {snapshot['generation_avg']:.2f}")
        
        # Explicación de las presiones del entorno
        diffs = snapshot["selection_differentials"]
        insights_seleccion = [
            f"{gen}: {'⬆️ Positiva' if val > 0.005 else '⬇️ Negativa' if val < -0.005 else '⚖️ Estable'} ({val:+.4f})" 
            for gen, val in diffs.items()
        ]
        self.logger.info(f" Presiones de Selección Activas: {', '.join(insights_seleccion)}")
        
        if snapshot["genes_in_extinction_risk"]:
            self.logger.warning(f" ⚠️ Rasgos en Peligro de Extinción: {snapshot['genes_in_extinction_risk']}")
            
        if snapshot["dominant_lineages"]:
            ganador = snapshot["dominant_lineages"][0]
            self.logger.info(f" 👑 Linaje Dominante: Fundador {ganador['founder_id']} ({ganador['descendants_alive']} descendientes vivos).")

    def export_to_json(self, filename: str = "evolution_data.json") -> None:
        """Persiste el historial macroevolutivo a disco para su análisis visual."""
        if not self.history: 
            return
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=4)