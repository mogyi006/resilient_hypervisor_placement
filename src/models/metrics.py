# Standard library imports.

# Related third party imports.

# Local application/library specific imports.

metrics = {}
metric = lambda f: metrics.setdefault(f.__name__, f)


@metric
def size(vSDN_request=None):
    return vSDN_request.get_size()


@metric
def utilization(vSDN_request=None):
    return vSDN_request.get_size() * vSDN_request.get_TTL()


@metric
def revenue(vSDN_request=None):
    return vSDN_request.get_size() * vSDN_request.get_TTL(
    ) * vSDN_request.get_QoS()
