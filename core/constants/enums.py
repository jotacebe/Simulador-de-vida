"""
Ruta: core/constants/enums.py
"""
from enum import Enum

class TimeScale(Enum):
    DIARIO = 1      # 1 Tick = 1 Día
    SEMANAL = 7     # 1 Tick = 7 Días
    MENSUAL = 30    # 1 Tick = 30 Días
    ANUAL = 360     # 1 Tick = 360 Días (Año simplificado de simulación)