get_ipython().run_line_magic("load_ext", " autoreload")
get_ipython().run_line_magic("autoreload", " 2")


# Standard library imports.

# Related third party imports.
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

# Local application/library specific imports.
from src.models.network_operator import NetworkOperator
from src.models.network_simulation import NetworkSimulation
import src.data.graph_utilities as gu


g = nx.read_gml(path='../data/processed/networks/26_usa.gml', label='id')
latency_matrix = gu.create_latency_matrix(g)
max_latency = np.amax(latency_matrix)
print("Max distance: ", np.amax(latency_matrix))
print("Min Max distance:", np.amin(np.amax(latency_matrix, axis=1)))


factor = 0.1
ml = max_latency * factor
ns = NetworkSimulation('26_usa', **{'max_length':ml, 'shortest_k':16})
ns.initial_hypervisor_placement(**{'repeat':50, 'optimize':'overall coverage', 'max_length':ml})


for factor in np.linspace(0.1, 0.8, 8):
    ml = max_latency * factor
    ns = NetworkSimulation('26_usa', **{'max_length':ml, 'shortest_k':16})
    ns.initial_hypervisor_placement(**{'repeat':50, 'optimize':'overall coverage', 'max_length':ml})
    for rs in range(2,11):
        ns.discard_old_vSDNs(all=True)
        ns.generate_new_vSDN_requests(2000, rs, 10)
        ns.setup_new_vSDN_requests(rs, ml, factor)


# fig, ax = plt.subplots(9, 1, figsize=(12, 9*9))
controller_usage = [np.zeros((len(g.nodes()),), dtype=int), np.zeros((len(g.nodes()),), dtype=int)]

for j,factor in enumerate([0.5, 0.3]):
    ml = max_latency * factor
    ns = NetworkSimulation('25_italy', **{'max_length':ml, 'shortest_k':16})
    ns.initital_hypervisor_placement(**{'repeat':50, 'select':'hypervisor count'})
    for idx, rs in enumerate(range(2,11)):
        ns.discard_old_vSDNs(all=True)
        ns.generate_new_vSDN_requests(1000, rs, 10)
        ns.setup_new_vSDN_requests(rs, ml, factor)
        ac = ns.network_operator.get_active_controllers()
        nodes, counts = np.unique(np.asarray(ac), return_counts=True)
        for i,v in enumerate(nodes):
            controller_usage[j][v] += counts[i]
        # ax[idx].bar(nodes, counts)


x = np.arange(len(g.nodes()))  # the label locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots(figsize=(12,6))
rects1 = ax.bar(x - width/2, controller_usage[0]/np.sum(controller_usage[0]), width, label='Usage (0.5)')
rects2 = ax.bar(x + width/2, controller_usage[1]/np.sum(controller_usage[1]), width, label='Usage (0.3)')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Used')
ax.set_title('Conroller usage')
ax.set_xticks(x)
ax.set_xticklabels(g.nodes())
ax.legend()

# ax.bar_label(rects1, padding=3)
# ax.bar_label(rects2, padding=3)

fig.tight_layout()

plt.show()


plt.hist(controller_usage[0]/np.sum(controller_usage[0]))
plt.hist(controller_usage[1]/np.sum(controller_usage[1]))


for c, quartet_list in no.quartets_by_controllers.items():
    print(c, len(np.unique([s for _,_,_,s in quartet_list])))


get_ipython().run_line_magic("time", " sns.countplot(x=[len(greedy(network_operator=no, start_with_pair=True)) for i in tqdm(range(13))])")


greedy(network_operator=no, start_with_pair=True)


no.hypervisor_placement(**{'max_length':4000, 'shortest_k':10})



no.hypervisor_assignment


primary, backup = no.get_hypervisor_switch_latencies()


no.quartets_by_controllers[0][:10]


for c in no.possible_controllers:
    print(c, set(s for _,h,h_,s in no.quartets_by_controllers[c] if (h in no.active_hypervisors) and (h_ in no.active_hypervisors) ))


for s in no.nodes:
    print(s, set(c for c,_,_,_ in no.quartets_by_switches[s]))
