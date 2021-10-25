# Standard library imports.
from itertools import combinations, chain
from collections import Counter

# Related third party imports.
from copy import deepcopy
from random import choice

# Local application/library specific imports.
import src.data.graph_utilities as gu
import src.models.ilp as ilp
from src.logger import measure


# Get facility with maximal covering possibility
# Choosing random at a tie
def get_facility_for_maxcover(C, C_covered, F, F_used, Tc):
    currently_covering = len(C_covered)
    F_notused = list(set(F) - set(F_used))

    covering = [
        len(gu.covered_customers(Tc,
                                 list(F_used) + [f], C)) for f in F_notused
    ]
    max_covering = max(covering)
    max_indexes = [
        idx for idx, value in enumerate(covering) if value == max_covering
    ]
    # print("Before: ", currently_covering, "Possible: ", sorted(covering, reverse=True)[:5])
    if max_covering > currently_covering:
        return set([F_notused[choice(max_indexes)]])
    else:
        return None


# Get facility-pair with maximal covering possibility
# Choosing random at a tie
def get_facility_pair_for_maxcover(C, C_covered, F, F_used, Tc):
    currently_covering = len(C_covered)
    F_notused = list(combinations(list(set(F) - set(F_used)), 2))

    covering = [
        len(gu.covered_customers(Tc,
                                 list(F_used) + [f, f_], C))
        for f, f_ in F_notused
    ]
    max_covering = max(covering)
    max_indexes = [
        idx for idx, value in enumerate(covering) if value == max_covering
    ]
    # print("Before: ", currently_covering, "Possible: ", sorted(covering, reverse=True)[:5])
    if max_covering > currently_covering:
        return set(F_notused[choice(max_indexes)])
    else:
        return None


# Removing unnecessary facilities
def minimize_cover(C, C_covered, F_used, Tc):
    F_min = deepcopy(F_used)
    for f in F_used:
        if len(gu.covered_customers(Tc, F_min - set([f]),
                                    C)) == len(C_covered):
            F_min.discard(f)
    return F_min


# Greedy Path-Disjoint Cover
# Minimizes the number of facilities
def greedy(network_operator=None,
           C=None,
           F=None,
           Tc=None,
           Tf=None,
           start_with_pair: bool = True,
           **kwargs):
    if network_operator is not None:
        C = network_operator.nodes
        F = network_operator.possible_hypervisors
        Tc = network_operator.triplets_by_switches
        Tf = network_operator.triplets_by_hypervisors

    F_ = set()
    C_ = set()

    if start_with_pair:
        F_.update(get_facility_pair_for_maxcover(C, C_, F, F_, Tc))

    while C != C_:
        F_.update(get_facility_for_maxcover(C, C_, F, F_, Tc))
        # print("Step 1:  ", F_)
        C_ = gu.covered_customers(Tc, F_, C)
        F_ = minimize_cover(C, C_, F_, Tc)
        # print("Step 2:  ", F_)
        # print("Covered: ", len(C_))
    return F_


def hp_multiple_greedy(repeat: int = 100, **kwargs):
    solutions = [greedy(**kwargs) for _ in range(repeat)]
    # controllable_switches = [
    #     gu.check_contoller_ability(solution, **kwargs) for solution in solutions
    # ]

    # if optimize == 'hypervisor count':
    return {'active hypervisors': min(solutions, key=len)}
    # elif optimize == 'max controlled':
    #     most_options = [len(list(chain.from_iterable(switch_dict.values()))) for switch_dict in controllable_switches]
    #     return solutions[most_options.index(max(most_options))]
    # else:
    #     return None


def hp_main_controller(network_operator=None,
                       C=None,
                       S=None,
                       Qc=None,
                       Qs=None,
                       **kwargs):
    if network_operator is not None:
        C = network_operator.possible_controllers
        S = network_operator.nodes
        Qc = network_operator.quartets_by_controllers
        Qs = network_operator.quartets_by_switches

    result = {}
    for c in C:
        S_controllable = set()
        H_usable = set()
        Ts = {}
        Th = {}
        for c, h, h_, s in Qc[c]:
            S_controllable.add(s)
            H_usable.update({h, h_})
            Ts.setdefault(s, []).append((s, h, h_))
            Th.setdefault(h, []).append((s, h, h_))
            Th.setdefault(h_, []).append((s, h, h_))

        S_notcontrollable = set(S) - S_controllable
        switch_not_controllable = False
        for s in S_notcontrollable:
            if not Qs[s]:
                switch_not_controllable = True
                break
            for _, h, h_, s in Qs[s]:
                H_usable.update({h, h_})
                Ts.setdefault(s, []).append((s, h, h_))
                Th.setdefault(h, []).append((s, h, h_))
                Th.setdefault(h_, []).append((s, h, h_))

        if len(result.get(
                'S_controllable',
            [])) >= len(S_controllable) or switch_not_controllable:
            continue
        else:
            result['main controller'] = c
            result['S_controllable'] = S_controllable
            result['Tc'] = Ts
            result['active hypervisors'] = greedy(C=S,
                                                  F=H_usable,
                                                  Tc=Ts,
                                                  Tf=Th)
    return result


