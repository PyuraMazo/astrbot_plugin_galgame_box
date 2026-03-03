from pydantic import BaseModel


class Image(BaseModel):
    url: str


class Developer(BaseModel):
    id: str
    original: str | None = None
    name: str


class Title(BaseModel):
    lang: str
    title: str
    official: bool


class Vn(BaseModel):
    id: str
    alttitle: str | None = None
    title: str | None = None
    image: Image | None = None
    rating: float | None = None


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
    rating: float | None = None
    released: str | None = None
    alttitle: str | None = None
    title: str
    image: Image
    average: float | None = None
    length_minutes: int | None = None
    platforms: list[str] | None = None
    aliases: list[str] | None = None
    developers: list[Developer] | None = None
    titles: list[Title] | None = None


class VNDBCharacterResponse(BaseModel):
    id: str
    name: str
    original: str | None = None
    birthday: list[int] | None = None
    image: Image | None = None
    vns: list[Vn] | None = None
    aliases: list[str] | None = None
    sex: list[str] | None = None
    waist: int | None = None
    hips: int | None = None
    bust: int | None = None
    blood_type: str | None = None
    weight: int | None = None
    height: int | None = None
    cup: str | None = None


class VNDBProducerResponse(BaseModel):
    id: str
    name: str
    original: str | None = None
    aliases: list[str] | None = None
    lang: str | None = None
    type: str | None = None


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
    rtime_last_played: int | None = 0


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
