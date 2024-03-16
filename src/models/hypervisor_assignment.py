# Standard library imports.
import itertools
import collections
import logging

# Related third party imports.
import numpy as np

# Local application/library specific imports.
import src.models.ilp as ilp


methods = {}
method = lambda f: methods.setdefault(f.__name__, f)


@method
def max_control_options(S, H_used, Qhh):
    Q_counts = {}
    for h1, h2 in itertools.product(H_used, H_used):
        Q_counts[(h1, h2)] = collections.Counter(
            [s for (c, s) in Qhh.get((h1, h2), [])])
    logging.debug("Q_counts: %s", Q_counts)

    assignment = {s: max(Q_counts, key=lambda x: Q_counts[x][s]) for s in S}
    logging.debug("Hypervisor assignment: %s", assignment)
    return assignment

@method
def ilp_assignment(network_operator, hypervisor_scores, **kwargs):
    """ILP assignment of switches to hypervisors."""
    logging.info("ILP assignment")
    n_hypervisors = int(kwargs.get('n_hypervisors', 2) + 6)
    logging.debug("n_hypervisors: %s", n_hypervisors)
    network_operator.possible_hypervisors = np.argsort(hypervisor_scores)[-n_hypervisors:]
    logging.debug("Possible hypervisors: %s", network_operator.possible_hypervisors)
    result = ilp.lcrhpp(
        network_operator=network_operator,
        # hp_objectives = ('acceptance_ratio',),
        **kwargs
    )
    network_operator.possible_hypervisors = list(network_operator.graph.nodes)
    return result
