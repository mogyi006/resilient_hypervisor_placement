# Standard library imports.
import itertools
import logging
import collections

# Related third party imports.
import gurobipy as gp
from gurobipy import GRB

# Local application/library specific imports.
import src.models.metrics as metrics
import src.models.objectives as objectives


def dict_to_string(d):
    if set(map(type, d.values())).issubset({float, int}):
        return str({k: v for k, v in d.items() if v > 0})
    else:
        return str(len(d))


def lcrhpp_minh(network_operator=None,
                hypervisor_capacity: int = None,
                **kwargs):
    logging.info('Starting ILP with the following parameters:')
    logging.debug(
        f'Latency requirement: {network_operator.get_latency_factor()}')
    logging.debug(f'Hypervisor capacity: {hypervisor_capacity}')

    S = list(network_operator.nodes)
    H = list(network_operator.possible_hypervisors)
    H_pairs = list(itertools.combinations_with_replacement(H, 2))
    HS_pairs = list(itertools.product(H, S))
    HHS_pairs = list(itertools.product(H_pairs, S))
    allowed_switch_H_pairs = network_operator.get_allowed_hypervisor_pairs_by_switch(
    )

    with gp.Model(env=env) as model:
        active_hypervisors = model.addVars(H, vtype=GRB.BINARY)
        hypervisor_controls_switch = model.addVars(HS_pairs, vtype=GRB.BINARY)
        load_dict = {}
        load_dict['hypervisor_load'] = model.addVars(H, vtype=GRB.INTEGER)
        load_dict['hypervisor_load_max'] = model.addVar(vtype=GRB.INTEGER)
        hypervisor_pair_controls_switch = model.addVars(HHS_pairs,
                                                        vtype=GRB.BINARY)

        # Only active hypervisors can control switches
        # Hypervisors without controlled switches are inactive
        c_1 = model.addConstrs(active_hypervisors[h] == gp.or_(
            [hypervisor_controls_switch[(h, s)] for s in S]) for h in H)

        # Each switch is controlled by a pair of hypervisors
        # except when there is a hypervisor at the switch’s location
        c_2a = model.addConstrs(
            active_hypervisors[s] <= hypervisor_controls_switch[(s, s)]
            for s in S)
        # c_2a = model.addConstrs(active_hypervisors[s] <= hypervisor_pair_controls_switch[((s,s),s)] for s in S)
        c_2b = model.addConstrs(
            hypervisor_controls_switch[(s, s)] +
            gp.LinExpr([(1, hypervisor_controls_switch[(h, s)])
                        for h in H]) == 2 for s in S)

        # The hypervisor pair controls the switch if both of them are controlling it
        c_3 = model.addConstrs(hypervisor_pair_controls_switch[((
            h1, h2), s)] == gp.and_(hypervisor_controls_switch[(
                h1, s)], hypervisor_controls_switch[(h2, s)])
                               for (h1, h2), s in HHS_pairs
                               if not (h1 == h2 and h1 != s))

        # Only valid triplets (T) can appear
        c_4 = model.addConstrs(
            gp.quicksum([
                hypervisor_pair_controls_switch[((h1, h2), s)]
                for h1, h2 in allowed_switch_H_pairs[s] if h1 in H and h2 in H
            ]) == 1 for s in S)

        # Each hypervisor can control at most 'hypervisor_capacity' switches
        if hypervisor_capacity is None:
            hypervisor_capacity = len(S)
        c_5a = model.addConstrs(load_dict['hypervisor_load'][h] == gp.quicksum(
            [hypervisor_controls_switch[(h, s)] for s in S]) for h in H)
        c_5b = model.addConstrs(
            load_dict['hypervisor_load'][h] <= hypervisor_capacity for h in H)
        c_5c = model.addConstr(load_dict['hypervisor_load_max'] == gp.max_(
            load_dict['hypervisor_load']))

        # Minimize the number of hypervisors
        # model.setObjective(gp.quicksum(active_hypervisors), GRB.MINIMIZE)
        metrics.add_objectives(
            model,
            active_hypervisors=active_hypervisors,
            hypervisor_load_max=load_dict['hypervisor_load_max'],
            **kwargs)
        model.optimize()

        logging.info('Optimization finished')

        result = {
            'active_hypervisors':
            [h for h, v in active_hypervisors.items() if v.x > 0.9],
            'hypervisor assignment': {
                s: (h1, h2)
                for ((h1, h2),
                     s), v in hypervisor_pair_controls_switch.items()
                if v.x > 0.9
            },
            'hypervisor_load': {
                h: sum([hypervisor_controls_switch[(h, s)].x > 0.9 for s in S])
                for h in H
            },
            'hypervisor_load_max':
            int(load_dict['hypervisor_load_max'].x),
            'hypervisor2switch control paths': []
        }

        logging.info(f"Active hypervisors: {result['active_hypervisors']}")
        logging.info(f"Hypervisor load max: {result['hypervisor_load_max']}")
        logging.info(
            f"Hypervisor load: {dict_to_string(result['hypervisor_load'])}")

        return result


