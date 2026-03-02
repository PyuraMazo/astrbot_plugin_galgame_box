from .const import trace_code
from .type import CommandBody


class Tips(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class InvalidArgsException(Tips):
    def __init__(self, cmd: CommandBody):
        _cmd = f"{cmd.type}-{cmd.value}"
        super().__init__(f"指令参数错误：{_cmd}")


class SessionTimeoutException(Tips):
    def __init__(self, cmd: CommandBody):
        _cmd = f"{cmd.type}-{cmd.value}"
        super().__init__(f"等待结果超时，指令失效：{_cmd}")


class ArgsOrNullException(Tips):
    def __init__(self, cmd: CommandBody):
        _cmd = f"{cmd.type}-{cmd.value}"
        super().__init__(f"参数错误或结果不存在：{_cmd}")


class InternetException(Tips):
    def __init__(self, url: str):
        super().__init__(f"请求网络失败：{url}")


class ResponseException(Tips):
    def __init__(self, url: str):
        super().__init__(f"请求结果为空，网站返回内容错误：{url}")


class NoResultException(Tips):
    def __init__(self, cmd: CommandBody | str):
        _cmd = f"{cmd.type}-{cmd.value}" if isinstance(cmd, CommandBody) else cmd
        super().__init__(f"未搜索到内容：{_cmd}")


class NoCacheException(Tips):
    def __init__(self, path: str):
        super().__init__(f"缓存不存在：{path}")


class CodeException(Tips):
    def __init__(self, code: int):
        super().__init__(trace_code.get(code, f"API返回码异常：{code}"))


class HasBoundException(Tips):
    def __init__(self, channel_id: str):
        super().__init__(f"你已经绑定了Steam账号：{channel_id}")


class NoBoundException(Tips):
    def __init__(self, channel_id: str):
        super().__init__(f"你还未绑定Steam账号：{channel_id}")
