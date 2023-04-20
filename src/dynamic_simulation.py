# Standard library imports.
import os
import datetime
import itertools
import logging

# Related third party imports.
import numpy as np
import tqdm

# Local application/library specific imports.
from src.models.network_simulation import NetworkSimulation
import src.logger as logger

logging.basicConfig(
    format="[%(funcName)30s()] %(message)s",
    level=logging.INFO,
    force=True,
)

networks = [('25_italy', 25), ('26_usa', 26), ('37_cost', 37),
            ('50_germany', 50)]
network_name, max_vSDN_size = networks[0]

simulation_group_id = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
simulation_group_folder = f"../results/{network_name}/dynamic/tmp/{simulation_group_id}/"
os.mkdir(simulation_group_folder)

hp_settings = {
    'basic': ('ilp', 'acceptance ratio'),
    'conservative': ('ilp', 'acceptance ratio'),
    'liberal': ('ilp', 'acceptance ratio'),
}
dynamic_type = 'basic'
hp_type, hp_objective = hp_settings[dynamic_type]

hp_objective_list = (
    'acceptance_ratio',
    # 'hypervisor_load',
    # 'controller_load_request',
    # 'controller_load_switch',
    # 'switch_load',
    # 'switch_load_time',
    # 'QoS',
    # 'revenue',
)

hp_algo_settings = {
    'hp_type': [hp_type],
    'hp_objective': [hp_objective],
    'hp_objectives': [
        # hp_obj
        hp_obj for hp_obj in itertools.permutations(hp_objective_list)
        # if hp_obj[0] == 'acceptance_ratio'
    ],
    'n_extra_hypervisors': [0],
    'hypervisor_capacity': [None],
    'controller_capacity': [None],
    'n_diff_hypervisors': [0],
    'flexibility_weight': [None],
    'repeat': [1],
    'heuristic_randomness': [0],
}

simulation_settings = {
    'simulation_group_id': [simulation_group_id],
    'simulation_group_folder': [simulation_group_folder],
    'dynamic_type': [dynamic_type],
    'sim_repeat': [2],
    'timesteps': [10],
    'request_per_timestep': [10],
    'TTL_range': [6],
    'network_name': [network_name],
    'latency_factor': [0.5],
    'shortest_k': [16],
    'max_request_size': [max(2, int(max_vSDN_size * 0.75))],
    'vSDN_count_ilp': [50],
    'vSDN_size_ilp': [max(2, int(max_vSDN_size * 0.75))],
}

possible_settings = {**hp_algo_settings, **simulation_settings}
param_names_1 = list(possible_settings.keys())
setting_generator = [
    dict(zip(param_names_1, x))
    for x in itertools.product(*possible_settings.values())
]

logging.info(f"\n'{simulation_group_folder}simulation-group-results.json'\n")

simulation_logs = []
for setting in tqdm.tqdm(setting_generator, total=len(setting_generator)):
    ns = NetworkSimulation(**setting)
    ns.init_simulation(**setting)
    ns.run_multiple_dynamic_simulations(**setting)
    simulation_logs.extend(ns.get_logs())

logger.save2json(simulation_group_folder + "simulation-group-results.json",
                 simulation_logs)