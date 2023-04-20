# Standard library imports.
import logging

# Related third party imports.
import gurobipy as gp
from gurobipy import GRB

# Local application/library specific imports.

vSDN_metrics = {}
vSDN_metric = lambda f: vSDN_metrics.setdefault(f.__name__, f)


@vSDN_metric
def size(vSDN_request=None):
    return vSDN_request.get_size()


@vSDN_metric
def TTL(vSDN_request=None):
    return vSDN_request.get_TTL()


@vSDN_metric
def utilization(vSDN_request=None):
    return vSDN_request.get_size() * vSDN_request.get_TTL()


@vSDN_metric
def QoS(vSDN_request=None):
    return vSDN_request.get_size() * vSDN_request.get_QoS()


@vSDN_metric
def revenue(vSDN_request=None, one_timestep=False, **kwargs):
    if one_timestep:
        return vSDN_request.get_size() * vSDN_request.get_QoS()
    else:
        return (vSDN_request.get_size() * vSDN_request.get_TTL() *
                vSDN_request.get_QoS())
