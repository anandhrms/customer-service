from abc import ABC, abstractmethod
from typing import Any


class BaseBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any:
        ...

    @abstractmethod
    async def set(self, response: Any, key: str, ttl: int = 60) -> None:
        ...

    @abstractmethod
    async def delete_startswith(self, value: str) -> None:
        ...

    @abstractmethod
    async def subscribe(self, channel: str) -> Any:
        ...

    @abstractmethod
    async def publish(self, channel: str, message: str) -> None:
        ...

    @abstractmethod
    async def unsubscribe(self, pubsub: Any, channel: str) -> None:
        ...
