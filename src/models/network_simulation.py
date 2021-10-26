# Standard library imports.
import pprint

# Related third party imports.

# Local application/library specific imports.
from src.models.network_operator import NetworkOperator
from src.models import vSDN_request
from src.logger import measure


class NetworkSimulation:
    def __init__(self, network_name: str = None, **kwargs) -> None:
        self._time = 0

        self._network_name = network_name
        self._network_path = f"../data/processed/networks/{self._network_name}.gml"
        self._request_folder = f"../data/processed/requests/{self._network_name}/"
        self._result_folder = f"../data/results/{self._network_name}/"

        self.network_operator = NetworkOperator(path=self._network_path)
        self.request_generator = vSDN_request.vSDN_request_generator(
            self._network_name, self._request_folder, **kwargs)

        return

    def init_simulation(self, **kwargs) -> None:
        self.network_operator.set_max_length(**kwargs)
        self.network_operator.set_shortest_k(**kwargs)
        self.network_operator.control_path_calculation(**kwargs)
        return

    def request_simulation(self, **kwargs) -> None:
        self.discard_vSDNs(all=True)
        self.generate_vSDN_requests(**kwargs)
        _, self.request_processing_time = self.setup_vSDN_requests(**kwargs)
        return

    def hypervisor_placement(self, **kwargs) -> None:
        if kwargs.get('hp_type', '') == 'ilp' and kwargs.get(
                'hp_objective', '') == 'acceptance ratio':
            random_vSDN_requests = self.request_generator.get_random_vSDN_requests(
                **kwargs)
            self.vSDN_count_ilp = len(random_vSDN_requests)
            self.vSDN_max_size_ilp = max(
                [r.get_size() for r in random_vSDN_requests])
            self.network_operator.hypervisor_placement(
                **dict(kwargs, vSDN_requests=random_vSDN_requests))
        else:
            self.network_operator.hypervisor_placement(**kwargs)
        # _, _ = self.network_operator.get_hypervisor_switch_latencies()
        return

    def modify_hypervisor_placement(self, **kwargs) -> None:
        return

    def generate_vSDN_requests(self, request_size, **kwargs):
        self.vSDN_size = request_size
        (self.vSDN_requests, self.vSDN_coverage,
         self.vSDN_count) = self.request_generator.get_request_list(
             request_size, **kwargs)
        return

    def check_new_vSDN_requests(self):
        return

    def get_vSDN_accepted_count(self):
        return getattr(self, 'vSDN_accepted_count', 1)

    @measure
    def setup_vSDN_requests(self, **kwargs) -> None:
        self.vSDN_accepted_count = self.network_operator.process_vSDN_requests(
            self.vSDN_requests, bool(self.get_vSDN_accepted_count()))
        _ = self.network_operator.get_control_path_stats()
        # print(latency_factor, max_length, request_size,
        #       len(self.network_operator.active_hypervisors), acceptance_ratio,
        #       *x)
        return

    def discard_vSDNs(self, all: bool = False) -> None:
        if all:
            self.network_operator.discard_all_vSDNs()
        else:
            self.network_operator.discard_old_vSDNs(self._time)
        return

    def next_timestep(self, **kwargs):
        self._time += 1
        self.discard_old_vSDNs()
        self.generate_new_vSDN_requests(**kwargs)
        self.check_new_vSDN_requests()
        self.modify_hypervisor_placement()
        self.setup_new_vSDN_requests(**kwargs)

    def run_simulation(self, timesteps, **kwargs):
        if self._time == 0:
            self.initital_hypervisor_placement(**kwargs)

        for _ in range(timesteps):
            self.next_timestep(**kwargs)

    def log_simulation(self):
        log = {
            'network': self._network_name,
            'diameter': self.network_operator.get_graph_diameter(),
            'max_length': self.network_operator.get_max_length(),
            'latency_factor': self.network_operator.get_latency_factor(),
            'shortest_k': self.network_operator.get_shortest_k(),
            'hp_type': self.network_operator.get_hp_type(),  # ilp, heuristics
            'hp_objective': self.network_operator.get_hp_objective(),
            'ha_objective': self.network_operator.get_ha_objective(),
            'cp_objective': 'random',  # random, cp length
            'hp_runtime': self.network_operator.get_hp_runtime(),
            'h_list': self.network_operator.get_active_hypervisors(),
            'h_count': self.network_operator.get_active_hypervisor_count(),
            'vSDN_generator_seed': self.request_generator.get_seed(),
            'vSDN_size': self.vSDN_size,
            'vSDN_count': self.vSDN_count,
            'vSDN_coverage': self.vSDN_coverage,
            'vSDN_count_ilp': getattr(self, 'vSDN_count_ilp', 0),
            'vSDN_max_size_ilp': getattr(self, 'vSDN_max_size_ilp', 0),
            'acceptable_count': self.vSDN_accepted_count,
            'acceptance_ratio': self.vSDN_accepted_count / self.vSDN_count,
            'acceptance_ratio_ilp':
            self.network_operator.get_hp_acceptance_ratio(),
            'request_processing_time':
            float(f"{self.request_processing_time:.2f}"),
            'chs_avg': 0,
            'chs_avg_p': self.network_operator.get_chs_cp_stat('avg_p'),
            'chs_max_p': self.network_operator.get_chs_cp_stat('max_p'),
            'chs_avg_b': self.network_operator.get_chs_cp_stat('avg_b'),
            'chs_max_b': self.network_operator.get_chs_cp_stat('max_b'),
        }
        # pprint.pprint(log)
        return log
