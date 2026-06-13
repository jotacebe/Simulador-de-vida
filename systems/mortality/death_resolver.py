"""Módulo responsable de la integridad de datos tras eventos de mortalidad."""

from core.state.pending_changes import PendingChanges
from core.state.world_state import WorldState

class DeathResolver:
    """Filtro de contingencia absoluta para purgar intenciones de entidades fallecidas."""

    @staticmethod
    def resolve(pending: PendingChanges, state: WorldState) -> None:
        """Examina las intenciones acumuladas y elimina toda referencia a agentes muertos.
        
        Esta limpieza es vital para evitar errores de referencia y comportamientos
        degenerados (como que un agente muerto se case o envejezca).
        """
        # Si no hay defunciones, no realizamos ninguna operación de limpieza.
        if not pending.deaths:
            return

        # Creamos un conjunto para optimizar las búsquedas de ID.
        muertos_set = set(pending.deaths)

        # 1. Cancelar movimientos: Un agente muerto no puede desplazarse.
        pending.movements = {
            e_id: coords for e_id, coords in pending.movements.items() 
            if e_id not in muertos_set
        }

        # 2. Cancelar envejecimiento: Los agentes no cumplen años el mismo tick que mueren.
        pending.age_increments = {
            e_id: inc for e_id, inc in pending.age_increments.items() 
            if e_id not in muertos_set
        }

        # 3. Cancelar infecciones: Eliminamos registros de contagio de los fallecidos.
        pending.infections = [
            e_id for e_id in pending.infections 
            if e_id not in muertos_set
        ]

        # 4. Cancelar Matrimonios: Si uno de los contrayentes muere, la unión se anula.
        matrimonios_limpios = {}
        for p_a, p_b in pending.marriages.items():
            if p_a not in muertos_set and p_b not in muertos_set:
                matrimonios_limpios[p_a] = p_b
        pending.marriages = matrimonios_limpios

        # 5. Cancelar Divorcios: Un proceso de divorcio se interrumpe si una parte muere.
        pending.divorces = [
            (pa, pb) for pa, pb in pending.divorces 
            if pa not in muertos_set and pb not in muertos_set
        ]