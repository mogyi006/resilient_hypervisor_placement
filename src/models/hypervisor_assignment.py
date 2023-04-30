# Standard library imports.
import itertools
import collections
import concurrent.futures
from copy import deepcopy
import random
import logging

# Related third party imports.
import numpy as np

# Local application/library specific imports.
import src.data.graph_utilities as gu
import src.models.ilp as ilp
from src.logger import measure

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
