from pydantic import BaseModel
from enum import Enum


class RenderedItem(BaseModel):
    sub_title: str
    image: str
    text: str


class RenderedProducer(BaseModel):
    column_info: str
    vns: list[RenderedItem]

class RenderedInfo(BaseModel):
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
    SELECT = 'select'

class CommandBody(BaseModel):
    type: CommandType
    value: str
    msg_id: str

class UnrenderedData(BaseModel):
    title: str
    items: list[RenderedItem | RenderedProducer | RenderedInfo]
    bg_image: str
    font: str

class TouchGalDetails(BaseModel):
    vndb_id: str
    images: list[str]
    description: str
