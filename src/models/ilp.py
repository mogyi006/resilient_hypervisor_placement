# Standard library imports.
import itertools
import logging

# Related third party imports.
import gurobipy as gp
from gurobipy import GRB
env = gp.Env()

# Local application/library specific imports.
import src.data.graph_utilities as gu
import src.models.objectives as objectives


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
                for h1, h2 in allowed_switch_H_pairs[s]
            ]) == 1 for s in S)

        # Each hypervisor can control at most 'hypervisor_capacity' switches
        if hypervisor_capacity is None:
            hypervisor_capacity = len(S)
        c_5 = model.addConstrs(
            gp.quicksum([hypervisor_controls_switch[(h, s)]
                         for s in S]) <= hypervisor_capacity for h in H)

        # Minimize the number of hypervisors
        model.setObjective(gp.quicksum(active_hypervisors), GRB.MINIMIZE)
        model.optimize()

        result = {
            'active hypervisors':
            [h for h, v in active_hypervisors.items() if v.x > 0.9],
            'hypervisor assignment': {
                s: (h1, h2)
                for ((h1, h2),
                     s), v in hypervisor_pair_controls_switch.items()
                if v.x > 0.9
            },
            'hypervisor2switch control paths': []
        }
        # print(result['active hypervisors'])
        # print(result['hypervisor assignment'])
        return result


def lcrhpp_maxa(network_operator,
                vSDN_requests,
                n_hypervisors: int,
                hypervisor_capacity: int = None,
                controller_capacity: int = None,
                required_vSDN_requests=None,
                **kwargs):
    # print("Start LC RHPP max A")
    S = list(network_operator.nodes)
    H = list(network_operator.possible_hypervisors)
    C = list(network_operator.possible_controllers)
    H_pairs = list(itertools.combinations_with_replacement(H, 2))
    HS_pairs = list(itertools.product(H, S))
    HHS_pairs = list(itertools.product(H_pairs, S))
    CS_pairs = list(itertools.product(C, S))
    R = {r.get_id(): r for r in vSDN_requests}
    CR_pairs = list(itertools.product(C, R.keys()))

    allowed_switch_H_pairs = network_operator.get_allowed_hypervisor_pairs_by_switch(
        get_all=True)
    allowed_cs_H_pairs = network_operator.quartets_by_cs

    with gp.Model(env=env) as model:
        active_hypervisors = model.addVars(H, vtype=GRB.BINARY)
        hypervisor_controls_switch = model.addVars(HS_pairs, vtype=GRB.BINARY)
        hypervisor_pair_controls_switch = model.addVars(HHS_pairs,
                                                        vtype=GRB.BINARY)
        controller_controls_switch = model.addVars(CS_pairs, vtype=GRB.BINARY)
        controller_can_control_request = model.addVars(CR_pairs,
                                                       vtype=GRB.BINARY)
        controller_controls_request = model.addVars(CR_pairs, vtype=GRB.BINARY)
        controllable_request = model.addVars(R.keys(), vtype=GRB.BINARY)

        # Only active hypervisors can control switches
        # Hypervisors without controlled switches are inactive
        c_1 = model.addConstrs(active_hypervisors[h] == gp.or_(
            [hypervisor_controls_switch[(h, s)] for s in S]) for h in H)

        # Each switch is controlled by a pair of hypervisors
        # Except when there is a hypervisor at the switch’s location
        c_2a = model.addConstrs(
            active_hypervisors[s] <= hypervisor_controls_switch[(s, s)]
            for s in S)
        # c_2a = model.addConstrs(active_hypervisors[s] <= hypervisor_pair_controls_switch[((s,s),s)] for s in S)
        c_2b = model.addConstrs(
            hypervisor_controls_switch[(s, s)] +
            gp.LinExpr([(1, hypervisor_controls_switch[(h, s)])
                        for h in H]) == 2 for s in S)
        # c_2b = model.addConstrs(gp.quicksum([hypervisor_pair_controls_switch[((h1,h2),s)] for h1,h2 in H_pairs]) == 1 for s in S)

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
        c_5 = model.addConstrs(
            gp.quicksum([hypervisor_controls_switch[(h, s)]
                         for s in S]) <= hypervisor_capacity for h in H)

        # The number of active hypervisors cannot exceed the given hypervisor count
        c_6 = model.addConstr(gp.quicksum(active_hypervisors) <= n_hypervisors)

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

        # The request is acceptable if there is a controller that can control all of its switches
        c_9 = model.addConstrs(controllable_request[r] == gp.or_(
            [controller_controls_request[(c, r)] for c in C]) for r in R)

        # Some requests must be accepted
        if required_vSDN_requests is not None:
            c_10 = model.addConstrs(controllable_request[r] == 1 for r in R
                                    if r in required_vSDN_requests)

        # Each controller can control at most 'controller_capacity' requests
        if controller_capacity is None:
            controller_capacity = len(R)
        c_11 = model.addConstrs(
            gp.quicksum([controller_controls_request[(c, r)]
                         for r in R]) <= controller_capacity for c in C)

        # Maximize the acceptance ratio
        # model.setObjective(
        #     gp.quicksum(controllable_request) / len(R), GRB.MAXIMIZE)
        objectives.objectives[kwargs.get('ilp_objective_function',
                                         'maximize_average')](
                                             model=model,
                                             Vars=controllable_request,
                                             vSDN_requests=R)
        model.optimize()

        # print(model.ObjVal)

        result = {
            'active hypervisors':
            [h for h, v in active_hypervisors.items() if v.x > 0.9],
            'hypervisor assignment': {
                s: (h1, h2)
                for ((h1, h2),
                     s), v in hypervisor_pair_controls_switch.items()
                if v.x > 0.9
            },
            'hypervisor2switch control paths': [],
            'hp acceptance ratio':
            model.ObjVal,
            'request status':
            {id_: v.x > 0.9
             for id_, v in controllable_request.items()}
        }
        # print(result['active hypervisors'])
        # print(result['hypervisor assignment'])
        return result


