import asyncio
from datetime import datetime
from typing import Awaitable, Callable, Dict, List

from .models import Event, EventType


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._queue: "asyncio.Queue[Event]" = asyncio.Queue()
        self._subscribers: Dict[EventType, List[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        handlers = self._subscribers.setdefault(event_type, [])
        handlers.append(handler)

    async def publish(self, event: Event) -> None:
        await self._queue.put(event)

    async def publish_now(self, event_type: EventType, payload: object) -> None:
        event = Event(type=event_type, payload=payload, timestamp=datetime.utcnow())
        await self.publish(event)

    async def run(self) -> None:
        while True:
            event = await self._queue.get()
            handlers = list(self._subscribers.get(event.type, []))
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    # Log error but keep bus running
                    print(f"Error handling event {event.type}: {e}")

