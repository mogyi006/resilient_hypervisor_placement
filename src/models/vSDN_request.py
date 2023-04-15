# Standard library imports.
import itertools
import random
import glob
import re
import linecache
import typing
from typing import List, Tuple

# Related third party imports.
import numpy as np

# Local application/library specific imports.
import src.models.metrics as metrics

# def generate_vSDN_request(request_file_path, TTL_range, time_):
#     with open(request_file_path, mode='r') as f:
#         subgraphs = f.readlines()
#         switches = [int(s) for s in random.choice(subgraphs).split()]
#         controller = random.choice(switches)
#         TTL = random.randint(1, TTL_range)
#         return vSDN_request(controller, switches, TTL, time_)

# def generate_vSDN_requests(request_file_path,
#                            number_of_requests,
#                            TTL_range,
#                            time_=0):
#     return [
#         generate_vSDN_request(request_file_path, TTL_range, time_)
#         for _ in range(number_of_requests)
#     ]

# def generate_vSDN_requests(request_file_path,
#                            coverage: float = None,
#                            count: int = None,
#                            TTL_range: int = 10,
#                            time_: int = 0,
#                            **kwargs):
#     with open(request_file_path, mode='r') as f:
#         subgraphs = f.readlines()
#         number_of_subgraphs = len(subgraphs)
#         subgraph_switches = [[int(s) for s in subgraph.split()]
#                              for subgraph in subgraphs]

#         if coverage and coverage <= 1 and coverage > 0:
#             number_of_requests = int(coverage * number_of_subgraphs)
#         elif count and count > 1:
#             number_of_requests = min(number_of_subgraphs, count)
#             coverage = number_of_requests / number_of_subgraphs
#         else:
#             return None
#         return ([
#             vSDN_request(controller=random.choice(switches),
#                          switches=switches,
#                          TTL=random.randint(1, TTL_range),
#                          time_=time_) for switches in random.sample(
#                              subgraph_switches, number_of_requests)
#         ], coverage, number_of_requests)

# def generate_random_vSDN_requests(request_file_path_list,
#                                   total_count: int = 100,
#                                   **kwargs):
#     request_list = []
#     request_file_count = len(request_file_path_list)
#     remaining_count = total_count
#     for i, request_file_path in enumerate(request_file_path_list):
#         if remaining_count <= 0:
#             continue
#         if i == request_file_count - 1:
#             sub_count = remaining_count
#         else:
#             sub_counts = np.random.multinomial(remaining_count,
#                                                [1 / (request_file_count - i)] *
#                                                (request_file_count - i))
#             sub_count = min(remaining_count, sub_counts[0])
#         sub_request_list, _, sub_count = generate_vSDN_requests(
#             request_file_path, count=sub_count, **kwargs)
#         request_list.extend(sub_request_list)
#         remaining_count -= sub_count
#     return request_list


class vSDN_request(object):
    id_iter = itertools.count()

    def __init__(self, controller, switches, TTL, QoS, time_, **kwargs):
        self.id = next(vSDN_request.id_iter)
        self.controller = controller
        self.switches = switches
        self.TTL = TTL
        self.start_time = time_
        self.end_time = time_ + TTL
        self.active_time = 0
        self.QoS = QoS
        self.active = False
        self.accepted = False

    def __repr__(self) -> str:
        return "%3s %3s %10s %3s" % (self.id, self.controller, self.switches,
                                     self.TTL)
        # return f"{self.id}\t{self.controller}\t{self.switches}\t{self.TTL}"

    def __getattribute__(self, name: str):
        return object.__getattribute__(self, name)

    def get_id(self):
        return self.id

    def get_controller(self):
        return self.controller

    def set_controller(self, c):
        self.controller = c

    def get_switches(self):
        return self.switches

    def get_size(self) -> int:
        return len(self.switches)

    def get_start_time(self):
        return self.start_time

    def set_end_time(self, t):
        self.end_time = t
        self.active_time = t - self.start_time

    def get_end_time(self):
        return self.end_time

    def get_active_time(self):
        return self.active_time

    def get_TTL(self):
        return self.TTL

    def get_QoS(self):
        return self.QoS

    def is_active(self):
        return self.active

    def is_accepted(self):
        return self.accepted

    def set_active(self):
        self.active = True
        self.accepted = True

    def set_inactive(self):
        self.active = False

    def get_metric(self, metric: str = None):
        return metrics.metrics[metric](self)


