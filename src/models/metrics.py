# Standard library imports.

# Related third party imports.

# Local application/library specific imports.
import src.models.vSDN_request as vSDN_request

metrics = {}
metric = lambda f: metrics.setdefault(f.__name__, f)


@metric
def get_revenue(vSDN_request: vSDN_request.vSDN_request = None):
    return vSDN_request.get_size() * vSDN_request.get_TTL(
    ) * vSDN_request.get_QoS()


@metric
def get_utilization(vSDN_request: vSDN_request.vSDN_request = None):
    return vSDN_request.get_size() * vSDN_request.get_TTL()