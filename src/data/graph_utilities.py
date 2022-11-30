# Standard library imports.
import itertools

# Related third party imports.
import numpy as np
import networkx as nx
import copy
import random
from tqdm import tqdm

# Local application/library specific imports.
import src.data.routing as routing


# Latency matrix of shortest paths
def create_latency_matrix(graph, weight: str = 'length'):
    n = len(graph.nodes)
    latency_matrix = np.zeros((n, n), dtype=int)
    all_shortest_paths = [
        x[1] for x in nx.all_pairs_dijkstra_path_length(graph, weight=weight)
    ]
    for i, j in itertools.product(range(n), range(n)):
        latency_matrix[i][j] = all_shortest_paths[i][j]
    return latency_matrix


# Controller-Hypervisor-Switch latency matrix
def create_chs_latency_matrix(latency_matrix):
    n = latency_matrix.shape[0]
    chs_latency_matrix = np.zeros((n, n, n), dtype=int)
    for i, j, k in itertools.product(range(n), range(n), range(n)):
        chs_latency_matrix[i][j][
            k] = latency_matrix[i][j] + latency_matrix[j][k]
    return chs_latency_matrix


# Graph Diameter
def get_graph_diameter(g):
    return np.amax(create_latency_matrix(g))


# Controllability matrix with given latency
def create_controllability_matrix(chs_latency_matrix, latency_contraint):
    return np.asarray(chs_latency_matrix <= latency_contraint, dtype=int)


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


# Check if there are 2 disjoint paths in pathlist P and Q
def is_path_disjoint(P, Q):
    for p, q in itertools.product(P, Q):
        if is_disjoint(p, q):  # and is_low_latency(p) and is_low_latency(q):
            return True
    return False


# Can f and f_ cover c in a path disjoint way?
def is_path_disjoint_cover(G, f, f_, c, max_length, shortest_k: int = 10):
    P = routing.get_paths(G, f, c, max_length, shortest_k=shortest_k)
    Q = routing.get_paths(G, f_, c, max_length, shortest_k=shortest_k)
    return is_path_disjoint(P, Q)


# Path/Disjoint covering triplets
# Only using paths with length below max_length
def construct_triplets(G, C, F, max_length):
    T = set()
    Tf, Tc = {}, {}

    for c in F:
        T.add((c, c, c))
        Tf.setdefault(c, []).append((c, c, c))
        Tc.setdefault(c, []).append((c, c, c))

    for c, (f, f_) in tqdm(itertools.product(C, itertools.combinations(F, 2))):
        if (c != f) and (c != f_) and (f < f_) and is_path_disjoint_cover(
                G, f, f_, c, max_length):
            T.add((c, f, f_))
            Tf.setdefault(f, []).append((c, f, f_))
            Tf.setdefault(f_, []).append((c, f, f_))
            Tc.setdefault(c, []).append((c, f, f_))

    return T, Tf, Tc


# Can f and f_ cover c in a path disjoint way?
def is_path_disjoint_control_cover(G, c, h, h_, s, max_length):
    Pc = routing.get_paths(G, c, h, max_length, with_length=True)
    Qc = routing.get_paths(G, c, h_, max_length, with_length=True)
    Ps = routing.get_paths(G, h, s, max_length, with_length=True)
    Qs = routing.get_paths(G, h_, s, max_length, with_length=True)
    pc, qc = routing.get_best_disjoint_path_pair(Pc, Qc)
    ps, qs = routing.get_best_disjoint_path_pair(Ps, Qs)
    if not pc or not qc or not ps or not qs:
        return False
    return pc['length'] + qc['length'] + ps['length'] + qs[
        'length'] < max_length * 2


def is_quartet_possible(all_paths, c, h, h_, s, max_length):
    # Pc = all_paths[(c,h)]
    # Qc = all_paths[(c,h_)]
    # Ps = all_paths[(h,s)]
    # Qs = all_paths[(h_,s)]

    if (not all_paths[(c, h)] or not all_paths[(h, s)]
            or not all_paths[(c, h_)] or not all_paths[(h_, s)]):
        # print("Not possible", c, h, h_, s)
        return False

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

    for pc, qc, ps, qs in itertools.product(Pc, Qc, Ps, Qs):
        if (pc['length'] + ps['length'] < max_length
                and qc['length'] + qs['length'] < max_length
                and is_disjoint(pc['path'], qc['path'])
                and is_disjoint(ps['path'], qs['path'])
                and is_disjoint(pc['path'], qs['path'])
                and is_disjoint(qc['path'], ps['path'])):
            return True
    return False


