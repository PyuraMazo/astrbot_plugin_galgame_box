from typing import Optional
from pydantic import BaseModel


class Image(BaseModel):
    url: str


class Developer(BaseModel):
    id: str
    original: Optional[str] = None
    name: str


class Title(BaseModel):
    lang: str
    title: str
    official: bool


class Vn(BaseModel):
    id: str
    alttitle: Optional[str] = None
    title: Optional[str] = None
    image: Optional[Image] = None
    rating: Optional[float] = None


class Tag(BaseModel):
    tag: dict


class DetectedInfo(BaseModel):
    work: str
    character: str


class AnimeTraceData(BaseModel):
    box: tuple[float, float, float, float]
    not_confident: bool
    character: list[DetectedInfo]


class Extlink(BaseModel):
    id: str
    label: str


class VNDBVnResponse(BaseModel):
    id: str
    rating: Optional[float] = None
    released: Optional[str] = None
    alttitle: Optional[str] = None
    title: str
    image: Image
    average: Optional[float] = None
    length_minutes: Optional[int] = None
    platforms: Optional[list[str]] = None
    aliases: Optional[list[str]] = None
    developers: Optional[list[Developer]] = None
    titles: Optional[list[Title]] = None


class VNDBCharacterResponse(BaseModel):
    id: str
    name: str
    original: Optional[str] = None
    birthday: Optional[list[int]] = None
    image: Optional[Image] = None
    vns: Optional[list[Vn]] = None
    aliases: Optional[list[str]] = None
    sex: Optional[list[str]] = None
    waist: Optional[int] = None
    hips: Optional[int] = None
    bust: Optional[int] = None
    blood_type: Optional[str] = None
    weight: Optional[int] = None
    height: Optional[int] = None
    cup: Optional[str] = None


class VNDBProducerResponse(BaseModel):
    id: str
    name: str
    original: Optional[str] = None
    aliases: Optional[list[str]] = None
    lang: Optional[str] = None
    type: Optional[str] = None


class TouchGalResponse(BaseModel):
    """
    id为TouchGal的全局ID
    unique_id为作品ID，可以访问对应页面
    """

    id: int
    unique_id: str
    banner: str
    name: str
    type: list[str]
    language: list[str]
    platform: list[str]
    averageRating: float
    tag: list[Tag]


class ResourceResponse(BaseModel):
    id: int
    name: str
    section: str
    storage: str
    size: str
    type: list[str]
    language: list[str]
    note: str
    content: str
    code: str
    password: str
    platform: list[str]


class AnimeTraceResponse(BaseModel):
    code: int
    data: list[AnimeTraceData]
    ai: bool


class SteamGameResponse(BaseModel):
    appid: int
    name: str
    playtime_forever: int
    rtime_last_played: Optional[int] = 0


class SteamOwnerResponse(BaseModel):
    game_count: int
    games: list[SteamGameResponse]


class SteamProfileResponse(BaseModel):
    steamid: str
    personaname: str
    avatarfull: str
    lastlogoff: int
    timecreated: int


class SteamAchievementsResponse(BaseModel):
    apiname: str
    achieved: int
    unlocktime: int


class VNDBReleaseResponse(BaseModel):
    id: str
    extlinks: list[Extlink]
    vns: list[Vn]
