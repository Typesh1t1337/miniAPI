import json
import socket
from enum import Enum
from typing import Callable, Optional, Dict, Any

from utils import call_handler

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


class MiniAPI:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__routes: Dict[(str, Method), Handler] = {}

    def add_route(self, path: str, method: Method, func: Handler) -> None:
        if (path, method) in self.__routes:
            raise KeyError(f"Duplicate route: {(path, method)}")
        self.__routes[(path, method)] = func

    def run(self):
        self.__socket.bind((HOST, PORT))
        self.__socket.listen()
        print(f"Server listening on {HOST}:{PORT}")
        self.__serve_forever()

    def __serve_forever(self):
        while True:
            conn, addr = self.__socket.accept()
            try:
                request_raw = conn.recv(1024).decode("utf-8")
                method_str, path, _ = request_raw.split("\r\n")[0].split()

                method = METHOD_ENUM_COMPARE.get(method_str, None)

                if method is None:
                    response = Response(
                        {
                            "error": f"Method {method_str} not supported",
                        }, ResponseCode.forbidden
                    )
                    self.__send_response(conn, response)
                    continue

                handler = self.__routes.get((path, method))
                if not callable(handler):
                    response = Response(
                        {
                            "error": f"Not found",
                        }, ResponseCode.not_found
                    )
                    self.__send_response(conn, response)

                request = Request()  # заглушка нужно спарсить payload, params,

                try:
                    response = call_handler(handler, request=request)
                    if not isinstance(response, Response):
                        raise TypeError("Handler should return Response")
                    self.__send_response(conn, response)
                except Exception:
                    response = Response(
                        {
                            "error": "Internal Server Error",
                        }, ResponseCode.server_error
                    )
                    self.__send_response(conn, response)
            except Exception as e:
                fallback = Response({"error": "Malformed Request", "detail": str(e)}, ResponseCode.bad_request)
                self.__send_response(conn, fallback)

            finally:
                conn.close()

    def __send_response(self, conn: socket.socket, response: Response):
        conn.sendall(response.to_http().encode("utf-8"))
