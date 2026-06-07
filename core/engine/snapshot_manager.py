"""
Ruta: core/engine/snapshot_manager.py
Responsabilidad: Serializar y deserializar el estado completo de la simulación 
                 para permitir guardados y cargas consistentes sin romper el tiempo.
"""
import pickle
import logging
from typing import Tuple
from core.state.world_state import WorldState
from core.engine.tick_manager import TickManager
from core.constants.enums import TimeScale

class SnapshotManager:
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def create_snapshot(self, state: WorldState, tick_manager: TickManager, filepath: str) -> bool:
        """Congela el estado exacto del mundo y el reloj interno en un archivo binario."""
        try:
            snapshot_data = {
                'world_state': state,
                'tick': tick_manager.current_tick,
                'total_days': tick_manager.total_simulated_days,
                'scale': tick_manager.current_scale
            }
            with open(filepath, 'wb') as f:
                pickle.dump(snapshot_data, f)
                
            self._logger.info(f"Snapshot determinista guardado en: {filepath}")
            return True
        except Exception as e:
            self._logger.error(f"Fallo crítico al crear snapshot: {e}")
            return False

    def load_snapshot(self, filepath: str) -> Tuple[WorldState, int, int, TimeScale]:
        """Recupera la simulación exactamente donde se dejó."""
        try:
            with open(filepath, 'rb') as f:
                snapshot_data = pickle.load(f)
                
            self._logger.info(f"Snapshot restaurado desde: {filepath}")
            return (
                snapshot_data['world_state'],
                snapshot_data['tick'],
                snapshot_data['total_days'],
                snapshot_data['scale']
            )
        except FileNotFoundError:
            self._logger.error(f"Archivo de guardado no encontrado: {filepath}")
            raise
        except Exception as e:
            self._logger.error(f"Archivo de guardado corrupto o incompatible: {e}")
            raise e