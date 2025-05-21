
def call_handler(handler, **kwargs):
    import inspect
    sig = inspect.signature(handler)
    params = sig.parameters

    filtered_params = {name: value for name, value in kwargs.items() if name in params}

    return handler(**filtered_params)


def response_logger(path, method, status_code, reason_phrase):
    from colorama import Fore, init

    init(autoreset=True)

    if 200 <= status_code < 300:
        color = Fore.LIGHTGREEN_EX
    elif 300 <= status_code < 400:
        color = Fore.YELLOW
    elif 400 <= status_code < 600:
        color = Fore.RED
    else:
        color = Fore.WHITE

    print(f"MiniAPI: {color}{path} {method} {status_code} {reason_phrase}")
