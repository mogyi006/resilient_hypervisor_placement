# Standard library imports.
import itertools
from collections import Counter
import concurrent.futures
from copy import deepcopy
from random import choice
import logging

# Related third party imports.
import numpy as np

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
    if max_covering > currently_covering:
        return set([F_notused[choice(max_indexes)]])
    else:
        return None


# Get facility-pair with maximal covering possibility
# Choosing random at a tie
def get_facility_pair_for_maxcover(C, C_covered, F, F_used, Tc):
    currently_covering = len(C_covered)
    F_notused = list(itertools.combinations(list(set(F) - set(F_used)), 2))

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
    if network_operator is not None and (C is None or F is None or Tc is None):
        C = network_operator.nodes
        F = network_operator.possible_hypervisors
        Tc = network_operator.triplets_by_switches
        Tf = network_operator.triplets_by_hypervisors
    elif C is None or F is None or Tc is None:
        raise ValueError

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


def greedy_limited(network_operator=None,
                   C=None,
                   F=None,
                   Tc=None,
                   Tf=None,
                   k: int = None,
                   start_with_pair: bool = True,
                   end_with_pair: bool = True,
                   **kwargs):
    if k < 2 or k > len(C):
        raise ValueError

    if network_operator is not None and (C is None or F is None or Tc is None):
        C = network_operator.nodes
        F = network_operator.possible_hypervisors
        Tc = network_operator.triplets_by_switches
        Tf = network_operator.triplets_by_hypervisors

    F_ = set()
    C_ = set()

    if start_with_pair:
        F_.update(get_facility_pair_for_maxcover(C, C_, F, F_, Tc))

    while len(F_) < k and C != C_:
        if end_with_pair and len(F_) == k - 2:
            F_.update(get_facility_pair_for_maxcover(C, C_, F, F_, Tc))
        else:
            F_.update(get_facility_for_maxcover(C, C_, F, F_, Tc))
            C_ = gu.covered_customers(Tc, F_, C)
            F_ = minimize_cover(C, C_, F_, Tc)
    return F_


def hp_multiple_greedy(repeat: int = 100, **kwargs):
    solutions = [greedy_limited(**kwargs) for _ in range(repeat)]
    print(f"No. Greedy Solutions: {len(solutions)}")

    min_h_count = len(min(solutions, key=len))
    min_solutions = list(
        set(
            frozenset(active_hypervisors) for active_hypervisors in solutions
            if len(active_hypervisors) == min_h_count))
    print(f"No. unique minimal Greedy Solutions: {len(min_solutions)}")
    print(min_solutions)

    network_operator = kwargs.get('network_operator', None)
    request_list = kwargs.get('vSDN_requests', [])

    futures = [None] * len(min_solutions)
    accepted_counts = [0] * len(min_solutions)
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as executor:
        for i, active_hypervisors in enumerate(min_solutions):
            future = executor.submit(
                network_operator.evaluate_hypervisor_placement, **{
                    'active_hypervisors': active_hypervisors,
                    'request_list': request_list
                })
            futures[i] = future

        for i, future in enumerate(futures):
            accepted_counts[i] = sum(future.result())

    # controllable_switches = [
    #     gu.check_contoller_ability(solution, **kwargs) for solution in solutions
    # ]

    return {
        'active hypervisors':
        min_solutions[accepted_counts.index(max(accepted_counts))],
        'no. accepted':
        max(accepted_counts)
    }
    # if optimize == 'hypervisor count':
    # return {'active hypervisors': min(solutions, key=len)}
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
    """Searches for a hypervisor placement that maximizes
    the number of controllable switches of one controller."""
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

        placement_result = hp_multiple_greedy(
            **dict(kwargs,
                   network_operator=network_operator,
                   C=S,
                   F=H_usable,
                   Tc=Ts,
                   Tf=Th,
                   k=kwargs.get('h_count', 0)))

        if placement_result.get('no. accepted', 0) > result.get(
                'no. accepted', 0):
            print(f"Better controller found: {c}")
            result['main controller'] = c
            result['S_controllable'] = S_controllable
            result['Tc'] = Ts
            result.update(placement_result)

    print(f"No. active hypervisors: {result['active hypervisors']}")
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


