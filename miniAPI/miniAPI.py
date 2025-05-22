import json
import socket
from enum import Enum
from typing import Callable, Optional, Dict, Any, Tuple
from .utils import call_handler, response_logger, parse_request_body
from .middleware import BaseMiddleware

HOST = "localhost"
PORT = 8080


class ResponseCode(Enum):
    ok = 200
    not_found = 404
    server_error = 500
    bad_request = 400
    forbidden = 403


REASON_PHRASES = {
    ResponseCode.ok: "OK",
    ResponseCode.not_found: "Not Found",
    ResponseCode.server_error: "Internal Server Error",
    ResponseCode.bad_request: "Bad Request",
    ResponseCode.forbidden: "Forbidden",
}


class Method(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


METHOD_ENUM_COMPARE = {
    "GET": Method.GET,
    "POST": Method.POST,
    "PUT": Method.PUT,
    "PATCH": Method.PATCH,
    "DELETE": Method.DELETE,
}


class Request:
    def __init__(self, param: Optional[str] = None, payload: Optional[Dict[str, Any]] = None):
        self.param = param
        self.payload = payload if payload is not None else {}


class Response:
    def __init__(self, json_response: Dict[str, Any] = None, status_code: ResponseCode = ResponseCode.ok):
        self.json_response = json_response
        self.status_code = status_code

    def to_http(self):
        body = json.dumps(self.json_response or {})
        status = f"HTTP/1.1 {self.status_code.value} {REASON_PHRASES[self.status_code]}\r\n"
        headers = f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
        return status + headers + body


# callable handler
Handler = Callable[[Optional[Request]], Response]


class Router:
    def __init__(self, prefix: str):
        self.prefix: str = prefix
        self.__handlers: Dict[Tuple[str, Method], Handler] = {}
        self.__check_route(prefix=prefix)

    @staticmethod
    def __check_route(prefix: str):
        if not prefix.startswith("/") or prefix.endswith("/"):
            raise KeyError(f"Prefix should start with '/'")  # /api/v1 example

    def add_handler(self, path: str, method: Method, handler: Handler):
        full_path = self.prefix + path
        if (full_path, method) in self.__handlers:
            raise KeyError(f"Duplicate route: {(full_path, method)}")

        self.__handlers[(full_path, method)] = handler

    @property
    def get_handlers(self):
        return self.__handlers


class MiniAPI:
    def __init__(self, debug: bool = True):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__handlers: Dict[Tuple[str, Method], Handler] = {}
        self.__middlewares = {}
        self.debug: bool = debug

    def add_handler(self, path: str, method: Method, handler: Handler) -> None:
        if (path, method) in self.__handlers:
            raise KeyError(f"Duplicate route: {(path, method)}")
        self.__handlers[(path, method)] = handler

    def add_router(self, router_handlers: Dict[Tuple[str, Method], Handler]) -> None:
        for (path, method), handler in router_handlers.items():
            if (path, method) in self.__handlers:
                raise KeyError(f"Duplicate route: {(path, method)}")
            self.__handlers[(path, method)] = handler

    def add_middleware(self, middleware: BaseMiddleware) -> None:
        self.__middlewares[middleware.__name__] = middleware

    def run(self):
        self.__socket.bind((HOST, PORT))
        self.__socket.listen()
        print(f"Server listening on {HOST}:{PORT}")
        self.__serve_forever()

    def __serve_forever(self):
        while True:
            conn, addr = self.__socket.accept()
            try:
                request_raw = conn.recv(4096).decode("utf-8")
                method_str, path, body = request_raw.split("\r\n")[0].split()

                method = METHOD_ENUM_COMPARE.get(method_str, None)

                request_lines, headers, body = parse_request_body(request_raw)

                if method is None:
                    response = Response(
                        {
                            "error": f"Method {method_str} not supported",
                        }, ResponseCode.forbidden
                    )
                    response_logger(path=path, method=method_str, status_code=response.status_code.value,
                                    reason_phrase=REASON_PHRASES.get(response.status_code))
                    self.__send_response(conn, response)
                    continue

                handler = self.__handlers.get((path, method), None)
                if not handler:
                    available_methods_for_handler = [h for h in Method if (path, h) in self.__handlers]
                    if available_methods_for_handler and available_methods_for_handler[0].value != method_str:
                        response = Response(
                            {
                                "error": f"Method {method_str} not supported",
                            }, status_code=ResponseCode.bad_request
                        )
                        response_logger(path=path, method=method_str,
                                        status_code=response.status_code.value,
                                        reason_phrase=REASON_PHRASES.get(response.status_code))
                        self.__send_response(conn, response)
                        continue

                    response = Response(
                        {
                            "error": f"Not found",
                        }, ResponseCode.not_found
                    )
                    response_logger(path=path, method=method.value,
                                    status_code=response.status_code.value,
                                    reason_phrase=REASON_PHRASES.get(response.status_code))
                    self.__send_response(conn, response)
                    continue

                try:
                    parsed_body = json.loads(body)
                    request = Request(payload=parsed_body)
                    response = call_handler(handler, request=request)

                    if not isinstance(response, Response):
                        raise TypeError("Handler should return Response")

                    response_logger(path=path, method=method_str,
                                    status_code=response.status_code.value,
                                    reason_phrase=REASON_PHRASES.get(response.status_code)
                                    )
                    self.__send_response(conn, response)

                except json.JSONDecodeError as e:
                    if self.debug:
                        raise
                    response = Response(
                        {
                            "error": str(e),
                        }, ResponseCode.bad_request
                    )

                    response_logger(path=path, method=method_str, status_code=response.status_code.value,
                                    reason_phrase=REASON_PHRASES.get(response.status_code)
                                    )
                except Exception:
                    if self.debug:
                        raise

                    response = Response(
                        {
                            "error": "Internal Server Error",
                        }, ResponseCode.server_error
                    )
                    response_logger(path=path, method=method.value,
                                    status_code=response.status_code.value,
                                    reason_phrase=REASON_PHRASES.get(response.status_code))
                    self.__send_response(conn, response)

            except Exception as e:
                fallback = Response({"error": "Malformed Request", "detail": str(e)}, ResponseCode.bad_request)
                self.__send_response(conn, fallback)

            finally:
                conn.close()

    @staticmethod
    def __send_response(conn: socket.socket, response: Response):
        conn.sendall(response.to_http().encode("utf-8"))
