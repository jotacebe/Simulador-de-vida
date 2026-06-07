"""
Ruta: core/engine/tick_manager.py
Responsabilidad: Controlar el avance del tiempo biológico interno y su conversión a tiempo visible.
                 Garantiza la causalidad temporal estricta y soporta escalas dinámicas en días continuos,
                 permitiendo que un tick dure cualquier cantidad de días configurada por el usuario o la UI.
"""
import logging
from typing import Optional

class TickManager:
    """
    Gestor central del tiempo de la simulación.
    Mantiene el contador de ticks del motor y calcula los ciclos y fechas visibles
    adaptándose a cualquier duración de tick de forma continua y escalable.
    """

    def __init__(self, initial_days_per_tick: float = 30.0, start_year: int = 1) -> None:
        """
        Inicializa el gestor del tiempo basándose puramente en días continuos.
        """
        self._current_tick: int = 0
        self._days_per_tick: float = float(initial_days_per_tick)
        
        # El núcleo absoluto del tiempo: días simulados acumulados en formato flotante
        self._total_simulated_days: float = 0.0
        self._start_year: int = start_year
        
        # Sincronizado estrictamente con el estándar del simulador (1 año = 365 días puros)
        self._days_per_visible_cycle: float = 365.0 
        
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.debug(f"TickManager inicializado con una escala base de: {self._days_per_tick} días por tick.")

    @property
    def current_tick(self) -> int:
        """Propiedad de solo lectura para obtener el tick del motor actual."""
        return self._current_tick

    @property
    def days_per_tick(self) -> float:
        """Devuelve los días asignados a cada tick actual."""
        return self._days_per_tick

    @property
    def total_simulated_days(self) -> float:
        """Devuelve el total de días biológicos transcurridos en el mundo."""
        return self._total_simulated_days

    def set_tick_duration(self, days: float) -> None:
        """
        Permite cambiar la duración real de un tick en caliente a través de la UI.
        Soporta cualquier ejemplo: 1.0 (un día), 30.0 (un mes), 365.0 (un año), 365000.0 (mil años).
        """
        if days <= 0:
            raise ValueError("La duración del tick en días debe ser estrictamente mayor que cero.")
        self._logger.info(f"Escala de tiempo modificada dinámicamente: {self._days_per_tick} -> {days} días por tick.")
        self._days_per_tick = float(days)

    @property
    def current_visible_cycle(self) -> int:
        """
        Calcula el ciclo visible (años acumulados) basado en los días reales transcurridos.
        Garantiza la consistencia exacta aunque cambies el paso del tiempo radicalmente a mitad de ejecución.
        """
        return int(self._total_simulated_days // self._days_per_visible_cycle)

    @property
    def is_new_visible_cycle(self) -> bool:
        """Indica si en este tick exacto se ha completado un año exacto en la simulación."""
        if self._total_simulated_days == 0:
            return False
        return int(self._total_simulated_days % self._days_per_visible_cycle) == 0

    def advance_tick(self, custom_delta_days: Optional[float] = None) -> float:
        """
        Avanza el reloj del motor en un tick incrementando los días correspondientes.
        Permite inyectar opcionalmente un valor dinámico directamente desde la ejecución.
        
        Returns:
            float: El delta_days exacto aplicado en esta iteración.
        """
        self._current_tick += 1
        
        # Prioriza un delta manual inyectado; de lo contrario, utiliza la duración configurada
        delta_days = float(custom_delta_days) if custom_delta_days is not None else self._days_per_tick
        self._total_simulated_days += delta_days
        
        self._logger.debug(
            f"Tiempo avanzado: Tick {self._current_tick} | (+{delta_days} días) | "
            f"Total acumulado: {self._total_simulated_days} días | Año UI: {self.current_visible_cycle + self._start_year}"
        )
        return delta_days

    def get_formatted_date(self) -> dict:
        """
        Traduce los días totales acumulados a una estructura de calendario legible para la UI.
        Normalizado bajo el estándar real y biológico de 365 días por año.
        """
        passed_years = int(self._total_simulated_days // 365)
        remainder_days = self._total_simulated_days % 365
        
        current_year = self._start_year + passed_years
        
        # Un mes exacto promedio equivale a 365 / 12 = 30.4166 días
        current_month = int(remainder_days // 30.4166) + 1
        current_day = int(remainder_days % 30.4166) + 1
        
        return {
            "tick": self._current_tick,
            "year": current_year,
            "month": current_month,
            "day": current_day,
            "days_per_tick": self._days_per_tick
        }

    def load_from_snapshot(self, saved_tick: int, saved_days: float) -> None:
        """Restaura el tiempo interno desde un archivo de guardado sin perder decimales."""
        if saved_tick < 0 or saved_days < 0:
            raise ValueError("Los valores de restauración no pueden ser negativos.")
            
        self._current_tick = saved_tick
        self._total_simulated_days = float(saved_days)
        self._logger.info(f"Tiempo restaurado desde guardado. Tick: {self._current_tick} | Días: {self._total_simulated_days}")

    def reset(self) -> None:
        """Reinicia el tiempo a cero."""
        self._current_tick = 0
        self._total_simulated_days = 0.0
        self._logger.info("El gestor del tiempo ha sido reiniciado por completo.")