from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ClientMessage(_message.Message):
    __slots__ = ("hello", "task_request", "response", "chunk", "task_result", "error")
    HELLO_FIELD_NUMBER: _ClassVar[int]
    TASK_REQUEST_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    TASK_RESULT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    hello: Hello
    task_request: TaskRequest
    response: HttpResponse
    chunk: HttpChunk
    task_result: TaskResult
    error: Error
    def __init__(self, hello: _Optional[_Union[Hello, _Mapping]] = ..., task_request: _Optional[_Union[TaskRequest, _Mapping]] = ..., response: _Optional[_Union[HttpResponse, _Mapping]] = ..., chunk: _Optional[_Union[HttpChunk, _Mapping]] = ..., task_result: _Optional[_Union[TaskResult, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class ServerMessage(_message.Message):
    __slots__ = ("task_accepted", "request", "extract_result")
    TASK_ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    EXTRACT_RESULT_FIELD_NUMBER: _ClassVar[int]
    task_accepted: TaskAccepted
    request: HttpRequest
    extract_result: ExtractResult
    def __init__(self, task_accepted: _Optional[_Union[TaskAccepted, _Mapping]] = ..., request: _Optional[_Union[HttpRequest, _Mapping]] = ..., extract_result: _Optional[_Union[ExtractResult, _Mapping]] = ...) -> None: ...

class Hello(_message.Message):
    __slots__ = ("device_id", "user_agent", "app_version", "cookies", "capabilities")
    class CapabilitiesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    USER_AGENT_FIELD_NUMBER: _ClassVar[int]
    APP_VERSION_FIELD_NUMBER: _ClassVar[int]
    COOKIES_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    user_agent: str
    app_version: str
    cookies: _containers.RepeatedCompositeFieldContainer[Cookie]
    capabilities: _containers.ScalarMap[str, str]
    def __init__(self, device_id: _Optional[str] = ..., user_agent: _Optional[str] = ..., app_version: _Optional[str] = ..., cookies: _Optional[_Iterable[_Union[Cookie, _Mapping]]] = ..., capabilities: _Optional[_Mapping[str, str]] = ...) -> None: ...

class TaskRequest(_message.Message):
    __slots__ = ("task_id", "url", "options")
    class OptionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    url: str
    options: _containers.ScalarMap[str, str]
    def __init__(self, task_id: _Optional[str] = ..., url: _Optional[str] = ..., options: _Optional[_Mapping[str, str]] = ...) -> None: ...

class TaskAccepted(_message.Message):
    __slots__ = ("task_id", "message")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    message: str
    def __init__(self, task_id: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class HttpRequest(_message.Message):
    __slots__ = ("request_id", "task_id", "method", "url", "headers", "body", "timeout_ms", "follow_redirects")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    FOLLOW_REDIRECTS_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    task_id: str
    method: str
    url: str
    headers: _containers.ScalarMap[str, str]
    body: bytes
    timeout_ms: int
    follow_redirects: bool
    def __init__(self, request_id: _Optional[str] = ..., task_id: _Optional[str] = ..., method: _Optional[str] = ..., url: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ..., body: _Optional[bytes] = ..., timeout_ms: _Optional[int] = ..., follow_redirects: bool = ...) -> None: ...

class HttpResponse(_message.Message):
    __slots__ = ("request_id", "task_id", "status", "headers", "body", "final_url")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    FINAL_URL_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    task_id: str
    status: int
    headers: _containers.ScalarMap[str, str]
    body: bytes
    final_url: str
    def __init__(self, request_id: _Optional[str] = ..., task_id: _Optional[str] = ..., status: _Optional[int] = ..., headers: _Optional[_Mapping[str, str]] = ..., body: _Optional[bytes] = ..., final_url: _Optional[str] = ...) -> None: ...

class HttpChunk(_message.Message):
    __slots__ = ("request_id", "task_id", "bytes", "eof")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    BYTES_FIELD_NUMBER: _ClassVar[int]
    EOF_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    task_id: str
    bytes: bytes
    eof: bool
    def __init__(self, request_id: _Optional[str] = ..., task_id: _Optional[str] = ..., bytes: _Optional[bytes] = ..., eof: bool = ...) -> None: ...

class ExtractResult(_message.Message):
    __slots__ = ("task_id", "info_json")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    INFO_JSON_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    info_json: str
    def __init__(self, task_id: _Optional[str] = ..., info_json: _Optional[str] = ...) -> None: ...

class TaskResult(_message.Message):
    __slots__ = ("task_id", "status", "message")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    status: str
    message: str
    def __init__(self, task_id: _Optional[str] = ..., status: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class Cookie(_message.Message):
    __slots__ = ("name", "value", "domain", "path", "expires_unix", "http_only", "secure")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_UNIX_FIELD_NUMBER: _ClassVar[int]
    HTTP_ONLY_FIELD_NUMBER: _ClassVar[int]
    SECURE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: str
    domain: str
    path: str
    expires_unix: int
    http_only: bool
    secure: bool
    def __init__(self, name: _Optional[str] = ..., value: _Optional[str] = ..., domain: _Optional[str] = ..., path: _Optional[str] = ..., expires_unix: _Optional[int] = ..., http_only: bool = ..., secure: bool = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("task_id", "request_id", "code", "message")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    request_id: str
    code: str
    message: str
    def __init__(self, task_id: _Optional[str] = ..., request_id: _Optional[str] = ..., code: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...
