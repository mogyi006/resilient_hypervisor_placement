# Standard library imports.
import itertools

# Related third party imports.
import gurobipy as gp
from gurobipy import GRB
env = gp.Env()

# Local application/library specific imports.
import src.data.graph_utilities as gu
import src.models.objectives as objectives


def lcrhpp_minh(network_operator=None, **kwargs):
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
                h_count,
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
        # c_5a = model.addConstrs(gp.quicksum([hypervisor_pair_controls_switch[((h1,h2),s)] for h1,h2 in not_allowed_switch_H_pairs[s]]) == 0 for s in S)
        # c_5b = model.addConstrs(hypervisor_pair_controls_switch[((h1,h2),s)] == 0 for h1,h2 in not_allowed_switch_H_pairs[s] for s in S)
        # c_5c = model.addConstrs(hypervisor_controls_switch[(h1,s)] + hypervisor_controls_switch[(h2,s)] <= 1 for h1,h2 in not_allowed_switch_H_pairs[s] for s in S)

        # If a good hypervisor pair controls the switch then the controller is able to control it
        c_6 = model.addConstrs(controller_controls_switch[(c, s)] == gp.or_([
            hypervisor_pair_controls_switch[((h1, h2), s)]
            for h1, h2 in allowed_cs_H_pairs.get((c, s), [])
        ]) for c, s in CS_pairs)

        # The request can be accepted with the controller if it can control all of its switches
        c_7 = model.addConstrs(controller_controls_request[(c, r)] == gp.and_(
            [controller_controls_switch[(c, s)] for s in R[r].get_switches()])
                               for c, r in CR_pairs)

        # The request is acceptable if there is a controller that can control all of its switches
        c_8 = model.addConstrs(controllable_request[r] == gp.or_(
            [controller_controls_request[(c, r)] for c in C]) for r in R)

        # Some requests must be accepted
        if required_vSDN_requests is not None:
            c_9 = model.addConstrs(controllable_request[r] == 1 for r in R
                                   if r in required_vSDN_requests)

        # The number of active hypervisors cannot exceed the given hypervisor count
        c_10 = model.addConstr(gp.quicksum(active_hypervisors) <= h_count)

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
