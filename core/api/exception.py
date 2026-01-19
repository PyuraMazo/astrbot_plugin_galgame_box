class InvalidArgsException(Exception):
    def __init__(self):
        self.message = '指令参数错误'
        super().__init__(self.message)

class SessionTimeoutException(Exception):
    def __init__(self):
        self.message = '等待结果超时，指令失效'
        super().__init__(self.message)


class ArgsOrNullException(Exception):
    def __init__(self):
        self.message = '参数错误或结果不存在'
        super().__init__(self.message)

class InternetException(Exception):
    def __init__(self, url: str = ''):
        self.message = '请求网络失败：' + url
        super().__init__(self.message)

class ResponseException(Exception):
    def __init__(self):
        self.message = '请求结果为空，网站返回内容错误'
        super().__init__(self.message)

class NoGameException(Exception):
    def __init__(self):
        self.message = '未搜索到内容'
        super().__init__(self.message)

class NoCacheException(Exception):
    def __init__(self):
        self.message = '缓存不存在'
        super().__init__(self.message)