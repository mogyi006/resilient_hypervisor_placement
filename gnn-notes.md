This file contains notes on Graph Neural Networks (GNNs).

## Graph Neural Networks (GNNs)
GNNs are a class of neural networks that operate on graphs. They are a generalization of convolutional neural networks (CNNs) and recurrent neural networks (RNNs) to graph-structured data. GNNs are a powerful tool for learning representations of graph-structured data. They have been applied to many tasks in the field of computer vision, natural language processing, and combinatorial optimization.

## Hypervisor Placement with GNNs
We use GNNs to learn a mapping from a graph representation of a network to a placement of hypervisors in the network. The GNN is trained on a dataset of network graphs and their corresponding hypervisor placements. The GNN is then used to predict the placement of hypervisors in a new network graph.

### Graph Representation
The network is represented as a graph, where the nodes are the switches and the edges are the links between the switches. The graph is undirected and unweighted. The graph is represented as an adjacency matrix.


### Resilient Hypervisor Placement
In Resilient Hypervisor Placement (RHP) we aim to place hypervisors in a network such that the network is resilient to failures. Each switch is controlled by 2 hypervisors. If one of the hypervisors fails, the other hypervisor can take over the control of the switch. The hypervisors are placed such that the network is resilient to the failure of any single hypervisor.

The control structures are represented as quartets: (controller, hypervisor1, hypervisor2, switch) or (c,h1,h2,s). The controller controls the switch. The switch is controlled by hypervisor1 and hypervisor2. If hypervisor1 fails, hypervisor2 can take over the control of the switch. If hypervisor2 fails, hypervisor1 can take over the control of the switch. The hypervisors are placed such that the network is resilient to the failure of any single hypervisor.

The goal is to place the hypervisors such that the network is resilient to the failure of any single hypervisor and the number of hypervisors is minimized. Additionally, we want to minimize the latency between the hypervisors and the switches they control.

The problem is similar to the setcover by pairs problem. The setcover by pairs problem is a generalization of the setcover problem. In the setcover problem we are given a set of elements and a set of subsets of the elements. The goal is to find a minimum size subset of the subsets such that the union of the subsets in the subset is equal to the set of elements. In the setcover by pairs problem we are given a set of elements and a set of pairs of elements. The goal is to find a minimum size subset of the pairs such that the union of the pairs in the subset is equal to the set of elements.

We introduce a representation of the control architecture
shown in Figure 1 without the a priori knowledge of the
vSDN request set. We store the possible locations satisfying
Definition 3 from which the feasible hypervisor placements for
every physical switch s ∈ S in the network can be efficiently
queried. Hence, we define quartets (c, h1, h2, s), where c ∈ C,
h1, h2 ∈ H, and s ∈ S, which represent that the maximum
global latency constraint L is met by controller location c ∈ C
with edge-disjoint paths p1 ∈ P(s, h1, c) and p2 ∈ P(s, h2, c).
We define Q as the set of all quartets that have a disjoint
control path-pair satisfying the latency requirement, formally:
Q = {(c, h1, h2, s) | ∃p1 ∈ P(s, h1, c), p2 ∈ P(s, h2, c) :
p1, p2 are edge-disjoint, and d(p1) ≤ L, d(p2) ≤ L}.
One can observe that the quartets in Q corresponding to
s contain all possible controller and hypervisor locations for
that node which satisfy the latency constraint L. Note that,
Q contains (s, s, s, s) for each s ∈ H and possibly other
quartets satisfying Definition 3 for s ∈ S where h1 6 = h2.
However, important to note that in practice P(s, t) contains
only a predefined number of P simple paths for each (s, t)
pair; thus, the concatenation of path in P(s, h) and P(h, c)
to P(s, h,c) will contain a limited number of paths as well.
Therefore, if path number P is not carefully selected and not
large enough, it is possible that Q will not contain all feasible
quartets. Please refer to Section VI-A for further analysis of
this question.
The projections of Q to different dimensions can be ef-
ficiently leveraged in the algorithms proposed for LHPP. For
example, if we select s and fix the hypervisor pair h1, h2 ∈ H,
then we can obtain from Q all possible controller locations
for s for that primary and backup hypervisor pair. Owing
to its importance in our LHPP algorithms, we define set T
from the projection of Q which represent that {h1, h2} ∈ H
is a primary and backup hypervisor pair for s ∈ S which
possibly can provide latency-aware pathwise-disjoint cover for
a (unknown) vSDN request in the future, formally:
T = {(h1, h2, s) | ∃c ∈ C : (c, h1, h2, s) ∈ Q}.
As a result, T contains all hypervisor pairs which can cover
∀s ∈ S in a latency-aware pathwise-disjoint fashion with an
appropriately selected controller location, denoted as T (s) for
a specific switch s.

The placement problem can be optimized by adding a representative set of vSDNs to the problem. The representative set of vSDNs is a set of vSDNs that represent the vSDN requests that are expected to arrive in the future. These vSDNs are random connected subgraphs from the network. Each vSDN has a latency requirement for the maximal controller-switch latency. The optimal placement meets the latency requirements of the representative set of vSDNs and minimizes the number of hypervisors.

#### Node Features for the GNN
Each node has a feature vector. The feature vector contains the following features:
- the number of quartets that contain the node as hypervisor
- the number of quartets that contain the node as controller
- the number of quartets that contain the node as switch
- the number of quartets that contain the node as hypervisor and are a possible control structure for the representative set of vSDNs
- the number of vSDNs in the representative set that contain the node as a switch
- the 25-th percentile of node's distance to all other nodes
- the 50-th percentile of node's distance to all other nodes
- the 75-th percentile of node's distance to all other nodes
- the 100-th percentile of node's distance to all other nodes
- the betweenness centrality of the node
- the closeness centrality of the node
- the degree centrality of the node
- the clustering coefficient of the node

# GNN Hypervisor Placement

## Options
- top k score is chosen for hypervisors
- top k score is chosen for possible hypervisors and another hypervisor placement methods is used to choose the hypervisors
