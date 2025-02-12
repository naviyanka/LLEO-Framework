from typing import Dict, List, Callable, Any
import asyncio
import logging

class EventBus:
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)

    def subscribe(self, event: str, handler: Callable) -> None:
        """Subscribe a handler to an event"""
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(handler)
        self.logger.debug(f"Subscribed handler to event: {event}")

    def unsubscribe(self, event: str, handler: Callable) -> None:
        """Unsubscribe a handler from an event"""
        if event in self.handlers and handler in self.handlers[event]:
            self.handlers[event].remove(handler)
            self.logger.debug(f"Unsubscribed handler from event: {event}")

    async def emit(self, event: str, data: Any = None) -> None:
        """Emit an event with optional data"""
        if event in self.handlers:
            self.logger.debug(f"Emitting event: {event}")
            tasks = []
            for handler in self.handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        tasks.append(asyncio.create_task(handler(data)))
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event}: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def clear(self) -> None:
        """Clear all event handlers"""
        self.handlers.clear()
        self.logger.debug("Cleared all event handlers") 