# Standard library imports.
import pickle
import pprint
from pathlib import Path
import itertools

# Related third party imports.
import numpy as np

# Local application/library specific imports.
from src.models import network_operator
from src.models import vSDN_request
from src.logger import measure


def generate_setting_list(setting_dict: dict = None) -> list:
    if setting_dict is None:
        raise ValueError
    param_names = list(setting_dict.keys())
    return [
        dict(zip(param_names, x))
        for x in itertools.product(*setting_dict.values())
    ]


class NetworkSimulation:
    def __init__(self, network_name: str = None, **kwargs) -> None:
        self._time = 0

        self._network_name = network_name
        self._network_path = f"../data/processed/networks/{self._network_name}.gml"
        self._request_folder = f"../data/processed/requests/{self._network_name}/"
        self._result_folder = f"../data/results/{self._network_name}/"
        self._network_operator_folder = f"../data/processed/network_operators/{self._network_name}/"

        self.init_network_operator(**kwargs)

        self.request_generator = vSDN_request.vSDN_request_generator(
            self._network_name, self._request_folder, **kwargs)
        self.request_generator_ = vSDN_request.vSDN_request_generator(
            self._network_name, self._request_folder, **kwargs)

        self.logs = []
        return

    def get_network_operator_path(self, latency_factor, shortest_k, **kwargs):
        return Path(
            f"{self._network_operator_folder}{self._network_name}_L{str(int(latency_factor*10))}_k{shortest_k}.p"
        )

    def is_network_operator_file_available(self, **kwargs):
        network_operator_path = self.get_network_operator_path(**kwargs)
        return network_operator_path.is_file()

    def init_network_operator(self, **kwargs) -> None:
        network_operator_path = self.get_network_operator_path(**kwargs)
        if self.is_network_operator_file_available(**kwargs):
            self.network_operator = pickle.load(
                open(network_operator_path, "rb"))
        else:
            self.network_operator = network_operator.NetworkOperator(
                path=self._network_path)
        return

    def save_network_operator(self, **kwargs) -> None:
        network_operator_path = self.get_network_operator_path(**kwargs)
        if not self.is_network_operator_file_available(**kwargs):
            with open(network_operator_path, 'wb') as outp:
                pickle.dump(self.network_operator, outp,
                            pickle.HIGHEST_PROTOCOL)
        return

    def init_simulation(self, **kwargs) -> None:
        if not self.is_network_operator_file_available(**kwargs):
            self.network_operator.set_max_length(**kwargs)
            self.network_operator.set_shortest_k(**kwargs)
            self.network_operator.control_path_calculation(**kwargs)
            self.save_network_operator(**kwargs)
        return

    def run_static_simulation(self,
                              hp_repeat: int = 1,
                              possible_request_settings: dict = None,
                              **kwargs) -> None:
        self.delete_logs()
        request_setting_list = generate_setting_list(possible_request_settings)

        for _ in range(hp_repeat):
            self.hypervisor_placement(**kwargs)
            for request_setting in request_setting_list:
                self.run_static_request_simulation(**request_setting)
                _ = self.log_simulation()
        return

    def run_optimal_static_simulation(self,
                                      hp_repeat: int = 1,
                                      possible_request_settings: dict = None,
                                      **kwargs) -> None:
        self.delete_logs()
        request_setting_list = generate_setting_list(possible_request_settings)

        for _ in range(hp_repeat):
            for request_setting in request_setting_list:
                self.run_static_request_simulation(to_setup=False,
                                                   **request_setting)
                self.hypervisor_placement(
                    **{
                        'hp_type': 'ilp',
                        'hp_objective': 'acceptance ratio',
                        'vSDN_requests_ilp': self.vSDN_requests,
                        'h_count': self.get_minimal_hypervisor_count(),
                    })

                _, self.request_processing_time = self.setup_vSDN_requests(
                    **kwargs)
                _ = self.log_simulation()
        return

    def run_static_request_simulation(self,
                                      to_setup: bool = True,
                                      **kwargs) -> None:
        self.discard_vSDNs(all=True)
        self.generate_vSDN_requests(**kwargs)
        if to_setup:
            _, self.request_processing_time = self.setup_vSDN_requests(
                **kwargs)
        return

    def run_dynamic_simulation(self, timesteps, **kwargs):
        if self._time == 0:
            self.hypervisor_placement(**kwargs)

        for _ in range(timesteps):
            self.next_timestep(**kwargs)
            _ = self.log_simulation()

    def run_optimal_dynamic_simulation(self, timesteps, **kwargs):
        min_h_count = self.get_minimal_hypervisor_count()
        for _ in range(timesteps):
            self.next_timestep(to_setup=False, **kwargs)
            self.hypervisor_placement(
                **{
                    'hp_type': 'ilp',
                    'hp_objective': 'acceptance ratio',
                    'vSDN_requests_ilp': self.vSDN_requests,
                    'h_count': min_h_count,
                })
            self.setup_vSDN_requests()
            _ = self.log_simulation()

    def next_timestep(self,
                      to_setup: bool = True,
                      request_per_timestep: int = 10,
                      **kwargs):
        self._time += 1
        self.discard_vSDNs()
        self.vSDN_requests = self.request_generator.get_random_vSDN_requests(
            **dict(kwargs, total_count=request_per_timestep, time_=self._time))
        # ! Add vSDN preprocessing
        if to_setup:
            self.setup_vSDN_requests()

    def hypervisor_placement(self, **kwargs) -> None:
        if kwargs.get('hp_type', '') == 'ilp' and kwargs.get(
                'hp_objective', '') == 'acceptance ratio':
            vSDN_requests_ilp = self.get_vSDN_requests_ilp(**kwargs)
            self.vSDN_count_ilp = len(vSDN_requests_ilp)
            self.vSDN_max_size_ilp = max(
                [r.get_size() for r in vSDN_requests_ilp])
            self.network_operator.hypervisor_placement(
                **dict(kwargs,
                       vSDN_requests=vSDN_requests_ilp,
                       h_count=self.get_minimal_hypervisor_count()))
        else:
            self.network_operator.hypervisor_placement(**kwargs)
        # _, _ = self.network_operator.get_hypervisor_switch_latencies()
        return

    def get_minimal_hypervisor_count(self) -> int:
        self.hypervisor_placement(**{
            'hp_type': 'ilp',
            'hp_objective': 'hypervisor count',
        })
        return self.network_operator.get_active_hypervisor_count()

    def modify_hypervisor_placement(self, **kwargs) -> None:
        return

    def generate_vSDN_requests(self, request_size, **kwargs):
        self.vSDN_size = request_size
        (self.vSDN_requests, self.vSDN_coverage,
         self.vSDN_count) = self.request_generator.get_request_list(
             request_size, **dict(kwargs, time_=self._time))
        # print(self.vSDN_requests)
        return

    def get_vSDN_requests_ilp(self, vSDN_count_ilp: int = 100, **kwargs):
        if kwargs.get('vSDN_requests_ilp', None) is None:
            return self.request_generator_.get_random_vSDN_requests(
                **dict(kwargs, total_count=vSDN_count_ilp, time_=self._time))
        else:
            return kwargs.get('vSDN_requests_ilp', None)

    def check_new_vSDN_requests(self):

        return

    @measure
    def setup_vSDN_requests(self, **kwargs) -> None:
        self.accepted_vSDN_requests = self.network_operator.process_vSDN_requests(
            request_list=self.vSDN_requests)
        self.vSDN_accepted_count = sum(self.accepted_vSDN_requests)
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

    def log_simulation(self):
        log = {
            'network':
            self._network_name,
            'diameter':
            self.network_operator.get_graph_diameter(),
            'max_length':
            self.network_operator.get_max_length(),
            'latency_factor':
            self.network_operator.get_latency_factor(),
            'shortest_k':
            self.network_operator.get_shortest_k(),
            'hp_type':
            self.network_operator.get_hp_type(),  # ilp, heuristics
            'hp_objective':
            self.network_operator.get_hp_objective(),
            'ha_objective':
            self.network_operator.get_ha_objective(),
            'cp_objective':
            'random',  # random, cp length
            'hp_runtime':
            self.network_operator.get_hp_runtime(),
            'h_list':
            self.network_operator.get_active_hypervisors(),
            'h_count':
            self.network_operator.get_active_hypervisor_count(),
            'vSDN_generator_seed':
            self.request_generator.get_seed(),
            'vSDN_size':
            self.get_vSDN_size(),
            'vSDN_count':
            self.get_vSDN_request_count(),
            'vSDN_coverage':
            self.get_vSDN_request_coverage(),
            'vSDN_count_ilp':
            getattr(self, 'vSDN_count_ilp', 0),
            'vSDN_max_size_ilp':
            getattr(self, 'vSDN_max_size_ilp', 0),
            'acceptable_count':
            self.get_vSDN_accepted_count(),
            'acceptance_ratio':
            (self.get_vSDN_accepted_count() / self.get_vSDN_request_count()),
            'acceptance_ratio_ilp':
            self.network_operator.get_hp_acceptance_ratio(),
            'request_processing_time':
            float(f"{self.get_request_processing_time():.2f}"),
            'chs_avg':
            0,
            'chs_avg_p':
            self.network_operator.get_chs_cp_stat('avg_p'),
            'chs_max_p':
            self.network_operator.get_chs_cp_stat('max_p'),
            'chs_avg_b':
            self.network_operator.get_chs_cp_stat('avg_b'),
            'chs_max_b':
            self.network_operator.get_chs_cp_stat('max_b'),
        }
        # pprint.pprint(log)
        self.logs.append(log)
        return log

    def get_logs(self):
        return self.logs

    def delete_logs(self):
        self.logs = []

    def get_vSDN_accepted_count(self):
        return getattr(self, 'vSDN_accepted_count', 0)

    def get_vSDN_requests(self):
        return getattr(self, 'vSDN_requests', [])

    def get_vSDN_request_count(self):
        return len(self.get_vSDN_requests())

    def get_vSDN_size(self):
        return getattr(
            self, 'vSDN_size',
            np.mean([r.get_size() for r in self.get_vSDN_requests()]))

    def get_vSDN_request_coverage(self):
        return getattr(self, 'vSDN_coverage', 0)

    def get_request_processing_time(self):
        return getattr(self, 'request_processing_time', 0)
