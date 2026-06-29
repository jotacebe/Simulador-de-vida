"""Punto de entrada de la aplicación.

Este archivo debe mantenerse deliberadamente pequeño. Su responsabilidad es
arrancar la simulación, no construir sistemas, fases ni lógica interna del
motor.
"""

from __future__ import annotations

import logging

from core.engine.simulation_engine import SimulationEngine


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    """Crea el motor por defecto y arranca la simulación."""

    engine = SimulationEngine.create_default()
    engine.run()


if __name__ == "__main__":
    main()