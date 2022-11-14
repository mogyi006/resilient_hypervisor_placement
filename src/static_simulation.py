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
network_name, max_vSDN_size = networks[0]

hp_settings = {
    'heu': ('heuristics', 'hypervisor count'),
    'ilpk': ('ilp', 'hypervisor count'),
    'ilpa': ('ilp', 'acceptance ratio'),
}
static_type = 'ilpa'
hp_type, hp_objective = hp_settings[static_type]

vSDN_count_ilp = 100

possible_settings = {
    'network_name': [network_name],
    'latency_factor': [0.4],
    'shortest_k': [16],
    'static_type': [static_type],
    'hp_type': [hp_type],
    'hp_objective': [hp_objective],
    'sim_repeat': [10],
    'repeat': [100],
    'max_request_size': [max(2, int(max_vSDN_size / 2))],
    'vSDN_count_ilp': [vSDN_count_ilp],
    'vSDN_size_ilp': [max(2, int(max_vSDN_size / 2))],
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

simulation_logs = []
for setting in tqdm.tqdm(setting_generator, total=len(setting_generator)):
    ns = NetworkSimulation(**setting)
    ns.init_simulation(**setting)
    ns.run_multiple_static_simulation(
        possible_request_settings=possible_request_settings, **setting)
    simulation_logs.extend(ns.get_logs())

with open(
        f"../results/{network_name}/{datetime.date.today()}-{network_name}-{static_type}-ph-{0}.json",
        'w') as file:
    json.dump(simulation_logs,
              file,
              indent=4,
              sort_keys=True,
              separators=(', ', ': '),
              ensure_ascii=False,
              cls=NumpyEncoder)