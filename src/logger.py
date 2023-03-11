# Standard library imports.
import functools
import time
import json

# Related third party imports.

# Local application/library specific imports.
from src.data.json_encoder import NumpyEncoder


def measure(func):
    @functools.wraps(func)
    def _time_it(*args, **kwargs):
        start = time.perf_counter()
        try:
            returned = func(*args, **kwargs)
        finally:
            runtime = time.perf_counter() - start
            # print(f"{func.__name__}: {runtime if runtime > 0 else 0} s")
            return returned, runtime

    return _time_it


def save2json(path, data):
    with open(path, 'w') as file:
        json.dump(
            data,
            file,
            # default=lambda o: f"<<non-serializable>>: {type(o).__qualname__}",
            default=str,
            indent=4,
            sort_keys=True,
            separators=(', ', ': '),
            ensure_ascii=False,
            cls=NumpyEncoder)