def get_hypervisor_additional_switch_coverage(S, S_covered, H, H_used, Ts):
    """Returns the additional switch coverage of a hypervisor."""
    H_notused = list(set(H) - set(H_used))

    if not H_used:
        return {
            h: len(set().union(*[
                set(gu.covered_customers(Ts, [h, h_], S)) for h_ in H_notused
            ]))
            for h in H_notused
        }
    else:
        return {
            h:
            len(gu.covered_customers(Ts,
                                     list(H_used) + [h], S)) - len(S_covered)
            for h in H_notused
        }


def get_hypervisor_additional_controller_switch_coverage(H, H_used, Qhh):
    """Returns the additional switch coverage of a hypervisor."""
    H_notused = list(set(H) - set(H_used))

    if not H_used:
        return {
            h: len(set().union(*[Qhh.get((h, h_), []) for h_ in H])
                   | set().union(*[Qhh.get((h_, h), []) for h_ in H]))
            for h in H
        }
    else:
        # return {h: 0 for h in H_notused}
        return {
            h: len(set().union(*[
                Qhh.get((h1, h2), [])
                for h1, h2 in itertools.product([h] + list(H_used), [h] +
                                                list(H_used))
            ]))
            for h in H_notused
        }


def get_hypervisor_additional_request_coverage(S, C, H, H_used, Qhh, Qcs, R):
    """Returns the additional request cs coverage of a hypervisor."""
    H_notused = list(set(H) - set(H_used))

    if not H_used:
        return {h: 0 for h in H_notused}
    elif R is None:
        return {h: 0 for h in H_notused}

    # RS_mask: masks out switches that are not used by a request
    RS_mask = np.zeros((len(R), len(C), len(S)), dtype=bool)
    for r_idx, request in enumerate(R):
        for s in request.get_switches():
            RS_mask[r_idx, :, S.index(s)] = True

    # RCS_mask: masks out controller-switch pairs
    # that can be used by a request
    RCS_mask = np.zeros((len(R), len(C), len(S)), dtype=bool)
    # for r_idx, request in enumerate(R):
    for c_idx, c in enumerate(C):
        for s in S:
            if len(Qcs.get((c, s), [])):
                RCS_mask[:, c_idx, S.index(s)] = True
    C_mask = np.sum(np.logical_and(RCS_mask, RS_mask),
                    axis=2) == np.sum(RS_mask, axis=2)
    RCS_mask = np.logical_and(
        RCS_mask,
        np.logical_and(
            RS_mask, np.concatenate([C_mask[:, :, np.newaxis]] * len(S),
                                    axis=2)))

    CS_current = np.zeros((len(C), len(S)), dtype=bool)
    for h, h_ in itertools.product(H_used, H_used):
        for c, s in Qhh.get((h, h_), []):
            CS_current[C.index(c), S.index(s)] = True

    additional_coverage = {h: 0 for h in H_notused}
    for h in H_notused:
        CS_new = np.zeros((len(C), len(S)), dtype=bool)
        for h1, h2 in itertools.product([h] + list(H_used),
                                        [h] + list(H_used)):
            for c, s in Qhh.get((h1, h2), []):
                CS_new[C.index(c), S.index(s)] = True

        additional_coverage[h] = (np.sum(np.logical_and(CS_new, RCS_mask)) -
                                  np.sum(np.logical_and(CS_current, RCS_mask)))

    return additional_coverage


