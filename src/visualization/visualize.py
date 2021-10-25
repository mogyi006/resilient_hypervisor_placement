# Standard library imports.

# Related third party imports.
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

# Local application/library specific imports.


def standard_layout(graph):
    return {node: np.array([graph.nodes[node]['Longitude'], graph.nodes[node]['Latitude']]) for node in graph}


def draw_network(graph, **kwargs):
    fig, ax = plt.subplots(figsize=(16,9))
    nx.draw_networkx(graph, pos=standard_layout(graph), node_color='skyblue', ax=ax, **kwargs)