def lcrhpp_max_af(network_operator,
                  vSDN_requests,
                  n_hypervisors: int,
                  n_diff_hypervisors: int = 0,
                  flexibility_weight: float = 1.,
                  hypervisor_capacity: int = None,
                  controller_capacity: int = None,
                  required_vSDN_requests=None,
                  **kwargs):
    logging.info('Starting ILP with the following parameters:')
    logging.debug(f'No. vSDN requests: {len(vSDN_requests)}')
    logging.debug(f'No. hypervisors: {n_hypervisors}')
    logging.debug(f'No. different hypervisors: {n_diff_hypervisors}')
    logging.debug(f'Flexibility weight: {flexibility_weight}')
    logging.debug(f'Hypervisor capacity: {hypervisor_capacity}')
    logging.debug(f'Controller capacity: {controller_capacity}')
    logging.debug(f"""No. required vSDN requests: {len(required_vSDN_requests)
        if required_vSDN_requests is not None else None}""")

    S = list(network_operator.nodes)
    H = list(network_operator.possible_hypervisors)
    C = list(network_operator.possible_controllers)
    H_pairs = list(itertools.combinations_with_replacement(H, 2))
    HS_pairs = list(itertools.product(H, S))
    HHS_pairs = list(itertools.product(H_pairs, S))
    CS_pairs = list(itertools.product(C, S))
    R = {r.get_id(): r for r in vSDN_requests}
    CR_pairs = list(itertools.product(C, R.keys()))

    allowed_switch_H_pairs = network_operator.get_allowed_hypervisor_pairs_by_switch(
        get_all=True)
    allowed_cs_H_pairs = network_operator.quartets_by_cs

    with gp.Model(env=env) as model:
        # ! Primary ILP
        active_hypervisors = model.addVars(H, vtype=GRB.BINARY)
        hypervisor_controls_switch = model.addVars(HS_pairs, vtype=GRB.BINARY)
        hypervisor_pair_controls_switch = model.addVars(HHS_pairs,
                                                        vtype=GRB.BINARY)
        controller_controls_switch = model.addVars(CS_pairs, vtype=GRB.BINARY)
        controller_can_control_request = model.addVars(CR_pairs,
                                                       vtype=GRB.BINARY)
        controller_controls_request = model.addVars(CR_pairs, vtype=GRB.BINARY)
        controllable_request = model.addVars(R.keys(), vtype=GRB.BINARY)

        # Only active hypervisors can control switches
        # Hypervisors without controlled switches are inactive
        c_1 = model.addConstrs(active_hypervisors[h] == gp.or_(
            [hypervisor_controls_switch[(h, s)] for s in S]) for h in H)

        # Each switch is controlled by a pair of hypervisors
        # Except when there is a hypervisor at the switch’s location
        c_2a = model.addConstrs(
            active_hypervisors[s] <= hypervisor_controls_switch[(s, s)]
            for s in S)
        # c_2a = model.addConstrs(active_hypervisors[s] <= hypervisor_pair_controls_switch[((s,s),s)] for s in S)
        c_2b = model.addConstrs(
            hypervisor_controls_switch[(s, s)] +
            gp.LinExpr([(1, hypervisor_controls_switch[(h, s)])
                        for h in H]) == 2 for s in S)
        # c_2b = model.addConstrs(gp.quicksum([hypervisor_pair_controls_switch[((h1,h2),s)] for h1,h2 in H_pairs]) == 1 for s in S)

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
        c_5 = model.addConstrs(
            gp.quicksum([hypervisor_controls_switch[(h, s)]
                         for s in S]) <= hypervisor_capacity for h in H)

        # The number of active hypervisors cannot exceed the given hypervisor count
        c_6 = model.addConstr(gp.quicksum(active_hypervisors) <= n_hypervisors)

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

        # The request is acceptable if there is a controller that can control all of its switches
        c_9 = model.addConstrs(controllable_request[r] == gp.or_(
            [controller_controls_request[(c, r)] for c in C]) for r in R)

        # Some requests must be accepted
        if required_vSDN_requests is not None:
            c_10 = model.addConstrs(controllable_request[r] == 1 for r in R
                                    if r in required_vSDN_requests)

        # Each controller can control at most 'controller_capacity' requests
        if controller_capacity is None:
            controller_capacity = len(R)
        c_11 = model.addConstrs(
            gp.quicksum([controller_controls_request[(c, r)]
                         for r in R]) <= controller_capacity for c in C)

        # ! Secondary ILP
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
                for h1, h2 in allowed_switch_H_pairs[s]
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
        c_7 = model.addConstrs(controller_controls_switch_2[(c, s)] == gp.or_([
            hypervisor_pair_controls_switch_2[((h1, h2), s)]
            for h1, h2 in allowed_cs_H_pairs.get((c, s), [])
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
            c_10 = model.addConstrs(controllable_request_2[r] == 1 for r in R
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

        if flexibility_weight == 0:
            model.setObjectiveN(controllable_request.sum(), 0, 2)
            model.setObjectiveN(controllable_request_any.sum(), 1, 1)
            model.setObjectiveN(controllable_request_2.sum(), 2, 0)
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

        model.ModelSense = GRB.MAXIMIZE
        model.optimize()

        logging.info("Optimization finished.")
        logging.info(
            ("No. accepted requests (1): " +
             f"{sum(v.x > 0.9 for v in controllable_request.values())}" +
             f" / {len(R)}"))
        logging.info(
            ("No. accepted requests (2): " +
             f"{sum(v.x > 0.9 for v in controllable_request_2.values())}" +
             f" / {len(R)}"))
        logging.info(
            ("No. accepted requests (1+2): " +
             f"{sum(v.x > 0.9 for v in controllable_request_any.values())}" +
             f" / {len(R)}"))
        logging.info((
            "No. new accepted requests (2-1): " +
            f"""{sum(v.x > 0.9 for r, v in controllable_request_2.items()
                if v.x > 0.9 and controllable_request[r].x < 0.9)}""" +
            f" / {len(R) - sum(v.x > 0.9 for v in controllable_request.values())}"
        ))

        logging.info(("Replaced hypervisors: " +
                      f"""{sum(1 for h in H if active_hypervisors[h].x > 0.9
            and active_hypervisors_2[h].x < 0.9)}""" +
                      f" / {n_diff_hypervisors}"))
        logging.info(
            "Active hypervisors (1): " +
            f"{[h for h, v in active_hypervisors.items() if v.x > 0.9]}")
        logging.info(
            "Active hypervisors (2): " +
            f"{[h for h, v in active_hypervisors_2.items() if v.x > 0.9]}")

        result = {
            'active hypervisors':
            [h for h, v in active_hypervisors.items() if v.x > 0.9],
            'hypervisor assignment': {
                s: (h1, h2)
                for ((h1, h2),
                     s), v in hypervisor_pair_controls_switch.items()
                if v.x > 0.9
            },
            'hypervisor2switch control paths': [],
            'hp acceptance ratio':
            model.ObjVal,
            'request status':
            {id_: v.x > 0.9
             for id_, v in controllable_request.items()},
            'flexibility status':
            {id_: v.x > 0.9
             for id_, v in controllable_request_2.items()}
        }
        logging.info(f"Finished solving the ILP.")
        return result