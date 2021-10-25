# Standard library imports.

# Related third party imports.
import numpy as np
import networkx as nx

# Local application/library specific imports.
from src.models.network_operator import NetworkOperator
from src.models.network_simulation import NetworkSimulation
import src.data.graph_utilities as gu


g = nx.read_gml(path='../data/processed/networks/25_italy.gml', label='id')
latency_matrix = gu.create_latency_matrix(g)
max_latency = np.amax(latency_matrix)
print("Max distance: ", np.amax(latency_matrix))
print("Min Max distance:", np.amin(np.amax(latency_matrix, axis=1)))

for factor in np.linspace(0.1, 0.8, 8):
    ml = max_latency * factor
    ns = NetworkSimulation('25_italy', **{'max_length':ml, 'shortest_k':16})
    ns.initial_hypervisor_placement(**{'repeat':50, 'optimize':'overall coverage', 'max_length':ml})
    for rs in range(2,11):
        ns.discard_old_vSDNs(all=True)
        ns.generate_new_vSDN_requests(2000, rs, 10)
        ns.setup_new_vSDN_requests(rs, ml, factor)
