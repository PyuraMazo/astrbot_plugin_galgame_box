from ..type.inner_models import CommandType


class Tips(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EarlyReturn(Tips):
    def __init__(self, message: str):
        super().__init__(message)


class InvalidArgsException(Tips):
    def __init__(self, _type: CommandType, _value: str):
        super().__init__(f"指令参数错误：{_type.value}-{_value}")


class SessionTimeoutException(Tips):
    def __init__(self, _type: CommandType, _value: str):
        super().__init__(f"等待结果超时，指令失效：{_type.value}-{_value}")


class ArgsOrNullException(Tips):
    def __init__(self, _type: CommandType, _value: str):
        super().__init__(f"参数错误或结果不存在：{_type.value}-{_value}")


class InternetException(Tips):
    def __init__(self, url: str):
        super().__init__(f"请求网络失败：{url}，请检查【安全配置】是否错误")


class AuthorityException(Tips):
    def __init__(self, msg: str):
        super().__init__(
            f"网络配置错误：网站返回信息为【{msg}】，这通常由【安全配置】配置错误导致"
        )


class ResponseException(Tips):
    def __init__(self, url: str):
        super().__init__(f"请求结果为空，网站返回内容错误：{url}")


class NoResultException(Tips):
    def __init__(self, _type: CommandType, _value: str):
        super().__init__(f"未搜索到内容：{_type.value}-{_value}")


class NoCacheException(Tips):
    def __init__(self, path: str):
        super().__init__(f"缓存不存在：{path}")


#
# class CodeException(Tips):
#     def __init__(self, code: int):
#         super().__init__(trace_code.get(code, f"异常返回码：{code}"))


class HasBoundException(Tips):
    def __init__(self, channel_id: str):
        super().__init__(f"你已经绑定了Steam账号：{channel_id}")


class NoBoundException(Tips):
    def __init__(self, channel_id: str):
        super().__init__(f"你还未绑定Steam账号：{channel_id}")


class SettingException(Tips):
    def __init__(self, setting: str):
        super().__init__(f"插件配置项错误：{setting}")
