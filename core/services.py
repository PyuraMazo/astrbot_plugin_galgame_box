import asyncio
from typing import Any, TypeVar

from astrbot.core import AstrBotConfig

from .command import *
from .function import *
from .network import *

T = TypeVar("T")


class Services:
    _services: dict[type, Any] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        async with cls._lock:
            cls._services[Http] = await Http.initialize(config)
            cls._services[Downloader] = await Downloader.initialize(config)
            cls._services[Vndb] = await Vndb.initialize(config)
            cls._services[TouchGal] = await TouchGal.initialize(config)
            cls._services[AnimeTrece] = await AnimeTrece.initialize(config)

            cls._services[Cache] = await Cache.initialize(config)

            cls._services[Vn] = await Vn.initialize(config)
            cls._services[Character] = await Character.initialize(config)
            cls._services[Producer] = await Producer.initialize(config)
            cls._services[VndbId] = await VndbId.initialize(config)
            cls._services[Event] = await Event.initialize(config)
            cls._services[Random] = await Random.initialize(config)
            cls._services[Recommend] = await Recommend.initialize(config)
            cls._services[Download] = await Download.initialize(config)
            cls._services[Find] = await Find.initialize(config)
            cls._services[EventTimed] = await EventTimed.initialize(config)

    @classmethod
    async def terminate(cls):
        await cls._services[Downloader].terminate()
        await cls._services[Http].terminate()
        await cls._services[Cache].terminate()

    @classmethod
    def get(cls, service_type: type[T]) -> T:
        if service_type not in cls._services:
            raise RuntimeError(f"{service_type}不存在。")
        return cls._services[service_type]
