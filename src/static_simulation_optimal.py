# Standard library imports.
import datetime
import itertools
import json
import os
import logging

# Related third party imports.
import numpy as np
import tqdm

# Local application/library specific imports.
from src.models.network_simulation import NetworkSimulation
from src import logger

networks = [('25_italy', 25), ('26_usa', 26), ('37_cost', 37),
            ('50_germany', 50)]
network_name, max_vSDN_size = networks[0]

static_type = 'opt'
hp_type = 'ilp'
hp_objective = 'acceptance ratio'

hp_objective_list = (
    'acceptance_ratio',
    # 'hypervisor_load',
    # 'controller_load_request',
    # 'controller_load_switch',
)

hp_algo_settings = {
    'hp_type': [hp_type],
    'hp_objective': [hp_objective],
    'hp_objectives': [
        hp_objective_list
        # hp_obj for hp_obj in itertools.permutations(hp_objective_list)
        # if hp_obj[0] == 'acceptance_ratio'
    ],
    'candidate_selection': ['acceptance_ratio'],
    'n_extra_hypervisors': [0],
    'hypervisor_capacity': [None],
    'controller_capacity': [None],
    'n_diff_hypervisors': [0],
    'flexibility_weight': [None],
    'repeat': [50],
    'heuristic_randomness': [0.1],
    'path2model': ['../models/'],
    'model_name': ['gnn_model_1'],
}

simulation_group_id = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
simulation_group_folder = f"../results/{network_name}/static/tmp/{simulation_group_id}/"
os.mkdir(simulation_group_folder)

simulation_settings = {
    'simulation_group_id': [simulation_group_id],
    'simulation_group_folder': [simulation_group_folder],
    'network_name': [network_name],
    'latency_factor': [0.5],
    'shortest_k': [16],
    'static_type': [static_type],
    'sim_repeat': [10],
    'max_request_size': [max(2, int(max_vSDN_size * 0.75))],
    'vSDN_count_ilp': [100],
    'vSDN_size_ilp': [max(2, int(max_vSDN_size * 0.75))],
}

possible_settings = {**hp_algo_settings, **simulation_settings}
param_names_1 = list(possible_settings.keys())
setting_generator = [
    dict(zip(param_names_1, x))
    for x in itertools.product(*possible_settings.values())
]

possible_request_settings = {
    'request_size': np.arange(max_vSDN_size, 1, -1),
    'count': [400],
}

logging.info(f"\n'{simulation_group_folder}simulation-group-results.json'\n")

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
