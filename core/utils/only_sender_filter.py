from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.session_waiter import SessionFilter


class OnlySenderFilter(SessionFilter):
    def filter(self, event: AstrMessageEvent) -> str:
        return (
            f"{event.get_platform_id()}:{event.get_group_id()}:{event.get_sender_id()}"
        )
