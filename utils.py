
def call_handler(handler, **kwargs):
    import inspect
    sig = inspect.signature(handler)
    params = sig.parameters

    filtered_params = {name: value for name, value in kwargs.items() if name in params}

    return handler(**filtered_params)
