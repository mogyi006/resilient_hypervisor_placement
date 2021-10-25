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

network_name = '37_cost'
max_vSDN_size = 19
hp_type = 'heuristics'
hp_objective = 'hypervisor count'
simulation_logs = []

possible_settings = {
    'network_name': [network_name],
    'latency_factor': np.arange(0.1, 1.1, 0.1),
    'shortest_k': [16],
    'hp_type': [hp_type],
    'hp_objective': [hp_objective],
    'repeat': [100],
}
param_names_1 = list(possible_settings.keys())
setting_generator = [
    dict(zip(param_names_1, x))
    for x in itertools.product(*possible_settings.values())
]

possible_request_settings = {
    'size_of_requests': range(2, max_vSDN_size),
    'count': [4000]
}
param_names_2 = list(possible_request_settings.keys())
request_setting_generator = [
    dict(zip(param_names_2, x))
    for x in itertools.product(*possible_request_settings.values())
]

for setting in tqdm.tqdm(setting_generator, total=len(setting_generator)):
    ns = NetworkSimulation(**setting)
    ns.init_simulation(**setting)
    ns.hypervisor_placement(**setting)
    for request_setting in request_setting_generator:
        ns.request_simulation(**request_setting)
        simulation_logs.append(ns.log_simulation())

with open(
        f"../results/{network_name}/{datetime.date.today()}-{network_name}-heu-hco.json",
        'w') as file:
    json.dump(simulation_logs,
              file,
              indent=4,
              sort_keys=True,
              separators=(', ', ': '),
              ensure_ascii=False,
              cls=NumpyEncoder)