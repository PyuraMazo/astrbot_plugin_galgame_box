import asyncio
from typing import Any, TypeVar

from astrbot.core import AstrBotConfig

T = TypeVar("T")


class Services:
    _services: dict[type, Any] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def initialize(cls, config: AstrBotConfig):
        async with cls._lock:
            from .command import (
                Character,
                Download,
                Event,
                EventTimed,
                Find,
                Producer,
                Random,
                Recommend,
                Vn,
                VndbId,
            )
            from .function import Cache
            from .network import AnimeTrece, Downloader, Http, TouchGal, Vndb

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
    def get(cls, service_type: type[T]) -> T:
        if service_type not in cls._services:
            raise RuntimeError(f"{service_type}不存在。")
        return cls._services[service_type]
