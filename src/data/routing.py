# Standard library imports.
from itertools import product, islice, combinations

# Related third party imports.
import numpy as np
import networkx as nx
from copy import deepcopy

# Local application/library specific imports.
"""Path-disjoint Set Cover"""

# path: set of tuples
# paths: list of path


# Check if 2 paths are link disjoint
def is_disjoint(p, q):
    if not p or not q:
        return False
    elif isinstance(p, set) and isinstance(q, set):
        return p.isdisjoint(q)
    else:
        print(f"p: {isinstance(p, set)}\nq:{isinstance(q, set)}")
        p_ = set(p)
        q_ = set(q)
        return p_.isdisjoint(q_)


# Node list -> Edge list
def path_as_edges(path):
    if all(isinstance(x, int) for x in path):
        return set(zip(path[0::], path[1::]))
    elif all(isinstance(x, tuple) for x in path):
        return path
    else:
        raise TypeError


# Latency of an Edge list (list of tuples)
def latency_of_path(G, p):
    length = 0
    for u, v in p:
        length += G[u][v]['length']
    return length


# Get the k shortest paths between u and v according to the weight parameter
def k_shortest_paths(G, u, v, k, weight="length"):
    return list(islice(nx.shortest_simple_paths(G, u, v, weight=weight), k))


# Get the k shortest paths between u and v
# with lower length than max_length
def get_paths(G,
              u,
              v,
              max_length: float = np.inf,
              shortest_k: int = 16,
              with_length: bool = False,
              **kwargs):
    shortest_k_path = k_shortest_paths(G, u, v, shortest_k)
    paths = []
    for path in shortest_k_path:
        p = path_as_edges(path)
        l = latency_of_path(G, p)
        if l < max_length:
            if with_length:
                paths.append({'length': l, 'path': p})
            else:
                paths.append(p)
    return paths


# All simple paths between nodes
def get_all_paths(G, **kwargs):
    all_paths = {}
    for s, t in combinations(G.nodes, 2):
        paths = get_paths(G=G, u=s, v=t, with_length=True, **kwargs)
        all_paths[(s, t)] = paths
        all_paths[(t, s)] = paths
    return all_paths


# Get all shortest paths between u and v
def get_shortest_paths(G, u, v):
    return list(
        set(zip(path[0::], path[1::]))
        for path in nx.all_shortest_paths(G, u, v))


# c = h, h_ != s
def triangle_control_path(all_paths, c, h, h_, s, max_length):
    # no Pc
    Ps = [p for p in all_paths[(h, s)] if p['length'] < max_length]
    Qc = [
        p for p in all_paths[(c, h_)]
        if p['length'] + all_paths[(h_, s)][0]['length'] < max_length
    ]
    Qs = [
        p for p in all_paths[(h_, s)]
        if p['length'] + all_paths[(c, h_)][0]['length'] < max_length
    ]

    best_control_path = {}
    for qc, ps, qs in product(Qc, Ps, Qs):
        if (is_disjoint(ps['path'], qs['path'])
                and is_disjoint(qc['path'], ps['path'])
                and ps['length'] < max_length
                and qc['length'] + qs['length'] < max_length):
            if not best_control_path:
                best_control_path['pc'] = None
                best_control_path['ps'] = ps
                best_control_path['qc'] = qc
                best_control_path['qs'] = qs
            elif ((best_control_path['ps']['length'] +
                   best_control_path['qc']['length'] +
                   best_control_path['qs']['length']) <
                  (ps['length'] + qc['length'] + qs['length'])):
                best_control_path['pc'] = None
                best_control_path['ps'] = ps
                best_control_path['qc'] = qc
                best_control_path['qs'] = qs
            else:
                continue
    return best_control_path


def diamond_control_path(all_paths, c, h, h_, s, max_length):
    Pc = [
        p for p in all_paths[(c, h)]
        if p['length'] + all_paths[(h, s)][0]['length'] < max_length
    ]
    Ps = [
        p for p in all_paths[(h, s)]
        if p['length'] + all_paths[(c, h)][0]['length'] < max_length
    ]
    Qc = [
        p for p in all_paths[(c, h_)]
        if p['length'] + all_paths[(h_, s)][0]['length'] < max_length
    ]
    Qs = [
        p for p in all_paths[(h_, s)]
        if p['length'] + all_paths[(c, h_)][0]['length'] < max_length
    ]

    best_control_path = {}
    for pc, qc, ps, qs in product(Pc, Qc, Ps, Qs):
        if (pc['length'] + ps['length'] < max_length
                and qc['length'] + qs['length'] < max_length
                and is_disjoint(pc['path'], qc['path'])
                and is_disjoint(ps['path'], qs['path'])
                and is_disjoint(pc['path'], qs['path'])
                and is_disjoint(qc['path'], ps['path'])):
            if not best_control_path:
                best_control_path['pc'] = pc
                best_control_path['ps'] = ps
                best_control_path['qc'] = qc
                best_control_path['qs'] = qs
            elif ((best_control_path['pc']['length'] +
                   best_control_path['ps']['length'] +
                   best_control_path['qc']['length'] +
                   best_control_path['qs']['length']) <
                  (pc['length'] + ps['length'] + qc['length'] + qs['length'])):
                best_control_path['pc'] = pc
                best_control_path['ps'] = ps
                best_control_path['qc'] = qc
                best_control_path['qs'] = qs
            else:
                continue
    return best_control_path


# Best Controller - Hypervisor - Switch control path
def full_control_path(all_paths, c, h, h_, s, max_length, **kwargs):
    control_path = {}

    # (c,c,c,c)
    if c == h and h == h_ and h_ == s:
        control_path['pc'] = None
        control_path['ps'] = None
        control_path['qc'] = None
        control_path['qs'] = None

    # (c,s,s,s)
    elif c != s and h == s and h_ == s:
        control_path['pc'] = all_paths[(c, s)][0]
        control_path['ps'] = None
        control_path['qc'] = None
        control_path['qs'] = None

    # (c,c,h,s)
    elif c == h:
        control_path = triangle_control_path(all_paths, c, h, h_, s,
                                             max_length)
    elif c == h_:
        control_path = triangle_control_path(all_paths, c, h_, h, s,
                                             max_length)

    # (c,h,h_,s)
    else:
        control_path = diamond_control_path(all_paths, c, h_, h, s, max_length)

    return control_path


def get_best_disjoint_path_pair(P, Q):
    p_, q_ = {'path': None, 'length': np.inf}, {'path': None, 'length': np.inf}
    for p, q in product(P, Q):
        if is_disjoint(p['path'], q['path']) and is_better_path_pair(
                p_, q_, p, q):
            p_, q_ = deepcopy(p), deepcopy(q)

    if not p_['path'] or not q_['path']:
        # print("No disjoint path-pair found!")
        # print("P: ", P)
        # print("Q: ", Q)
        return None, None
    else:
        return p_, q_


def is_better_path_pair(p, q, p_, q_):
    """True if (p_, q_) is better then (p,q)

    Args:
        p, q: path-pair
        p_, q_: path-pair

    Returns:
        bool
    """
    return p['length'] + q['length'] > p_['length'] + q_['length']