# c = h, h_ != s
def is_triangle_quartet_possible(all_paths, c, h, h_, s, max_length):
    # Pc = all_paths[(c,h)] -> no Pc
    Qc = all_paths[(c, h_)]
    Ps = all_paths[(h, s)]
    Qs = all_paths[(h_, s)]
    for qc, ps, qs in itertools.product(Qc, Ps, Qs):
        if (is_disjoint(ps['path'], qs['path'])
                and is_disjoint(qc['path'], ps['path'])
                and ps['length'] < max_length
                and qc['length'] + qs['length'] < max_length):
            return True
    return False


# Path-Disjoint covering quartets
def construct_quartets(C, S, H, all_paths, max_length):
    Q = set()
    Qc, Qs = {}, {}
    Qcs = {}

    for c, s in itertools.product(C, S):
        # (c,c,c,c)
        if c == s and c in H:
            q = (c, c, c, c)
            Q.add(q)
            Qc.setdefault(c, []).append(q)
            Qs.setdefault(s, []).append(q)
            Qcs.setdefault((s, s), set()).add((s, s))

        # (c,s,s,s)
        if (c != s and s in H and all_paths[(c, s)]
                and all_paths[(c, s)][0]['length'] < max_length):
            q = (c, s, s, s)
            Q.add(q)
            Qc.setdefault(c, []).append(q)
            Qs.setdefault(s, []).append(q)
            Qcs.setdefault((c, s), set()).add((s, s))

        # (c,c,h,s) and (c,h,c,s)
        if c != s and c in H:
            for h in set(H) - {c, s}:
                if is_triangle_quartet_possible(all_paths, c, c, h, s,
                                                max_length):
                    for q in [(c, c, h, s), (c, h, c, s)]:
                        Q.add(q)
                        Qc.setdefault(c, []).append(q)
                        Qs.setdefault(s, []).append(q)
                        Qcs.setdefault((c, s), set()).add((min(c,
                                                               h), max(c, h)))

        for h, h_ in itertools.combinations(set(H) - {c, s}, 2):
            if is_quartet_possible(all_paths, c, h, h_, s, max_length):
                q = (c, h, h_, s)
                Q.add(q)
                Qc.setdefault(c, []).append(q)
                Qs.setdefault(s, []).append(q)
                Qcs.setdefault((c, s), set()).add((min(h, h_), max(h, h_)))

    return Q, Qc, Qs, Qcs


def quartets_to_triplets(Q):
    T = set()
    Tf, Tc = {}, {}
    for q in Q:
        # (s, h_1, h_2)
        t = (q[3], q[1], q[2])
        if t not in T:
            T.add(t)
            Tf.setdefault(t[1], []).append(t)
            Tf.setdefault(t[2], []).append(t)
            Tc.setdefault(t[0], []).append(t)
    return T, Tf, Tc


def get_allowed_hypervisor_pairs_by_switch(Ts):
    return {
        s: [(i, j) for _, i, j in Ts[s] if (i <= j)]  # i != s and j != s and 
        for s in Ts
    }


# Path-Disjoint covered customers by F
def covered_customers(Tc, F, C):
    covered = []
    for c in C:
        if c in F:
            covered.append(c)
            continue
        for c, f, f_ in Tc[c]:
            if (f in F) and (f_ in F):
                covered.append(c)
                break
    return covered


def control_path_length(control_path):
    primary, secondary = 0, 0
    if control_path['pc']:
        primary += control_path['pc']['length']
    if control_path['ps']:
        primary += control_path['ps']['length']
    if control_path['qc']:
        secondary += control_path['qc']['length']
    if control_path['qs']:
        secondary += control_path['qs']['length']
    if primary < secondary:
        return primary, secondary
    else:
        return secondary, primary


def check_contoller_ability(H, C, Qc, **kwargs):
    return {
        c: {s
            for _, h, h_, s in Qc[c] if (h in H) and (h_ in H)}
        for c in C
    }


def best_controller_ability(controllable_nodes):
    most_controllable = max(controllable_nodes.values())
    best_controllers = [
        c for c, nodes in controllable_nodes.items()
        if len(nodes) == most_controllable
    ]
    return random.choice(best_controllers)


def triplets_2_hypervisor_pairs(T, H):
    return [(h, h_) for _, h, h_ in T if (h in H) and (h_ in H)]


def is_better_full_control_path(cp1, cp2, objective: str = 'min avg'):
    if objective == 'min avg':
        return sum(control_path_length(cp1)) < sum(control_path_length(cp2))
    elif objective == 'min primary':
        return control_path_length(cp1)[0] < control_path_length(cp2)[0]
    elif objective == 'min backup':
        return control_path_length(cp1)[1] < control_path_length(cp2)[1]
    else:
        return False


