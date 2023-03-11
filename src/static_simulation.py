# Standard library imports.
import os
import datetime
import itertools

# Related third party imports.
import numpy as np
import tqdm

# Local application/library specific imports.
from src.models.network_simulation import NetworkSimulation
import src.logger as logger

networks = [('25_italy', 25), ('26_usa', 26), ('37_cost', 28),
            ('50_germany', 19)]
network_name, max_vSDN_size = networks[0]

simulation_group_id = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
simulation_group_folder = f"../results/{network_name}/static/tmp/{simulation_group_id}/"
os.mkdir(simulation_group_folder)

hp_settings = {
    'heu': ('heuristics', 'hypervisor count'),
    'heu_scs': ('heuristics', 'combined S CS'),
    'mc': ('heuristics', 'main controller'),
    'ilpk': ('ilp', 'hypervisor count'),
    'ilpa': ('ilp', 'acceptance ratio'),
    'ilpaf': ('ilp', 'acceptance and flexibility'),
}
static_type = 'ilpa'
hp_type, hp_objective = hp_settings[static_type]

possible_settings = {
    'simulation_group_id': [simulation_group_id],
    'simulation_group_folder': [simulation_group_folder],
    'network_name': [network_name],
    'latency_factor': [0.4, 0.5, 0.6],
    'shortest_k': [16],
    'static_type': [static_type],
    'hp_type': [hp_type],
    'hp_objective': [hp_objective],
    'sim_repeat': [10],
    'repeat': [10],
    'max_request_size': [max(2, int(max_vSDN_size / 2))],
    'vSDN_count_ilp': [500],
    'vSDN_size_ilp': [max(2, int(max_vSDN_size / 2))],
    'n_extra_hypervisors': [0],
    'hypervisor_capacity': [None],
    'controller_capacity': [None],
    'n_diff_hypervisors': [0],
    'flexibility_weight': [0],
}
param_names_1 = list(possible_settings.keys())
setting_generator = [
    dict(zip(param_names_1, x))
    for x in itertools.product(*possible_settings.values())
]

possible_request_settings = {
    'request_size': range(2, max_vSDN_size),
    'count': [1000]
}

print(f"\n'{simulation_group_folder}simulation-group-results.json'\n")

simulation_logs = []
for setting in tqdm.tqdm(setting_generator, total=len(setting_generator)):
    print()
    ns = NetworkSimulation(**setting)
    ns.init_simulation(**setting)
    ns.run_multiple_static_simulation(
        possible_request_settings=possible_request_settings, **setting)
    simulation_logs.extend(ns.get_logs())

logger.save2json(simulation_group_folder + "simulation-group-results.json",
                 simulation_logs)
