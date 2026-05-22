from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

from astrbot.api.event import AstrMessageEvent


class CommandType(Enum):
    VN = "vn"
    CHARACTER = "character"
    PRODUCER = "producer"
    ID = "id"
    EVENT = "galgame_event"
    RANDOM = "random"
    DOWNLOAD = "download"
    SELECT = "select"
    FIND = "find"
    RECOMMEND = "recommend"
    BIND = "bind"
    PUZZLE = "puzzle"
    GAL_EVENT = "galgame_event_pro"


class CommandBody(BaseModel):
    type: CommandType
    value: str | list[str]
    event: AstrMessageEvent | None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UnrenderedData(BaseModel):
    bg_image: str | None = None
    font: str | None = None
    current_title: str | None = None
    current_subtitle: str | None = None
    current_image: str | None = None
    current_desc: str | None = None
    extra_info: Any | None = None
    items: list["UnrenderedData"] | None = None


class TouchGalDetails(BaseModel):
    third_info: list[str]
    images: list[str]
    description: str
    title: str


class AnimeTraceModel(Enum):
    Profession = "full_game_model_kira"
    Common = "animetrace_high_beta"


class SelectInfo(BaseModel):
    cmd_body: CommandBody
    cache: list[UnrenderedData]
    current: int
    total: int
    tmpl: str
    ready: str | None = None


class SteamVnsInfo(BaseModel):
    name: str
    play_time: int
    vndb_img: str


class SteamData(BaseModel):
    platform_id: str
    steam_id: str | None = None
    key: str | None = None
    record: bool
    write_time: float | None = None
    others_id: list[int] | None = None
    vns: dict[int, SteamVnsInfo] | None = None