def lcrhpp(network_operator,
           hp_objectives: tuple = ('hypervisor_count', ),
           vSDN_requests = None,
           n_hypervisors: int = None,
           n_diff_hypervisors: int = 0,
           flexibility_weight: float = None,
           hypervisor_capacity: float = None,
           controller_capacity: float = None,
           required_vSDN_requests = None,
           prev_active_hypervisors: list = None,
           n_possible_changes: int = None,
           **kwargs):
    logging.info('Starting ILP with the following parameters:')
    if vSDN_requests is None:
        vSDN_requests = []

    for var_name, var_value in locals().items():
        string = f"{var_name.replace('_', ' ').title()}: "
        if type(var_value) in [int, float, str, tuple, type(None)]:
            logging.debug(string + str(var_value))
        elif type(var_value) in [list, dict]:
            logging.debug(string + str(len(var_value)))
        # else:
        #     logging.debug(string + str(type(var_value)))

    S = list(network_operator.nodes)
    H = list(network_operator.possible_hypervisors)
    C = list(network_operator.possible_controllers)
    H_pairs = list(itertools.combinations_with_replacement(H, 2))
    HS_pairs = list(itertools.product(H, S))
    HHS_pairs = list(itertools.product(H_pairs, S))
    CS_pairs = list(itertools.product(C, S))
    R = {r.get_id(): r for r in vSDN_requests}
    CR_pairs = list(itertools.product(C, R.keys()))

    allowed_switch_H_pairs = network_operator.get_allowed_hypervisor_pairs_by_switch(get_all=True)
    for switch, pairs in allowed_switch_H_pairs.items():
        allowed_switch_H_pairs[switch] = []
        for pair in pairs:
            if pair in H_pairs:
                allowed_switch_H_pairs[switch].append(pair)
            elif (pair[1], pair[0]) in H_pairs:
                allowed_switch_H_pairs[switch].append((pair[1], pair[0]))
    allowed_cs_H_pairs = network_operator.quartets_by_cs
    for cs, pairs in allowed_cs_H_pairs.items():
        allowed_cs_H_pairs[cs] = []
        for pair in pairs:
            if pair in H_pairs:
                allowed_cs_H_pairs[cs].append(pair)
            elif (pair[1], pair[0]) in H_pairs:
                allowed_cs_H_pairs[cs].append((pair[1], pair[0]))

    with gp.Env() as env, gp.Model(env=env) as model:
        model.setParam('OutputFlag', 0)
        # ! Primary ILP
        active_hypervisors = model.addVars(H, vtype=GRB.BINARY)
        hypervisor_controls_switch = model.addVars(HS_pairs, vtype=GRB.BINARY)
        load_dict = {}
        load_dict['hypervisor_load'] = model.addVars(H, vtype=GRB.INTEGER)
        load_dict['hypervisor_load_max'] = model.addVar(vtype=GRB.INTEGER)
        hypervisor_pair_controls_switch = model.addVars(HHS_pairs,
                                                        vtype=GRB.BINARY)
        controller_controls_switch = model.addVars(CS_pairs, vtype=GRB.BINARY)

        controller_can_control_request = model.addVars(CR_pairs,
                                                       vtype=GRB.BINARY)
        controller_controls_request = model.addVars(CR_pairs, vtype=GRB.BINARY)
        load_dict['controller_load_switch'] = model.addVars(C,
                                                            vtype=GRB.INTEGER)
        load_dict['controller_load_switch_max'] = model.addVar(
            vtype=GRB.INTEGER)
        load_dict['controller_load_request'] = model.addVars(C,
                                                             vtype=GRB.INTEGER)
        load_dict['controller_load_request_max'] = model.addVar(
            vtype=GRB.INTEGER)
        controllable_request = model.addVars(R.keys(), vtype=GRB.BINARY)
        load_dict['switch_load'] = model.addVars(S, vtype=GRB.INTEGER)
        load_dict['switch_load_max'] = model.addVar(vtype=GRB.INTEGER)
        load_dict['switch_load_total'] = model.addVar(vtype=GRB.INTEGER)
        load_dict['switch_load_time'] = model.addVars(S, vtype=GRB.INTEGER)
        load_dict['switch_load_time_total'] = model.addVar(vtype=GRB.INTEGER)
        load_dict['vSDN_QoS_total'] = model.addVar(vtype=GRB.INTEGER)
        load_dict['vSDN_revenue_total'] = model.addVar(vtype=GRB.INTEGER)

        # Only active hypervisors can control switches
        # Hypervisors without controlled switches are inactive
        c_1 = model.addConstrs(active_hypervisors[h] == gp.or_(
            [hypervisor_controls_switch[(h, s)] for s in S]) for h in H)

        # Each switch is controlled by a pair of hypervisors
        # Except when there is a hypervisor at the switch’s location
        c_2a = model.addConstrs(
            active_hypervisors[h] <= hypervisor_controls_switch[(h, h)]
            for h in H)
        # c_2a = model.addConstrs(active_hypervisors[s] <= hypervisor_pair_controls_switch[((s,s),s)] for s in S)
        c_2b = model.addConstrs(
            gp.LinExpr([(1, hypervisor_controls_switch[(h, s)]) if h != s else (2, hypervisor_controls_switch[(h, s)])
                        for h in H]) == 2 for s in S)
        # c_2b = model.addConstrs(gp.quicksum([hypervisor_pair_controls_switch[((h1,h2),s)] for h1,h2 in H_pairs]) == 1 for s in S)

        if prev_active_hypervisors and n_possible_changes is not None:
            c_2c = model.addConstr(
                gp.quicksum([
                    active_hypervisors[h] for h in prev_active_hypervisors
                ]) >= len(prev_active_hypervisors) - n_possible_changes)

        # The hypervisor pair controls the switch if both of them are controlling it
        c_3 = model.addConstrs(hypervisor_pair_controls_switch[((
            h1, h2), s)] == gp.and_(hypervisor_controls_switch[(
                h1, s)], hypervisor_controls_switch[(h2, s)])
                               for (h1, h2), s in HHS_pairs
                               if not (h1 == h2 and h1 != s))

        # Only valid triplets (T) can appear
        c_4 = model.addConstrs(
            gp.quicksum([
                hypervisor_pair_controls_switch[((h1, h2), s)]
                for h1, h2 in allowed_switch_H_pairs[s]
            ]) == 1 for s in S)

        # Each hypervisor can control at most 'hypervisor_capacity' switches
        if hypervisor_capacity is None:
            hypervisor_capacity = len(S)
        else:
            hypervisor_capacity = min(int(hypervisor_capacity * len(S)),
                                      len(S))

        if (n_hypervisors is not None and (hypervisor_capacity * n_hypervisors
                                           < 2 * len(S) - n_hypervisors)):
            logging.warning(
                f"Given hypervisor capacity ({hypervisor_capacity}) is too low"
                + f" for the given number of hypervisors ({n_hypervisors}).")
            hypervisor_capacity = (int(
                (2 * len(S) - n_hypervisors) / n_hypervisors) + int(
                    (2 * len(S) - n_hypervisors) % n_hypervisors > 0))
            logging.warning(
                f"Setting hypervisor capacity to {hypervisor_capacity}.")

        c_5a = model.addConstrs(load_dict['hypervisor_load'][h] == gp.quicksum(
            [hypervisor_controls_switch[(h, s)] for s in S]) for h in H)
        c_5b = model.addConstrs(
            load_dict['hypervisor_load'][h] <= hypervisor_capacity for h in H)
        c_5c = model.addConstr(load_dict['hypervisor_load_max'] == gp.max_(
            load_dict['hypervisor_load']))

        # The number of active hypervisors cannot exceed the given hypervisor count
        if n_hypervisors is None:
            if hp_objectives[0] != 'hypervisor_count':
                hp_objectives = ('hypervisor_count', ) + hp_objectives
        else:
            c_6 = model.addConstr(
                gp.quicksum(active_hypervisors) <= n_hypervisors)

        # If a good hypervisor pair controls the switch then the controller is able to control it
        c_7 = model.addConstrs(controller_controls_switch[(c, s)] == gp.or_([
            hypervisor_pair_controls_switch[((h1, h2), s)]
            for h1, h2 in allowed_cs_H_pairs.get((c, s), [])
        ]) for c, s in CS_pairs)

        # The request can be accepted with the controller if it can control all of its switches
        c_8 = model.addConstrs(
            controller_can_control_request[(c, r)] == gp.and_([
                controller_controls_switch[(c, s)]
                for s in R[r].get_switches()
            ]) for c, r in CR_pairs)

        # The request can be accepted with the controller if it can be controlled by the controller
        c_8 = model.addConstrs(controller_controls_request[(
            c, r)] <= controller_can_control_request[(c, r)]
                               for c, r in CR_pairs)
        # Each request can only have one controller
        c_8 = model.addConstrs(
            gp.quicksum([controller_controls_request[(c, r)] for c in C]) <= 1
            for r in R)

        # The request is acceptable if there is a controller that can control all of its switches
        c_9a = model.addConstrs(controllable_request[r] == gp.or_(
            [controller_controls_request[(c, r)] for c in C]) for r in R)
        c_9b = model.addConstrs(load_dict['switch_load'][s] == gp.quicksum(
            [controllable_request[r] for r in R if s in R[r].get_switches()])
                                for s in S)
        c_9c = model.addConstr(
            load_dict['switch_load_max'] == gp.max_(load_dict['switch_load']))
        c_9d = model.addConstr(load_dict['switch_load_total'] == gp.quicksum(
            load_dict['switch_load']))
        c_9f = model.addConstrs(
            load_dict['switch_load_time'][s] == gp.quicksum([
                controllable_request[r] * R[r].get_TTL() for r in R
                if s in R[r].get_switches()
            ]) for s in S)
        c_9e = model.addConstr(load_dict['switch_load_time_total'] ==
                               gp.quicksum(load_dict['switch_load_time']))
        c_9e = model.addConstr(load_dict['vSDN_QoS_total'] == gp.quicksum(
            controllable_request[r] * R[r].get_QoS() for r in R))
        c_9e = model.addConstr(load_dict['vSDN_revenue_total'] == gp.quicksum(
            controllable_request[r] * metrics.vSDN_metrics['revenue'](R[r])
            for r in R))

        # Some requests must be accepted
        if required_vSDN_requests is not None:
            c_10 = model.addConstrs(controllable_request[r] == 1 for r in R
                                    if r in required_vSDN_requests)

        # Each controller can control at most 'controller_capacity' requests
        if controller_capacity is None:
            controller_capacity = len(R)
        else:
            controller_capacity = min(int(controller_capacity * len(R)),
                                      len(R))

        if required_vSDN_requests:
            controller_capacity = max(
                collections.Counter([
                    R[r].get_controller() for r in required_vSDN_requests
                ]).most_common(1)[0][1], controller_capacity)

        c_11a = model.addConstrs(
            load_dict['controller_load_request'][c] == gp.quicksum(
                [controller_controls_request[(c, r)] for r in R]) for c in C)
        c_11b = model.addConstrs(
            load_dict['controller_load_request'][c] <= controller_capacity
            for c in C)
        c_11c = model.addConstr(load_dict['controller_load_request_max'] ==
                                gp.max_(load_dict['controller_load_request']))
        c_11d = model.addConstrs(
            load_dict['controller_load_switch'][c] == gp.quicksum([
                controller_controls_request[(c, r)] * len(R[r].get_switches())
                for r in R
            ]) for c in C)
        c_11e = model.addConstr(load_dict['controller_load_switch_max'] ==
                                gp.max_(load_dict['controller_load_switch']))

        # ! Secondary ILP
        if flexibility_weight is not None:
            active_hypervisors_2 = model.addVars(H, vtype=GRB.BINARY)
            active_hypervisors_or = model.addVars(H, vtype=GRB.BINARY)
            active_hypervisors_and = model.addVars(H, vtype=GRB.BINARY)
            hypervisor_controls_switch_2 = model.addVars(HS_pairs,
                                                         vtype=GRB.BINARY)
            hypervisor_pair_controls_switch_2 = model.addVars(HHS_pairs,
                                                              vtype=GRB.BINARY)
            controller_controls_switch_2 = model.addVars(CS_pairs,
                                                         vtype=GRB.BINARY)
            controller_can_control_request_2 = model.addVars(CR_pairs,
                                                             vtype=GRB.BINARY)
            controller_controls_request_2 = model.addVars(CR_pairs,
                                                          vtype=GRB.BINARY)
            controllable_request_2 = model.addVars(R.keys(), vtype=GRB.BINARY)

            # Only active hypervisors can control switches
            # Hypervisors without controlled switches are inactive
            c_1 = model.addConstrs(active_hypervisors_2[h] == gp.or_(
                [hypervisor_controls_switch_2[(h, s)] for s in S]) for h in H)

            # Each switch is controlled by a pair of hypervisors
            # Except when there is a hypervisor at the switch’s location
            c_2a = model.addConstrs(
                active_hypervisors_2[s] <= hypervisor_controls_switch_2[(s, s)]
                for s in S)
            c_2b = model.addConstrs(
                hypervisor_controls_switch_2[(s, s)] +
                gp.LinExpr([(1, hypervisor_controls_switch_2[(h, s)])
                            for h in H]) == 2 for s in S)

            # The hypervisor pair controls the switch if both of them are controlling it
            c_3 = model.addConstrs(hypervisor_pair_controls_switch_2[((
                h1, h2), s)] == gp.and_(hypervisor_controls_switch_2[(
                    h1, s)], hypervisor_controls_switch_2[(h2, s)])
                                   for (h1, h2), s in HHS_pairs
                                   if not (h1 == h2 and h1 != s))

            # Only valid triplets (T) can appear
            c_4 = model.addConstrs(
                gp.quicksum([
                    hypervisor_pair_controls_switch_2[((h1, h2), s)]
                    for h1, h2 in allowed_switch_H_pairs[s] if h1 in H and h2 in H
                ]) == 1 for s in S)

            # Each hypervisor can control at most 'hypervisor_capacity' switches
            if hypervisor_capacity is None:
                hypervisor_capacity = len(S)
            c_5 = model.addConstrs(
                gp.quicksum([hypervisor_controls_switch_2[(h, s)]
                             for s in S]) <= hypervisor_capacity for h in H)

            # The number of active hypervisors cannot exceed the given hypervisor count
            c_6 = model.addConstr(
                gp.quicksum(active_hypervisors_2) <= n_hypervisors)

            # If a good hypervisor pair controls the switch then the controller is able to control it
            c_7 = model.addConstrs(
                controller_controls_switch_2[(c, s)] == gp.or_([
                    hypervisor_pair_controls_switch_2[((h1, h2), s)]
                    for h1, h2 in allowed_cs_H_pairs.get((c, s), []) if h1 in H and h2 in H
                ]) for c, s in CS_pairs)

            # The request can be accepted with the controller if it can control all of its switches
            c_8 = model.addConstrs(
                controller_can_control_request_2[(c, r)] == gp.and_([
                    controller_controls_switch_2[(c, s)]
                    for s in R[r].get_switches()
                ]) for c, r in CR_pairs)

            # The request can be accepted with the controller if it can be controlled by the controller
            c_8 = model.addConstrs(controller_controls_request_2[(
                c, r)] <= controller_can_control_request_2[(c, r)]
                                   for c, r in CR_pairs)

            # The request is acceptable if there is a controller that can control all of its switches
            c_9 = model.addConstrs(controllable_request_2[r] == gp.or_(
                [controller_controls_request_2[(c, r)] for c in C]) for r in R)

            # Some requests must be accepted
            if required_vSDN_requests is not None:
                c_10 = model.addConstrs(controllable_request_2[r] == 1
                                        for r in R
                                        if r in required_vSDN_requests)

            # Each controller can control at most 'controller_capacity' requests
            if controller_capacity is None:
                controller_capacity = len(R)
            c_11 = model.addConstrs(
                gp.quicksum([controller_controls_request_2[(c, r)]
                             for r in R]) <= controller_capacity for c in C)

            # The primary and secondary ILP must differ in at most 'n_hypervisors_difference' hypervisors
            # c_12 = model.addConstrs(
            #     active_hypervisors_difference[h] == (active_hypervisors[h] -
            #                                          active_hypervisors_2[h])
            #     for h in H)
            # c_13 = model.addConstrs(active_hypervisors_abs_difference[h] ==
            #                         gp.abs_(active_hypervisors_difference[h])
            #                         for h in H)
            # c_14 = model.addConstr(
            #     gp.quicksum(active_hypervisors_abs_difference) == (
            #         2 * n_diff_hypervisors))

            c_12 = model.addConstrs(active_hypervisors_or[h] == gp.or_(
                active_hypervisors[h], active_hypervisors_2[h]) for h in H)
            c_13 = model.addConstrs(active_hypervisors_and[h] == gp.and_(
                active_hypervisors[h], active_hypervisors_2[h]) for h in H)
            c_14 = model.addConstr(
                active_hypervisors_or.sum() <= active_hypervisors_and.sum() +
                (2 * n_diff_hypervisors))

            controllable_request_any = model.addVars(R, vtype=GRB.BINARY)
            model.addConstrs(controllable_request_any[r] == gp.or_(
                controllable_request[r], controllable_request_2[r]) for r in R)

            controllable_request_both = model.addVars(R, vtype=GRB.BINARY)
            model.addConstrs(controllable_request_both[r] == gp.and_(
                controllable_request[r], controllable_request_2[r]) for r in R)

        if flexibility_weight is None:
            objectives.add_objectives(
                model=model,
                hp_objectives=hp_objectives,
                active_hypervisors=active_hypervisors,
                vSDN_requests=R,
                controllable_request=controllable_request,
                hypervisor_load_max=load_dict['hypervisor_load_max'],
                controller_load_request_max=load_dict[
                    'controller_load_request_max'],
                controller_load_switch_max=load_dict[
                    'controller_load_switch_max'],
                switch_load_total=load_dict['switch_load_total'],
                switch_load_time_total=load_dict['switch_load_time_total'],
                vSDN_QoS_total=load_dict['vSDN_QoS_total'],
                vSDN_revenue_total=load_dict['vSDN_revenue_total'],
                **kwargs)
        elif flexibility_weight == 0:
            model.setObjectiveN(controllable_request.sum(), 0, 2)
            model.setObjectiveN(controllable_request_any.sum(), 1, 1)
            model.setObjectiveN(controllable_request_2.sum(), 2, 0)
            model.modelSense = GRB.MAXIMIZE
        else:
            model.setObjectiveN(controllable_request.sum(),
                                index=0,
                                priority=1,
                                weight=1)
            model.setObjectiveN((controllable_request_2.sum() -
                                 controllable_request_both.sum()),
                                index=1,
                                priority=1,
                                weight=flexibility_weight)
            model.setObjectiveN(controllable_request_2.sum(),
                                index=2,
                                priority=0)
            model.modelSense = GRB.MAXIMIZE

        model.optimize()

        logging.info("Optimization finished.")
        logging.info(f"Solution status: {model.Status}")

        logging.info(f"Active hypervisors: {active_hypervisors}")

        result = {
            'active_hypervisors':
            [h for h, v in active_hypervisors.items() if v.x > 0.9],
            'hypervisor assignment': {
                s: (h1, h2)
                for ((h1, h2),
                     s), v in hypervisor_pair_controls_switch.items()
                if v.x > 0.9
            },
            'hypervisor2switch control paths': [],
            'vSDN_accepted_count_ilp':
            sum(v.x > 0.9 for v in controllable_request.values()),
            'hp_objective':
            model.ObjVal,
            'request status':
            {id_: v.x > 0.9
             for id_, v in controllable_request.items()},
        }

        for var_name, var_value in load_dict.items():
            if isinstance(var_value, gp.Var):
                result[var_name + '_ilp'] = int(round(var_value.x))
            else:
                result[var_name +
                       '_ilp'] = {k: int(v.x)
                                  for k, v in var_value.items()}

        logging.info((
            "No. accepted requests (1): " +
            #  f"{sum(v.x > 0.9 for v in controllable_request.values())}" +
            f"{result['vSDN_accepted_count_ilp']}" + f" / {len(R)}"))
        if flexibility_weight is not None:
            logging.info(
                ("No. accepted requests (2): " +
                 f"{sum(v.x > 0.9 for v in controllable_request_2.values())}" +
                 f" / {len(R)}"))
            logging.info(
                ("No. accepted requests (1+2): " +
                 f"{sum(v.x > 0.9 for v in controllable_request_any.values())}"
                 + f" / {len(R)}"))
            logging.info((
                "No. new accepted requests (2-1): " +
                f"""{sum(v.x > 0.9 for r, v in controllable_request_2.items()
                    if v.x > 0.9 and controllable_request[r].x < 0.9)}""" +
                f" / {len(R) - sum(v.x > 0.9 for v in controllable_request.values())}"
            ))

        logging.info(f"Active hypervisors (1): {result['active_hypervisors']}")

        if flexibility_weight is not None:
            logging.info(
                ("Replaced hypervisors: " +
                 f"""{sum(1 for h in H if active_hypervisors[h].x > 0.9
                and active_hypervisors_2[h].x < 0.9)}""" +
                 f" / {n_diff_hypervisors}"))
            logging.info(
                "Active hypervisors (2): " +
                f"{[h for h, v in active_hypervisors_2.items() if v.x > 0.9]}")
        if flexibility_weight is not None:
            result['request status'] = {
                id_: v.x > 0.9
                for id_, v in controllable_request_2.items()
            }

        for name, value in result.items():
            string = f"{name}: "
            if isinstance(value, dict):
                string += dict_to_string(value)
            else:
                string += str(value)
            logging.info(string)

        return result
