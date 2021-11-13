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
hp_type = 'ilp'
hp_objective = 'acceptance ratio'
vSDN_count_ilp = 100
request_per_timestep = 5
TTL_range = 5

possible_settings = {
    'network_name': [network_name],
    'latency_factor': np.arange(0.4, 0.65, 0.05),
    'shortest_k': [16],
    'hp_type': [hp_type],
    'hp_objective': [hp_objective],
    'sim_repeat': [10],
    'timesteps': [50],
    'max_request_size': list(range(max_vSDN_size - 4, max_vSDN_size + 1)),
    'request_per_timestep': [4, 6, 8],
    'TTL_range': [4, 6, 8],
    'vSDN_count_ilp': [100],
    'vSDN_size_ilp': [max(2, int(max_vSDN_size / 2))]
}
param_names_1 = list(possible_settings.keys())
setting_generator = [
    dict(zip(param_names_1, x))
    for x in itertools.product(*possible_settings.values())
]

simulation_logs = []
for setting in tqdm.tqdm(setting_generator, total=len(setting_generator)):
    ns = NetworkSimulation(**setting)
    ns.init_simulation(**setting)
    ns.run_multiple_dynamic_simulations(**setting)
    simulation_logs.extend(ns.get_logs())

with open(
        f"../results/{network_name}/dynamic/{datetime.date.today()}-{network_name}-{hp_type[:3]}-acc.json",
        'w') as file:
    json.dump(simulation_logs,
              file,
              indent=4,
              sort_keys=True,
              separators=(', ', ': '),
              ensure_ascii=False,
              cls=NumpyEncoder)