def hp_overall_coverage(network_operator=None,
                        C=None,
                        S=None,
                        Qs=None,
                        **kwargs):
    if network_operator is not None:
        C = network_operator.possible_controllers
        S = network_operator.nodes
        Qs = network_operator.quartets_by_switches

    dict_hypervisor_pair_counts = {}

    for s in S:
        dict_ch = {}
        for c, h, h_, _ in Qs[s]:
            dict_ch.setdefault(c, []).append((h, h_))
        hypervisor_pair_counts = Counter()
        for c in C:
            hypervisor_pair_counts += Counter(dict_ch.get(c, []))
        dict_hypervisor_pair_counts[s] = hypervisor_pair_counts

    # max_count = max([max(counter.values()) for _,counter in dict_hypervisor_pair_counts.items()])
    # best_1st_hypervisors = [s for s,counter in dict_hypervisor_pair_counts.items() if counter.most_common(1)[0][1] == max_count]
    best_1st_hypervisor_pair = sum(dict_hypervisor_pair_counts.values(),
                                   start=Counter()).most_common(1)[0][0]

    H_ = set(best_1st_hypervisor_pair)
    C_ = set()

    while set(S) != set(C_):
        next_hypervisors = Counter()
        for s, counter_ in dict_hypervisor_pair_counts.items():
            if s in C_:
                continue

            hypervisors_for_switch = Counter()
            for (h, h_), count in counter_.most_common():
                if (h in H_ and h_ in H_):
                    C_.add(s)
                    break
                elif count < 0.8 * max(hypervisors_for_switch.values(),
                                       default=0):
                    break
                elif h != h_ and h not in H_ and h_ not in H_:
                    continue
                elif h == h_ and h not in H_:
                    if h in hypervisors_for_switch:
                        continue
                    else:
                        hypervisors_for_switch += Counter({h: count})
                elif h in H_ and h_ not in H_:
                    if h_ in hypervisors_for_switch:
                        continue
                    else:
                        hypervisors_for_switch += Counter({h_: count})
                elif h not in H_ and h_ in H_:
                    if h in hypervisors_for_switch:
                        continue
                    else:
                        hypervisors_for_switch += Counter({h: count})
                else:
                    continue
            next_hypervisors += hypervisors_for_switch

        if next_hypervisors:
            H_.add(next_hypervisors.most_common(1)[0][0])
        else:
            break

    hypervisor_assignment = {}
    hypervisor2switch_control_paths = {}
    for s, counter in dict_hypervisor_pair_counts.items():
        if s in H_:
            hypervisor_assignment[s] = (s, s)
            hypervisor2switch_control_paths[(s, s, s)] = ({
                'length': 0,
                'path': set()
            }, {
                'length': 0,
                'path': set()
            })
            continue

        for (h, h_), count in counter.most_common():
            if (h in H_ and h_ in H_):
                hypervisor_assignment[s] = (h, h_)
                hypervisor2switch_control_paths[(h, h_, s)] = ({
                    'length': 0,
                    'path': set()
                }, {
                    'length': 0,
                    'path': set()
                })
                break

        if s not in hypervisor_assignment.keys():
            print("Not assigned switch:", s)
            return None

    result = {
        'active hypervisors': set().union(*hypervisor_assignment.values()),
        'hypervisor assignment': hypervisor_assignment,
        'hypervisor2switch control paths': hypervisor2switch_control_paths
    }
    return result


@measure
def hypervison_placement_solutions(type: str = 'heuristics',
                                   objective: str = 'hypervisor count',
                                   **kwargs):
    if type == 'heuristics':
        if objective == 'hypervisor count':
            return hp_multiple_greedy(**kwargs)
        elif objective == 'main controller':
            return hp_main_controller(**kwargs)
        elif objective == 'overall coverage':
            return hp_overall_coverage(**kwargs)
        else:
            return None
    elif type == 'ilp':
        if objective == 'hypervisor count':
            return ilp.lcrhpp_minh(**kwargs)
        if objective == 'acceptance ratio':
            return ilp.lcrhpp_maxa(**kwargs)
    else:
        return None