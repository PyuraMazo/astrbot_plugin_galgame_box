from pydantic import BaseModel


class DetectedInfo(BaseModel):
    work: str
    character: str


class AnimeTraceData(BaseModel):
    box: tuple[float, float, float, float]
    not_confident: bool
    character: list[DetectedInfo]


class AnimeTraceResponse(BaseModel):
    code: int
    data: list[AnimeTraceData]
    ai: bool
    zh_message: str | None = None
