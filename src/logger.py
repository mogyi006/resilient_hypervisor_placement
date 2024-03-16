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

def remove_int_keys(simulation_logs):
    if type(simulation_logs) is dict:
        return simulation_logs
    for log in simulation_logs:
        keys_to_remove = []
        for key in log.keys():
            if type(log[key]) is dict:
                for key2 in log[key].keys():
                    if type(key2) != str:
                        keys_to_remove.append(key)
                        break
        for key in keys_to_remove:
            del log[key]
    return simulation_logs

def save2json(path, data):
    data = remove_int_keys(data)
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

def load_json(path):
    with open(path, 'r') as file:
        data = json.load(file)
    return data