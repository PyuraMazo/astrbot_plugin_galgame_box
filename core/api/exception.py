from .const import trace_code

class Tips(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)

class InvalidArgsException(Tips):
    def __init__(self, cmd: str):
        super().__init__(f'指令参数错误：{cmd}')

class SessionTimeoutException(Tips):
    def __init__(self, cmd: str):
        super().__init__(f'等待结果超时，指令失效：{cmd}')


class ArgsOrNullException(Tips):
    def __init__(self, cmd: str):
        super().__init__(f'参数错误或结果不存在：{cmd}')

class InternetException(Tips):
    def __init__(self, url: str):
        super().__init__(f'请求网络失败：{url}')

class ResponseException(Tips):
    def __init__(self, url: str):
        super().__init__(f'请求结果为空，网站返回内容错误：{url}')

class NoResultException(Tips):
    def __init__(self, cmd: str):
        super().__init__(f'未搜索到内容：{cmd}')

class NoCacheException(Tips):
    def __init__(self, path: str):
        super().__init__(f'缓存不存在：{path}')

class CodeException(Tips):
    def __init__(self, code: int):
        super().__init__(trace_code.get(code, f'API返回码异常：{code}'))
