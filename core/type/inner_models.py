from asyncio import Event
from enum import Enum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict

from .outer_models import TouchGalResponse

bs64: TypeAlias = str


class CommandType(Enum):
    VN = "vn"
    CHARACTER = "character"
    PRODUCER = "producer"
    ID = "id"
    EVENT = "event"
    RANDOM = "random"
    DOWNLOAD = "download"
    SELECT = "select"
    FIND = "find"
    RECOMMEND = "recommend"
    BIND = "bind"
    PUZZLE = "puzzle"
    EVENT_TIMED = "event_timed"


class TouchGalDetails(BaseModel):
    third_info: list[str]
    previews: list[str]
    description: str
    title: str


class RecommendCache(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tasks_remaining_queue: list[TouchGalResponse]
    ready_queue: list[str]
    total: int
    handling: int  # 1开始
    ready_signal: Event
    use_signal: Event
    stop_signal: Event
    stop_info: str | None = None


template_list = {
    "vn": "template1.html",
    "character": "template1.html",
    "producer": "template2.html",
    "event": "template2.html",
    "random": "template3.html",
    "recommend": "template3.html",
    "find": "template2.html",
    "event_timed": "template3.html",
}

vndb_command_fields = {
    "vn": "id,average,rating,released,length_minutes,platforms,aliases,developers{id,original,name},titles{lang,title,official},image{url},alttitle,title",
    "character": "id,name,aliases,sex,birthday,waist,hips,bust,blood_type,weight,height,cup,original,image{url},vns{id,alttitle,title}",
    "producer": "id,name,original,aliases,lang,type",
    "vn_short": "id,alttitle,title,released,rating,image{url}",
    "character_short": "id,name,original,aliases,image{url},vns{id,alttitle,title}",
    "release": "id,alttitle,title,extlinks{id,label},vns{id,image{url}}",
    "character_event": "id,name,aliases,birthday,original,image{url}",
}

id2command = {
    "v": CommandType.VN,
    "c": CommandType.CHARACTER,
    "p": CommandType.PRODUCER,
}

lang = {"ja": "日文", "en": "英文", "zh-Hans": "简中", "zh-Hant": "繁中", "zh": "中文"}

develop_type = {"co": "公司", "in": "个人", "ng": "业余团体"}

gender = {"m": "男性", "f": "女性", "b": "双性", "n": "无性"}

ja_weeks = ["月", "火", "水", "木", "金", "土", "日"]

mime_type = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "avif": "image/avif",
    "ttf": "font/ttf",
}
