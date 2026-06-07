"""
Ruta: systems/relationships/marriage_system.py
Responsabilidad: Gestionar el cortejo y matrimonios de forma transaccional,
                 normalizada por tiempo y sin efectos secundarios en el estado.
"""
import random
import logging
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

class MarriageSystem:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("MarriageSystem")

    def _es_incesto(self, p1, p2) -> bool:
        # Uso de la API Genética/Parental correcta
        parents_p1 = set(p1.parents_ids) if hasattr(p1, 'parents_ids') else set()
        parents_p2 = set(p2.parents_ids) if hasattr(p2, 'parents_ids') else set()
        
        if p1.entity_id in parents_p2 or p2.entity_id in parents_p1: return True
        if parents_p1 and parents_p2 and parents_p1.intersection(parents_p2): return True
        return False

    def _calcular_compatibilidad(self, p1, p2) -> float:
        # Uso estricto de la API Genética
        soc1, soc2 = p1.genome.sociability, p2.genome.sociability
        temp1, temp2 = p1.genome.temperament, p2.genome.temperament
        
        afinidad = 1.0 - ((abs(soc1 - soc2) + abs(temp1 - temp2)) / 2.0)
        dif_edad = abs(p1.age - p2.age)
        factor_edad = max(0.2, 1.0 - (dif_edad * 0.02)) if dif_edad > 15 else 1.0
        return afinidad * factor_edad

    def process(self, state: WorldState, pending: PendingChanges, delta_days: int) -> None:
        cfg = state.config.marriage
        all_persons = state.get_all_persons()
        
        # Filtros básicos de solteros vivos
        solteros = [p for p in all_persons if p.age >= cfg["min_marriage_age"] 
                    and p.marital_status != "casado" 
                    and p.entity_id not in pending.deaths]
        
        solteros_m = [p for p in solteros if p.gender == "M"]
        solteros_f = [p for p in solteros if p.gender == "F"]

        if not solteros_m or not solteros_f: return
        
        # Normalización temporal: probabilidad acumulada en delta_days
        base_daily_chance = cfg.get("base_marriage_chance", 0.01)
        total_marriage_chance = 1 - ((1 - base_daily_chance) ** delta_days)
        
        random.shuffle(solteros_m)
        comprometidos_hoy = set()

        for hombre in solteros_m:
            mejor_candidata, mejor_score, flechazo = None, -1.0, False

            for mujer in solteros_f:
                if mujer.entity_id in comprometidos_hoy: continue
                # Validación espacial: usamos el estado actual
                if abs(hombre.x - mujer.x) > cfg["courtship_radius"] or \
                   abs(hombre.y - mujer.y) > cfg["courtship_radius"]: continue
                if self._es_incesto(hombre, mujer): continue

                # Flechazo (probabilidad diaria)
                flechazo_diario = cfg.get("love_at_first_sight_chance", 0.001)
                total_flechazo = 1 - ((1 - flechazo_diario) ** delta_days)
                
                if random.random() < total_flechazo:
                    mejor_candidata, flechazo = mujer, True
                    break

                score = self._calcular_compatibilidad(hombre, mujer)
                if score > mejor_score:
                    mejor_score, mejor_candidata = score, mujer

            if mejor_candidata:
                chance = 1.0 if flechazo else (total_marriage_chance * mejor_score)
                if random.random() < chance:
                    # AQUÍ ESTÁ LA DIFERENCIA CRÍTICA:
                    # Registramos el matrimonio en PendingChanges, NO en la persona
                    pending.register_marriage(hombre.entity_id, mejor_candidata.entity_id)
                    comprometidos_hoy.add(mejor_candidata.entity_id)
                    self.logger.info(f"Cortejo exitoso entre {hombre.entity_id} y {mejor_candidata.entity_id}")