# def assign_switches_to_hypervisors(V, Tc, hypervisors, all_paths=None, select=None, **kwargs):
#     hypervisor_assignment = {}
#     hypervisor2switch_control_paths = {}
#     for s in V:
#         # print("\nAssigning switch ", s)
#         possible_hypervisor_pairs = triplets_2_hypervisor_pairs(Tc[s], hypervisors)

#         # print("Number of possible hypervisor pairs: ", len(possible_hypervisor_pairs))
#         if not possible_hypervisor_pairs:
#             print("No path-disjoint cover for switch ", s)
#             raise ValueError

#         best_hypervisor_pair = None
#         best_h2s_control_paths = None

#         if (s,s) in possible_hypervisor_pairs:
#             # print("Covers itself...")
#             hypervisor_assignment[s] = (s,s)
#             hypervisor2switch_control_paths[(s,s,s)] = ({'length':0, 'path':set()}, {'length':0, 'path':set()})
#             continue

#         if select == 'best hypervisor':
#             pass

#         for h, h_ in possible_hypervisor_pairs:
#             # print(f"Checking ({h},{h_})")
#             # P = get_paths(G, h , s, with_length=True, **kwargs)
#             # Q = get_paths(G, h_, s, with_length=True, **kwargs)
#             P = all_paths[(h,s)]
#             Q = all_paths[(h_,s)]
#             p, q = get_best_disjoint_path_pair(P, Q)
#             if not p or not q:
#                 continue
#             if not best_hypervisor_pair and not best_h2s_control_paths:
#                 if p['length'] < q['length']:
#                     best_hypervisor_pair = (h, h_)
#                     best_h2s_control_paths = (p, q)
#                 else:
#                     best_hypervisor_pair = (h_, h)
#                     best_h2s_control_paths = (q, p)
#             elif is_better_path_pair(best_h2s_control_paths[0], best_h2s_control_paths[1], p, q):
#                 if p['length'] < q['length']:
#                     best_hypervisor_pair = (h, h_)
#                     best_h2s_control_paths = (p, q)
#                 else:
#                     best_hypervisor_pair = (h_, h)
#                     best_h2s_control_paths = (q, p)
#             else:
#                 continue

#         if best_hypervisor_pair and best_h2s_control_paths:
#             hypervisor_assignment[s] = best_hypervisor_pair
#             hypervisor2switch_control_paths[best_hypervisor_pair+(s,)] = best_h2s_control_paths
#         else:
#             # print("No path-disjoint cover found")
#             raise ValueError

#     return hypervisor_assignment, hypervisor2switch_control_paths


def assign_switches_to_hypervisors(S,
                                   Tc,
                                   hypervisors,
                                   main_controller=None,
                                   Smc=None,
                                   all_paths=None,
                                   **kwargs):
    hypervisor_assignment = {}
    hypervisor2switch_control_paths = {}

    for s in S:
        # print("\nAssigning switch ", s)
        possible_hypervisor_pairs = triplets_2_hypervisor_pairs(
            Tc[s], hypervisors)

        # print("Number of possible hypervisor pairs: ", len(possible_hypervisor_pairs))
        if not possible_hypervisor_pairs:
            print("No path-disjoint cover for switch ", s)
            raise ValueError

        best_hypervisor_pair = None
        best_h2s_control_paths = None
        best_full_control_path = None

        if (s, s) in possible_hypervisor_pairs:
            # print("Covers itself...")
            hypervisor_assignment[s] = (s, s)
            hypervisor2switch_control_paths[(s, s, s)] = ({
                'length': 0,
                'path': set()
            }, {
                'length': 0,
                'path': set()
            })
            continue

        for h, h_ in possible_hypervisor_pairs:

            if s in Smc:
                control_path = routing.full_control_path(
                    all_paths, main_controller, h, h_, s, **kwargs)
                if not control_path:
                    continue
                if not best_hypervisor_pair:
                    best_hypervisor_pair = (h, h_)
                    best_h2s_control_paths = (control_path['ps'],
                                              control_path['qs'])
                    best_full_control_path = copy.deepcopy(control_path)
                elif is_better_full_control_path(control_path,
                                                 best_full_control_path):
                    best_hypervisor_pair = (h, h_)
                    best_h2s_control_paths = (control_path['ps'],
                                              control_path['qs'])
                    best_full_control_path = copy.deepcopy(control_path)
                else:
                    continue

            else:
                P = all_paths[(h, s)]
                Q = all_paths[(h_, s)]
                p, q = routing.get_best_disjoint_path_pair(P, Q)

                if not p or not q:
                    continue
                if not best_hypervisor_pair and not best_h2s_control_paths:
                    if p['length'] < q['length']:
                        best_hypervisor_pair = (h, h_)
                        best_h2s_control_paths = (p, q)
                    else:
                        best_hypervisor_pair = (h_, h)
                        best_h2s_control_paths = (q, p)
                elif routing.is_better_path_pair(best_h2s_control_paths[0],
                                                 best_h2s_control_paths[1], p,
                                                 q):
                    if p['length'] < q['length']:
                        best_hypervisor_pair = (h, h_)
                        best_h2s_control_paths = (p, q)
                    else:
                        best_hypervisor_pair = (h_, h)
                        best_h2s_control_paths = (q, p)
                else:
                    continue

            if best_hypervisor_pair and best_h2s_control_paths:
                hypervisor_assignment[s] = best_hypervisor_pair
                hypervisor2switch_control_paths[best_hypervisor_pair +
                                                (s, )] = best_h2s_control_paths
            else:
                # print("No path-disjoint cover found")
                raise ValueError

    return hypervisor_assignment, hypervisor2switch_control_paths


