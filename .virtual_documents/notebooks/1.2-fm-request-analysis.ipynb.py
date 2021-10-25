get_ipython().run_line_magic("load_ext", " autoreload")
get_ipython().run_line_magic("autoreload", " 2")


# Standard library imports.

# Related third party imports.
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from sklearn.preprocessing import normalize

# Local application/library specific imports.
from src.visualization.visualize import standard_layout, draw_network



all_counts = np.zeros(shape=(25,))
for i in range(2,26):
    R = np.fromfile(f'../data/processed/requests/25_italy/25_italy.{i}.subgraphs', dtype=int, sep=' ')
    nodes, counts = np.unique(R, return_counts=True)
    density = counts/sum(counts)
    all_counts += counts
all_density = all_counts / sum(all_counts)


for i,d in zip(range(25),all_density):
    print(f'{i},{d:.3f}')


fig, ax = plt.subplots(figsize=(12,6))

ax.bar(nodes, all_density);
ax.grid(axis='y')


R10 = np.fromfile('../data/processed/requests/25_italy/25_italy.10.subgraphs', dtype=int, sep=' ')
nodes10, counts10 = np.unique(R10, return_counts=True)
density10 = counts10/sum(counts10)


R4 = np.fromfile('../data/processed/requests/25_italy/25_italy.4.subgraphs', dtype=int, sep=' ')
nodes4, counts4 = np.unique(R4, return_counts=True)
density4 = counts4/sum(counts4)


fig, ax = plt.subplots(1,2,figsize=(16,5))

ax[0].bar(nodes4, counts4);
ax[0].grid(axis='y')

ax[1].bar(nodes10, counts10);
ax[1].grid(axis='y')


# Compare node usage distributions
network = '26_usa'

R = np.fromfile(f'../data/processed/requests/{network}/{network}.4.subgraphs', dtype=int, sep=' ')
nodes, counts4 = np.unique(R, return_counts=True)
density4 = counts4/len(R)
R = np.fromfile(f'../data/processed/requests/{network}/{network}.10.subgraphs', dtype=int, sep=' ')
_, counts10 = np.unique(R, return_counts=True)
density10 = counts10/len(R)


x = np.arange(len(nodes))  # the label locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots(figsize=(12,6))
rects1 = ax.bar(x - width/2, density4, width, label='Counts (4)')
rects2 = ax.bar(x + width/2, density10, width, label='Counts (10)')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Counts')
ax.set_title('Counts in subgraphs')
ax.set_xticks(x)
ax.set_xticklabels(nodes)
ax.legend()

# ax.bar_label(rects1, padding=3)
# ax.bar_label(rects2, padding=3)

fig.tight_layout()

plt.show()


# Degree centrality
network = '26_usa'
g = nx.read_gml(path=f'../data/processed/networks/{network}.gml', label='id')
dc = nx.degree_centrality(g)

fig, ax = plt.subplots(figsize=(8,4))
ax.bar(dc.keys(), dc.values());


draw_network(g, **{'node_size':density10*10000})