def hp_combined_S_CS(network_operator=None,
                     S=None,
                     H=None,
                     C=None,
                     Qcs=None,
                     Qhh=None,
                     Ts=None,
                     n_hypervisors=None,
                     **kwargs):
    """Greedy algorithm for the combined switch and controller placement problem."""

    if network_operator is not None and (S is None or H is None or Qhh is None
                                         or Ts is None):
        S = network_operator.nodes
        H = network_operator.possible_hypervisors
        C = network_operator.possible_controllers
        Ts = network_operator.triplets_by_switches
        Qcs = network_operator.quartets_by_cs
        Qhh = network_operator.quartets_by_hh

    R = kwargs.get('vSDN_requests', None)

    if n_hypervisors is None or n_hypervisors < 2 or (H is not None and
                                                      n_hypervisors > len(H)):
        raise ValueError

    # Initialization
    S_covered = set()
    H_used = set()
    hypervisor_additional_switch_coverage = get_hypervisor_additional_switch_coverage(
        S, S_covered, H, H_used, Ts)
    hypervisor_additional_controller_switch_coverage = get_hypervisor_additional_controller_switch_coverage(
        H, H_used, Qhh)
    hypervisor_additional_request_coverage = get_hypervisor_additional_request_coverage(
        S, C, H, H_used, Qhh, Qcs, R)

    # Main loop
    while len(H_used) < n_hypervisors and len(S_covered) < len(S):
        logging.debug("Additional switch coverage: %s",
                      hypervisor_additional_switch_coverage)
        logging.debug("Additional controller-switch coverage: %s",
                      hypervisor_additional_controller_switch_coverage)
        logging.debug("Additional request coverage: %s",
                      hypervisor_additional_request_coverage)
        # Select subset of hypervisors with highest combined coverage
        combined_additional_coverage = {
            h: hypervisor_additional_switch_coverage[h] +
            max(1, max(hypervisor_additional_switch_coverage.values())) *
            (hypervisor_additional_controller_switch_coverage[h] / max(
                1,
                max(hypervisor_additional_controller_switch_coverage.values()))
             ) + max(1, max(hypervisor_additional_switch_coverage.values())) *
            (hypervisor_additional_request_coverage[h] /
             max(1, max(hypervisor_additional_request_coverage.values())))
            for h in hypervisor_additional_switch_coverage.keys()
        }
        logging.debug("Combined additional coverage: %s",
                      combined_additional_coverage)

        h = max(combined_additional_coverage,
                key=combined_additional_coverage.get)
        H_used.add(h)
        S_covered.update(gu.covered_customers(Ts, H_used, S))
        logging.debug("H_used: %s", H_used)

        # Update additional switch coverage
        hypervisor_additional_switch_coverage = get_hypervisor_additional_switch_coverage(
            S, S_covered, H, H_used, Ts)
        hypervisor_additional_controller_switch_coverage = get_hypervisor_additional_controller_switch_coverage(
            H, H_used, Qhh)
        hypervisor_additional_request_coverage = get_hypervisor_additional_request_coverage(
            S, C, H, H_used, Qhh, Qcs, R)

    return {
        'active hypervisors': H_used,
        'hypervisor assignment': hypervisor_assignment(S, H_used, Qhh),
    }


def hypervisor_assignment(S, H_used, Qhh):
    Q_counts = {}
    for h1, h2 in itertools.product(H_used, H_used):
        Q_counts[(h1, h2)] = Counter([s for (c, s) in Qhh.get((h1, h2), [])])
    logging.debug("Q_counts: %s", Q_counts)

    hypervisor_assignment = {
        s: max(Q_counts, key=lambda x: Q_counts[x][s])
        for s in S
    }
    logging.debug("Hypervisor assignment: %s", hypervisor_assignment)
    return hypervisor_assignment


@measure
def hypervisor_placement_solutions(hp_type: str = 'heuristics',
                                   hp_objective: str = 'hypervisor count',
                                   **kwargs):
    if hp_type == 'heuristics':
        if hp_objective == 'hypervisor count':
            return hp_multiple_greedy(**kwargs)
        elif hp_objective == 'main controller':
            return hp_main_controller(**kwargs)
        elif hp_objective == 'overall coverage':
            return hp_overall_coverage(**kwargs)
        elif hp_objective == 'combined S CS':
            return hp_combined_S_CS(**kwargs)
    elif hp_type == 'ilp':
        if hp_objective == 'hypervisor count':
            return ilp.lcrhpp_minh(**kwargs)
        elif hp_objective == 'acceptance ratio':
            return ilp.lcrhpp_maxa(**kwargs)
        elif hp_objective == 'acceptance and flexibility':
            return ilp.lcrhpp_max_af(**kwargs)

    return None