def multiple_switch_assignment(hypervisor_placements, V, C, Q, Qs, Qc,
                               all_paths):
    complete_placement = []
    for idx, hypervisors in enumerate(hypervisor_placements):
        complete_placement.append({'hypervisors': hypervisors})
        switch_assignment = {}
        hypervisor2switch_control_paths = {}

        # Best control counts
        controlled_switches, controlled_count = check_contoller_ability(
            hypervisors, C, Qc)
        # Select the one with the highest
        max_controllers = [
            key for key, value in controlled_count.items()
            if value == max(controlled_count.values())
        ]
        optimized_controller = C[random.choice(max_controllers)]

        for s in V:
            # print("\nAssigning switch ", s)
            best_hypervisor_pair = None
            best_h2s_control_paths = None

            if s in hypervisors:
                switch_assignment[s] = (s, s)
                hypervisor2switch_control_paths[(s, s, s)] = ({
                    'length': 0,
                    'path': set()
                }, {
                    'length': 0,
                    'path': set()
                })
                continue

            if s in controlled_switches[optimized_controller]:
                possible_hypervisor_pairs = [
                    (h, h_) for c, h, h_, s in Qs[s]
                    if (h in hypervisors) and (h_ in hypervisors) and (
                        c == optimized_controller)
                ]
            else:
                possible_hypervisor_pairs = [
                    (h, h_) for _, h, h_, s in Qs[s]
                    if (h in hypervisors) and (h_ in hypervisors)
                ]

            # print("Number of possible hypervisor pairs: ", len(possible_hypervisor_pairs))
            if not possible_hypervisor_pairs:
                print("No path-disjoint cover for switch ", s)
                raise ValueError

            for h, h_ in possible_hypervisor_pairs:
                # print(f"Checking ({h},{h_})")
                # P = get_paths(G, h , s, with_length=True, **kwargs)
                # Q = get_paths(G, h_, s, with_length=True, **kwargs)
                P = all_paths[(h, s)]
                Q = all_paths[(h_, s)]
                p, q = routing.get_best_disjoint_path_pair(P, Q)
                if not p or not q:
                    continue
                if not best_hypervisor_pair and not best_h2s_control_paths:
                    if p['length'] < q['length']:
                        best_hypervisor_pair = (h, h_)
                        best_h2s_control_paths = (p, q)
                    else:
                        best_hypervisor_pair = (h_, h)
                        best_h2s_control_paths = (q, p)
                elif routing.is_better_path_pair(best_h2s_control_paths[0],
                                                 best_h2s_control_paths[1], p,
                                                 q):
                    if p['length'] < q['length']:
                        best_hypervisor_pair = (h, h_)
                        best_h2s_control_paths = (p, q)
                    else:
                        best_hypervisor_pair = (h_, h)
                        best_h2s_control_paths = (q, p)
                else:
                    continue

            if best_hypervisor_pair and best_h2s_control_paths:
                switch_assignment[s] = best_hypervisor_pair
                hypervisor2switch_control_paths[best_hypervisor_pair +
                                                (s, )] = best_h2s_control_paths
            else:
                # print("No path-disjoint cover found")
                raise ValueError

        complete_placement[idx]['assignment'] = switch_assignment
        complete_placement[idx][
            'control paths'] = hypervisor2switch_control_paths
    return complete_placement