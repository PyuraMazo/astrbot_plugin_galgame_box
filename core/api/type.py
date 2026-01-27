from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

from astrbot.api.event import AstrMessageEvent

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


class CommandType(Enum):
    VN = 'vn'
    CHARACTER = 'character'
    PRODUCER = 'producer'
    ID = 'id'
    RANDOM = 'random'
    DOWNLOAD = 'download'
    SELECT = 'select',
    FIND = 'find'

class CommandBody(BaseModel):
    type: CommandType
    value: str
    event: AstrMessageEvent

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

class UnrenderedData(BaseModel):
    title: str
    items: list[RenderedItem | RenderedBlock | RenderedRandom]
    bg_image: str
    font: str
    main_image: Optional[str] = None

class TouchGalDetails(BaseModel):
    vndb_id: str
    images: list[str]
    description: str


class AnimeTraceModel(Enum):
    Profession = 'full_game_model_kira'
    Common = 'animetrace_high_beta'