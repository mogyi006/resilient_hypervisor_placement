# Standard library imports.

# Related third party imports.
import gurobipy as gp

# Local application/library specific imports.
import src.models.metrics as metrics

objectives = {}
objective = lambda f: objectives.setdefault(f.__name__, f)


@objective
def minimize_sum(model: gp.Model = None, Vars: gp.tupledict = None, **kwargs):
    model.setObjective(Vars.sum(), gp.GRB.MINIMIZE)


@objective
def maximize_sum(model: gp.Model = None, Vars: gp.tupledict = None, **kwargs):
    model.setObjective(Vars.sum(), gp.GRB.MAXIMIZE)


@objective
def maximize_average(model: gp.Model = None,
                     Vars: gp.tupledict = None,
                     **kwargs):
    model.setObjective(Vars.sum() / len(Vars), gp.GRB.MAXIMIZE)


@objective
def maximize_utilized_switches(model: gp.Model = None,
                               Vars: gp.tupledict = None,
                               vSDN_requests: dict = None,
                               **kwargs):
    model.setObjective(
        gp.quicksum(Vars[i] * vSDN.get_size()
                    for i, vSDN in vSDN_requests.items()), gp.GRB.MAXIMIZE)


@objective
def maximize_total_QoS(model: gp.Model = None,
                       Vars: gp.tupledict = None,
                       vSDN_requests: dict = None,
                       **kwargs):
    model.setObjective(
        gp.quicksum(Vars[i] * vSDN.get_QoS()
                    for i, vSDN in vSDN_requests.items()), gp.GRB.MAXIMIZE)


@objective
def maximize_total_revenue(model: gp.Model = None,
                           Vars: gp.tupledict = None,
                           vSDN_requests: dict = None,
                           **kwargs):
    model.setObjective(
        gp.quicksum(Vars[i] * metrics.metrics['revenue'](vSDN_request)
                    for i, vSDN_request in vSDN_requests.items()),
        gp.GRB.MAXIMIZE)
