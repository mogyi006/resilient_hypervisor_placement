# Standard library imports.
import logging

# Related third party imports.
import gurobipy as gp
from gurobipy import GRB

# Local application/library specific imports.

ilp_objectives = {}
objective = lambda f: ilp_objectives.setdefault(f.__name__, f)


def add_objectives(model: gp.Model = None,
                   hp_objectives: tuple = None,
                   **kwargs):
    # Add the objectives to the model.
    for i, obj in enumerate(hp_objectives):
        model.setObjectiveN(ilp_objectives[obj](**kwargs),
                            index=i,
                            priority=len(hp_objectives) - i)
    model.ModelSense = GRB.MAXIMIZE


@objective
def hypervisor_count(active_hypervisors: gp.tupledict = None, **kwargs):
    # Minimize the number of active hypervisors.
    if active_hypervisors is None:
        logging.warning("No variable found...")
        logging.warning(f"active_hypervisors: {active_hypervisors}")
        return 0
    else:
        return -active_hypervisors.sum()


@objective
def acceptance_ratio(controllable_request: gp.tupledict = None, **kwargs):
    # Maximize the acceptance ratio.
    if controllable_request is None:
        logging.warning("No variable found...")
        logging.warning(f"controllable_request: {controllable_request}")
        return 0
    else:
        return controllable_request.sum()


@objective
def switch_load_time(switch_load_time_total: gp.Var = None, **kwargs):
    # Maximize the utilization time of switches.
    if switch_load_time_total is None:
        logging.warning("No variable found...")
        return 0
    return switch_load_time_total


@objective
def switch_load(switch_load_total: gp.Var = None, **kwargs):
    # Maximize the number of utilized switches.
    if switch_load_total is None:
        logging.warning("No variable found...")
        return 0
    return switch_load_total


@objective
def QoS(vSDN_QoS_total: gp.Var = None, **kwargs):
    # Maximize the total QoS of requests.
    if vSDN_QoS_total is None:
        logging.warning("No variable found...")
        return 0
    return vSDN_QoS_total


@objective
def revenue(vSDN_revenue_total: gp.Var = None, **kwargs):
    # Maximize the total revenue of requests.
    if vSDN_revenue_total is None:
        logging.warning("No variable found...")
        return 0
    return vSDN_revenue_total


@objective
def hypervisor_load(hypervisor_load_max: gp.Var = None, **kwargs):
    # Minimize the maximum load of a hypervisor.
    if hypervisor_load_max is None:
        logging.warning("No variable found...")
        logging.warning(f"hypervisor_load_max: {hypervisor_load_max}")
        return 0
    return -hypervisor_load_max


@objective
def controller_load_request(controller_load_request_max: gp.Var = None,
                            **kwargs):
    # Minimize the maximum load of a controller.
    if controller_load_request_max is None:
        logging.warning("No variable found...")
        logging.warning(f"controller_load_request_max: "
                        f"{controller_load_request_max}")
        return 0
    else:
        return -controller_load_request_max


@objective
def controller_load_switch(controller_load_switch_max: gp.Var = None,
                           **kwargs):
    # Minimize the maximum load of a controller.
    if controller_load_switch_max is None:
        logging.warning("No variable found...")
        logging.warning(f"controller_load_switch_max: "
                        f"{controller_load_switch_max}")
        return 0
    else:
        return -controller_load_switch_max


@objective
def maximize_joint_sum(model: gp.Model = None,
                       Vars: gp.tupledict = None,
                       Vars_2: gp.tupledict = None,
                       weight: float = 0.5,
                       **kwargs):
    model.setObjective(
        gp.quicksum(Vars[i] + weight * (1 - Vars[i]) * Vars_2[i]
                    for i in Vars.keys()), gp.GRB.MAXIMIZE)
