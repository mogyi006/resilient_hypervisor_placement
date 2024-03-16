# Standard library imports.
import os
os.environ["DGLBACKEND"] = "pytorch"
import random
import itertools
import logging
import datetime
import collections

# Related third party imports.
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import tqdm

import dgl
import torch
import torch.nn as nn
import torch.nn.functional as F
import sklearn.metrics


# Local application/library specific imports.
from src.models.network_simulation import NetworkSimulation
import src.logger as logger
import src.models.gnn as gnn
import src.models.hypervisor_placement as hypervisor_placement

logging.basicConfig(
    format="[%(funcName)30s()] %(message)s",
    level=logging.DEBUG,
    force=True,
)


networks = [('25_italy', 25), ('26_usa', 26), ('37_cost', 37),
            ('50_germany', 50)]
network_name, max_vSDN_size = networks[2]

simulation_group_id = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
simulation_group_folder = f"../results/{network_name}/static/tmp/{simulation_group_id}/"
os.mkdir(simulation_group_folder)

hp_possibilities = {
    'heu': ('heuristics', 'hypervisor count'),
    'heu_scs': ('heuristics', 'combined S CS'),
    'mc': ('heuristics', 'main controller'),
    'ilpk': ('ilp', 'hypervisor count'),
    'ilpa': ('ilp', 'acceptance ratio'),
    'ilpaf': ('ilp', 'acceptance and flexibility'),
}
static_type = 'heu_scs'
hp_type, hp_objective = hp_possibilities[static_type]

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
    'candidate_selection': ['acceptance'],
    'n_extra_hypervisors': [0],
    'hypervisor_capacity': [None],
    'controller_capacity': [None],
    'n_diff_hypervisors': [0],
    'flexibility_weight': [None],
    'repeat': [50],
    'heuristic_randomness': [0.1],
}

simulation_settings = {
    'simulation_group_id': [simulation_group_id],
    'simulation_group_folder': [simulation_group_folder],
    'network_name': [network_name],
    'latency_factor': [0.6],
    'shortest_k': [16],
    'static_type': [static_type],
    'sim_repeat': [50],
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
    'count': [100],
}

logging.info(f"\n'{simulation_group_folder}simulation-group-results.json'\n")

simulation_logs = []
dgl_graphs = []
for setting in tqdm.tqdm(setting_generator, total=len(setting_generator)):
    print()
    ns = NetworkSimulation(**setting)
    ns.init_simulation(**setting)
    ns.run_multiple_static_simulation(
        possible_request_settings=possible_request_settings, generate_dgl=True, **setting)
    simulation_logs.extend(ns.get_logs())

    n_graphs = len(ns.dgl_graphs)
    dgl_graphs.extend(ns.dgl_graphs)

dgl_graph = dgl.batch(dgl_graphs)

dgl.save_graphs("../data/processed/dgl_graphs/35_eu_0.6_50_heu.bin", dgl_graph)