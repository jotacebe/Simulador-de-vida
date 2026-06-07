"""
Ruta: events/event_bus.py
Responsabilidad: Gestionar el patrón de publicación/suscripción para 
                 desacoplar los sistemas lógicos de las salidas (logs, UI, métricas).
"""

from typing import Callable, Any

class EventBus:
    def __init__(self):
        # Diccionario que mapea: TipoDeEvento -> [lista_de_funciones_suscriptas]
        self._subscribers = {}

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Registra una función (handler) para que se ejecute cuando ocurra un event_type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def publish(self, event: Any) -> None:
        """Recibe un evento y se lo pasa a todos los suscriptores interesados."""
        event_type = type(event)
        
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                handler(event)