"""Gestor de instantáneas (Snapshots) de la simulación.

Responsabilidad: Serializar y deserializar el estado completo de la simulación
para permitir persistencia transaccional, guardados y cargas consistentes
sin romper la línea temporal ni la coherencia del estado del mundo.
"""

from __future__ import annotations

import logging
import pickle

from core.engine.tick_manager import TickManager
from core.state.world_state import WorldState


class SnapshotManager:
    """Gestiona el volcado y restauración determinista del estado simétrico del mundo."""

    def __init__(self) -> None:
        """Inicializa el gestor de snapshots configurando su sistema de logging."""
        self._logger = logging.getLogger(self.__class__.__name__)

    def create_snapshot(
        self,
        state: WorldState,
        tick_manager: TickManager,
        filepath: str,
    ) -> bool:
        """Congela el estado exacto del mundo y el reloj interno en un archivo binario.

        Args:
            state: Estado actual y autoritativo del mundo.
            tick_manager: Gestor del reloj e índices temporales.
            filepath: Ruta física del sistema de archivos donde se guardará el snapshot.

        Returns:
            True si el proceso se consolidó correctamente; False en caso de fallo.
        """
        try:
            snapshot_data = {
                "world_state": state,
                "tick": tick_manager.current_tick,
                "total_days": tick_manager.total_simulated_days,
                "scale": tick_manager.days_per_tick,
            }
            with open(filepath, "wb") as f:
                pickle.dump(snapshot_data, f)

            self._logger.info("Snapshot determinista guardado en: %s", filepath)
            return True
        except Exception as e:
            self._logger.error("Fallo crítico al crear snapshot: %s", e)
            return False

    def load_snapshot(self, filepath: str) -> tuple[WorldState, int, float, float]:
        """Recupera el estado completo de la simulación exactamente donde se dejó.

        Args:
            filepath: Ruta del archivo binario a cargar.

        Returns:
            Una tupla conteniendo el WorldState restaurado, el tick numérico,
            los días totales transcurridos (float) y la escala de tiempo o días por tick (float).

        Raises:
            FileNotFoundError: Si la ruta especificada no existe en el disco.
            Exception: Si el archivo está corrupto o es incompatible con la versión actual.
        """
        try:
            with open(filepath, "rb") as f:
                snapshot_data = pickle.load(f)

            self._logger.info("Snapshot restaurado con éxito desde: %s", filepath)
            return (
                snapshot_data["world_state"],
                snapshot_data["tick"],
                snapshot_data["total_days"],
                snapshot_data["scale"],
            )
        except FileNotFoundError:
            self._logger.error("Archivo de guardado no encontrado: %s", filepath)
            raise
        except Exception as e:
            self._logger.error("Archivo de guardado corrupto o incompatible: %s", e)
            raise e