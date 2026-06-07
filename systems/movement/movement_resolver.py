"""
Ruta: systems/movement/movement_resolver.py
Responsabilidad: Evaluar y arbitrar conflictos espaciales antes del commit global.
                 Asegura que dos entidades no ocupen la misma celda si el motor no lo permite.
"""
import random
from core.state.world_state import WorldState
from core.state.pending_changes import PendingChanges

class MovementResolver:
    @staticmethod
    def resolve(pending: PendingChanges, state: WorldState) -> None:
        """
        Analiza las intenciones de movimiento acumuladas en 'pending.movements'
        y resuelve los cuellos de botella espaciales de forma determinista.
        """
        if not getattr(pending, 'movements', None):
            return  # Si nadie se mueve, no hay nada que resolver

        # 1. Identificar casillas bloqueadas (ocupadas por gente que NO se mueve)
        casillas_bloqueadas = set()
        for person in state.get_all_persons():
            # Los muertos no bloquean espacio
            if person.entity_id in pending.deaths:
                continue 
                
            # Si la persona no ha pedido moverse, su celda es intransitable en este tick
            if person.entity_id not in pending.movements:
                casillas_bloqueadas.add((person.x, person.y))

        # 2. Agrupar peticiones por celda destino
        peticiones_por_celda = {} 
        for entity_id, (target_x, target_y) in pending.movements.items():
            # Validar límites del mapa por seguridad física antes de agrupar
            final_x = max(0, min(int(target_x), state.width - 1))
            final_y = max(0, min(int(target_y), state.height - 1))
            destino = (final_x, final_y)
            
            if destino not in peticiones_por_celda:
                peticiones_por_celda[destino] = []
            peticiones_por_celda[destino].append(entity_id)

        # 3. Arbitrar conflictos
        movimientos_validados = {}
        for destino, candidatos in peticiones_por_celda.items():
            # REGLA A: Destino bloqueado por entidad estática
            if destino in casillas_bloqueadas:
                continue

            # REGLA B: Celda libre
            if len(candidatos) == 1:
                ganador = candidatos[0]
                movimientos_validados[ganador] = destino
            else:
                # CONFLICTO: Varios quieren la misma celda. Elegimos uno al azar.
                ganador = random.choice(candidatos)
                movimientos_validados[ganador] = destino

        # 4. REEMPLAZO ATÓMICO: 
        # Sobrescribimos el búfer solo con los movimientos que han sobrevivido.
        pending.movements = movimientos_validados