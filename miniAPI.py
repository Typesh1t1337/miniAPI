import socket
from enum import Enum
from typing import Callable, Optional, Dict, Any


HOST = "localhost"
PORT = 8080


class ResponseCode(Enum):
    ok = 200
    not_found = 404
    server_error = 500
    bad_request = 400
    forbidden = 403


class Method(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class Request:
    def __init__(self, param: Optional[str] = None, json: Optional[Dict[str, Any]] = None):
        self.param = param
        self.json = json


class Response:
    def __init__(self, json_response: Dict[str, Any] = None, status_code: ResponseCode = ResponseCode.ok):
        json_response = json_response
        status_code = status_code


# callable handler
Handler = Callable[[Request], Response]


class Server:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.routes = {}

    def add_route(self, path: str, method: Method, func: Handler) -> None:
        if (path, method) in self.routes:
            raise KeyError(f"Duplicate route: {(path, method)}")
        self.routes[(path, method)] = func


