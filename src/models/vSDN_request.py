# Standard library imports.
import itertools
import random
#import numpy as np

# Related third party imports.

# Local application/library specific imports.


def generate_vSDN_request(request_file_path, TTL_range, time_):
    with open(request_file_path, mode='r') as f:
        subgraphs = f.readlines()
        switches = [int(s) for s in random.choice(subgraphs).split()]
        controller = random.choice(switches)
        TTL = random.randint(1, TTL_range)
        return vSDN_request(controller, switches, TTL, time_)


# def generate_vSDN_requests(request_file_path,
#                            number_of_requests,
#                            TTL_range,
#                            time_=0):
#     return [
#         generate_vSDN_request(request_file_path, TTL_range, time_)
#         for _ in range(number_of_requests)
#     ]


def generate_vSDN_requests(request_file_path,
                           coverage: float = None,
                           count: int = None,
                           TTL_range: int = 10,
                           time_: int = 0,
                           **kwargs):
    with open(request_file_path, mode='r') as f:
        subgraphs = f.readlines()
        number_of_subgraphs = len(subgraphs)
        subgraph_switches = [[int(s) for s in subgraph.split()]
                             for subgraph in subgraphs]

        if coverage and coverage <= 1 and coverage > 0:
            number_of_requests = int(coverage * number_of_subgraphs)
        elif count and count > 1:
            number_of_requests = min(number_of_subgraphs, count)
            coverage = number_of_requests / number_of_subgraphs
        else:
            return None
        return ([
            vSDN_request(controller=random.choice(switches),
                         switches=switches,
                         TTL=random.randint(1, TTL_range),
                         time_=time_) for switches in random.sample(
                             subgraph_switches, number_of_requests)
        ], coverage, number_of_requests)


class vSDN_request:
    id_iter = itertools.count()

    def __init__(self, controller, switches, TTL, time_):
        self._id = next(vSDN_request.id_iter)
        self._controller = controller
        self._switches = switches
        self._TTL = TTL
        self._start_time = time_
        self._end_time = time_ + TTL

    def __repr__(self):
        return "%3s %3s %10s %3s" % (self._id, self._controller,
                                     self._switches, self._TTL)
        # return f"{self._id}\t{self._controller}\t{self._switches}\t{self._TTL}"

    def get_end_time(self):
        return self._end_time

    def get_id(self):
        return self._id

    def get_switches(self):
        return self._switches
