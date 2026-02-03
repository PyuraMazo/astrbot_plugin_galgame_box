from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

from astrbot.api.event import AstrMessageEvent, MessageEventResult


class RenderedItem(BaseModel):
    sub_title: str
    image: str
    text: str


class ColumnStyle(BaseModel):
    image: str
    title: str

class RenderedBlock(BaseModel):
    column_info: str | ColumnStyle
    vns: list[RenderedItem]

class RenderedRandom(BaseModel):
    sub_title: str
    main_image: str
    images: list[str]
    description: str
    text: str

class RenderedPuzzle(BaseModel):
    g: int
    game: str
    span: int
    img: str
    text: str



class CommandType(Enum):
    VN = 'vn'
    CHARACTER = 'character'
    PRODUCER = 'producer'
    ID = 'id'
    RANDOM = 'random'
    DOWNLOAD = 'download'
    SELECT = 'select'
    FIND = 'find'
    RECOMMEND = 'recommend'
    BIND = 'bind'
    SCHEDULE = 'schedule'

class CommandBody(BaseModel):
    type: CommandType
    value: str | list[str]
    event: AstrMessageEvent

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

class UnrenderedData(BaseModel):
    title: str
    items: list[RenderedItem | RenderedBlock | RenderedRandom | RenderedPuzzle]
    bg_image: str
    font: str
    main_image: Optional[str] = None

class TouchGalDetails(BaseModel):
    vndb_id: str
    images: list[str]
    description: str
    title: str


class AnimeTraceModel(Enum):
    Profession = 'full_game_model_kira'
    Common = 'animetrace_high_beta'

class SelectInfo(BaseModel):
    cmd_body: CommandBody
    cache: list[UnrenderedData]
    current: int
    total: int
    tmpl: str
    ready: Optional[str] = None

class SteamVnsInfo(BaseModel):
    name: str
    play_time: int
    achievement_rate: float | str
    last_play: int
    vndb_img: str
    rate: Optional[float] = None

class SteamData(BaseModel):
    channel_id: str
    steam_id: Optional[str] = None
    key: Optional[str] = None
    record: bool
    write_time: Optional[int] = None
    others_id: Optional[list[int]] = None
    vns: Optional[dict[int, SteamVnsInfo]] = None