"""
Ruta: systems/mortality/death_resolver.py
Responsabilidad: Filtro de contingencia absoluta. Limpia cualquier intención 
                 futura de una entidad si esta se encuentra en la lista de defunciones.
"""
from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState

class DeathResolver:
    @staticmethod
    def resolve(pending: PendingChanges, state: WorldState) -> None:
        """
        Examina las intenciones acumuladas y purga las acciones de los fallecidos.
        """
        if not pending.deaths:
            return  # Si nadie muere en este tick, no hay conflictos de este tipo que resolver.

        muertos_set = set(pending.deaths)

        # 1. Cancelar movimientos
        pending.movements = {
            e_id: coords for e_id, coords in pending.movements.items() 
            if e_id not in muertos_set
        }

        # 2. Cancelar envejecimiento (no puedes cumplir años el mismo tick que mueres)
        pending.age_increments = {
            e_id: inc for e_id, inc in pending.age_increments.items() 
            if e_id not in muertos_set
        }

        # 3. Cancelar infecciones simultáneas (si mueres y te contagias a la vez)
        pending.infections = [
            e_id for e_id in pending.infections 
            if e_id not in muertos_set
        ]

        # 4. Cancelar Matrimonios
        # Si A iba a casarse con B, pero A muere, anulamos el matrimonio para ambos.
        matrimonios_limpios = {}
        for p_a, p_b in pending.marriages.items():
            if p_a not in muertos_set and p_b not in muertos_set:
                matrimonios_limpios[p_a] = p_b
        pending.marriages = matrimonios_limpios

        # 5. Cancelar Divorcios en progreso
        pending.divorces = [
            (pa, pb) for pa, pb in pending.divorces 
            if pa not in muertos_set and pb not in muertos_set
        ]

        # 6. Cancelar actualizaciones de embarazo si la gestante muere
        pending.pregnancy_updates = {
            e_id: data for e_id, data in pending.pregnancy_updates.items() 
            if e_id not in muertos_set
        }