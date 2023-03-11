# Standard library imports.
import os
import datetime
import itertools
import json

# Related third party imports.
import numpy as np
import tqdm

# Local application/library specific imports.
from src.models.network_simulation import NetworkSimulation
import src.logger as logger

networks = [('25_italy', 25), ('26_usa', 26), ('37_cost', 37),
            ('50_germany', 50)]
network_name, max_vSDN_size = networks[2]

simulation_group_id = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
simulation_group_folder = f"../results/{network_name}/dynamic/{simulation_group_id}/"
os.mkdir(simulation_group_folder)

hp_settings = {
    'basic': ('ilp', 'acceptance ratio'),
    'conservative': ('ilp', 'acceptance ratio'),
    'liberal': ('ilp', 'acceptance ratio'),
}
dynamic_type = 'conservative'
hp_type, hp_objective = hp_settings[dynamic_type]

vSDN_count_ilp = 100
request_per_timestep = 10
TTL_range = 6

possible_settings = {
    'simulation_group_id': [simulation_group_id],
    'simulation_group_folder': [simulation_group_folder],
    'network_name': [network_name],
    'latency_factor': [0.7],
    'shortest_k': [16],
    'dynamic_type': [dynamic_type],
    'hp_type': [hp_type],
    'hp_objective': [hp_objective],
    'ilp_objective_function': ['maximize_total_revenue'],
    'cp_method': ['max_total_hpair', 'random_controller'],
    'sim_repeat': [5],
    'timesteps': [100],
    'max_request_size': [max_vSDN_size],
    'request_per_timestep': [request_per_timestep],
    'TTL_range': [TTL_range],
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

logger.save2json(simulation_group_folder + "simulation-group-results.json",
                 simulation_logs)