class vSDN_request_generator:
    def __init__(self,
                 network_name,
                 request_folder,
                 seed: int = 123,
                 **kwargs) -> None:
        self._network_name = network_name
        self._request_folder = request_folder
        self.build_request_file_dict()
        self.random_generator = np.random.default_rng(seed)
        self.seed = seed

    def get_seed(self):
        return self.seed

    def TTL_generator(self, min_TTL: int = 1, max_TTL: int = 10, **kwargs):
        return self.random_generator.integers(min_TTL, max_TTL, 1)[0]

    def QoS_generator(self, min_QoS: int = 1, max_QoS: int = 3, **kwargs):
        return self.random_generator.integers(min_QoS, max_QoS, 1)[0]

    def get_request_file_path(self, request_size):
        return f"{self._request_folder}{self._network_name}.{str(request_size)}.subgraphs"

    def build_request_file_dict(self) -> None:
        self.request_file_dict = {}
        for request_file_path in sorted(
                glob.glob(self.get_request_file_path('*'))):
            m = re.search('(\d+)\.subgraphs', request_file_path)
            request_size = int(m.group(1))
            self.request_file_dict[request_size] = {
                'file_path': request_file_path,
                'file_size': sum(1 for _ in open(request_file_path, 'r'))
            }
        # print(self.request_file_dict)
        return

    def get_request_from_file(self, request_file_path, line_index,
                              **kwargs) -> vSDN_request:
        switches = [
            int(s)
            for s in linecache.getline(request_file_path, line_index).split()
        ]
        # print(line_index, switches)
        controller = None
        # self.random_generator.choice(switches)  # ! controller selection
        TTL = self.TTL_generator(**kwargs)
        QoS = self.QoS_generator(**kwargs)
        return vSDN_request(controller=controller,
                            switches=switches,
                            TTL=TTL,
                            QoS=QoS,
                            **kwargs)

    def get_request(self, request_size, **kwargs) -> vSDN_request:
        request_file_path = self.request_file_dict[request_size]['file_path']
        line_index = self.random_generator.integers(
            1, self.request_file_dict[request_size]['file_size'], 1)[0]
        return self.get_request_from_file(request_file_path, line_index,
                                          **kwargs)

    def get_request_list(self,
                         request_size: int = 2,
                         coverage: float = None,
                         count: int = None,
                         **kwargs) -> Tuple[List[vSDN_request], float, int]:
        request_file_path = self.request_file_dict[request_size]['file_path']
        number_of_subgraphs = self.request_file_dict[request_size]['file_size']

        if coverage is not None and coverage <= 1 and coverage > 0:
            number_of_requests = int(coverage * number_of_subgraphs)
        elif count is not None and count >= 1:
            number_of_requests = min(number_of_subgraphs, int(count))
            coverage = number_of_requests / number_of_subgraphs
        else:
            return None

        line_indexes = self.random_generator.choice(np.arange(
            1, number_of_subgraphs + 1),
                                                    number_of_requests,
                                                    replace=False)

        return [
            self.get_request_from_file(request_file_path, line_index, **kwargs)
            for line_index in line_indexes
        ], coverage, number_of_requests

    def get_random_vSDN_requests(self,
                                 max_request_size: typing.Optional[int] = None,
                                 total_count: int = 100,
                                 **kwargs) -> List[vSDN_request]:
        request_sizes = sorted([
            size for size in self.request_file_dict.keys()
            if size <= max_request_size
        ])
        request_file_sizes = [
            self.request_file_dict[size]['file_size'] for size in request_sizes
        ]
        cum_request_file_sizes = [
            sum(request_file_sizes[:i]) for i in range(len(request_file_sizes))
        ]
        request_indexes = self.random_generator.integers(
            1, sum(request_file_sizes), total_count)

        request_list = []
        for index in request_indexes:
            diff = index - np.array(cum_request_file_sizes)
            request_size_index = np.where(diff > 0, diff, np.inf).argmin()
            line_index = diff[request_size_index]
            request_list.append(
                self.get_request_from_file(
                    self.request_file_dict[request_sizes[request_size_index]]
                    ['file_path'], line_index, **kwargs))
        return request_list
