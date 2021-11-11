# Standard library imports.
import datetime
import itertools
import json

# Related third party imports.
import numpy as np
import tqdm

# Local application/library specific imports.
from src.models.network_simulation import NetworkSimulation
from src.data.json_encoder import NumpyEncoder

networks = [('25_italy', 14), ('26_usa', 14), ('37_cost', 19),
            ('50_germany', 19)]
network_name, max_vSDN_size = networks[2]
hp_type = 'ilp'
hp_objective = 'acceptance ratio'
simulation_logs = []

possible_settings = {
    'network_name': [network_name],
    'latency_factor': np.arange(0.1, 1.1, 0.1),
    'shortest_k': [16],
    'hp_type': [hp_type],
    'hp_objective': [hp_objective],
    'hp_repeat': [10],
    'repeat': [100],
    'max_request_size': [max(2, int(max_vSDN_size / 2))],
    'vSDN_count_ilp': [100],
}
param_names_1 = list(possible_settings.keys())
setting_generator = [
    dict(zip(param_names_1, x))
    for x in itertools.product(*possible_settings.values())
]

possible_request_settings = {
    'request_size': range(2, max_vSDN_size),
    'count': [100]
}

for setting in tqdm.tqdm(setting_generator, total=len(setting_generator)):
    ns = NetworkSimulation(**setting)
    ns.init_simulation(**setting)
    ns.run_static_simulation(
        possible_request_settings=possible_request_settings, **setting)
    simulation_logs.extend(ns.get_logs())

with open(
        f"../results/{network_name}/{datetime.date.today()}-{network_name}-{hp_type[:3]}-acc.json",
        'w') as file:
    json.dump(simulation_logs,
              file,
              indent=4,
              sort_keys=True,
              separators=(', ', ': '),
              ensure_ascii=False,
              cls=NumpyEncoder)