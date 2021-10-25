# Standard library imports.
import functools
import time

# Related third party imports.

# Local application/library specific imports.


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