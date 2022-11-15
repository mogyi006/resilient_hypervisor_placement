# Standard library imports.
import datetime
import pickle
import pprint
from pathlib import Path
import itertools
from typing import List

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
        self.simulation_id = 0

        self._network_name = network_name
        self._network_path = f"../data/processed/networks/{self._network_name}.gml"
        self._request_folder = f"../data/processed/requests/{self._network_name}/"
        self._result_folder = f"../results/{self._network_name}/"
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
            f"{self._network_operator_folder}{self._network_name}_L{str(int(latency_factor*100))}_k{shortest_k}.p"
        )

    def is_network_operator_file_available(self, **kwargs) -> bool:
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
            self.save2pickle(network_operator_path, self.network_operator)
        return

    def init_simulation(self, **kwargs) -> None:
        if not self.is_network_operator_file_available(**kwargs):
            self.network_operator.set_max_length(**kwargs)
            self.network_operator.set_shortest_k(**kwargs)
            self.network_operator.control_path_calculation(**kwargs)
            self.save_network_operator(**kwargs)
        return

    def run_static_simulation(self,
                              possible_request_settings: dict = None,
                              **kwargs) -> None:
        self.discard_vSDNs(all=True)
        request_setting_list = generate_setting_list(possible_request_settings)

        self.hypervisor_placement(**kwargs)
        for request_setting in request_setting_list:
            self.run_static_request_simulation(**request_setting)
            _ = self.log_simulation()

        return

    def run_optimal_static_simulation(self,
                                      possible_request_settings: dict = None,
                                      **kwargs) -> None:
        self.discard_vSDNs(all=True)
        request_setting_list = generate_setting_list(possible_request_settings)

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

    def run_multiple_static_simulation(self,
                                       sim_repeat: int = 10,
                                       static_type: str = 'basic',
                                       **kwargs) -> None:
        self.delete_logs()
        self.simulation_type = 'static'
        self.sim_static_type = static_type
        self.min_h_count = self.get_minimal_hypervisor_count(recalculate=True)

        for sim_id in range(sim_repeat):
            self.simulation_id = sim_id
            if static_type == 'opt':
                self.run_optimal_static_simulation(**kwargs)
            else:
                self.run_static_simulation(**kwargs)
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

    def run_basic_dynamic_simulation(self,
                                     timesteps: int = 100,
                                     **kwargs) -> None:
        """
        t=0 Hypervisor placement.
        t>0 Requests are arriving, reject new if not acceptable.
            No Reconfiguration!
        """
        self._time = 0
        self.discard_vSDNs(all=True)
        self.simulation_timesteps = timesteps

        self.hypervisor_placement(**kwargs)

        for _ in range(self.simulation_timesteps):
            self.next_timestep(**kwargs)
            _ = self.log_simulation()
        return

    def run_conservative_dynamic_simulation(self,
                                            timesteps: int = 100,
                                            **kwargs) -> None:
        """
        t=0 -
        t>0 Requests are arriving
            Reconfiguration if not all new requests are acceptable.
            Deployed vSDNs operate until TTL.
        """
        self._time = 0
        self.discard_vSDNs(all=True)
        self.simulation_timesteps = timesteps

        for _ in range(self.simulation_timesteps):
            self.next_timestep(to_setup=False, **kwargs)

            all_acceptable = (self._time > 1) and (np.sum(
                self.preprocess_vSDN_requests()) == self.
                                                   get_vSDN_request_count())
            current_placement = set(
                self.network_operator.get_active_hypervisors())

            if not all_acceptable:
                self.hypervisor_placement(
                    **{
                        'hp_type':
                        'ilp',
                        'hp_objective':
                        'acceptance ratio',
                        'vSDN_requests_ilp':
                        self.vSDN_requests +
                        list(self.network_operator.vSDNs.values()),
                        'required_vSDN_requests':
                        list(self.network_operator.vSDNs.keys()),
                        'h_count':
                        self.get_minimal_hypervisor_count(),
                    })

            new_placement = set(self.network_operator.get_active_hypervisors())
            self.hp_changed = len(new_placement - current_placement)
            # print(f"Current: {current_placement}\nNew: {new_placement}")
            self.setup_vSDN_requests()
            _ = self.log_simulation()

        self.save_vSDN_history()
        return

    def run_liberal_dynamic_simulation(self,
                                       timesteps: int = 100,
                                       **kwargs) -> None:
        """
        t=0 -
        t>0 Requests are arriving
            Reconfiguration to maximize the number of active vSDNs.
            Deployed vSDNs may be removed if necessary.
        """
        self._time = 0
        self.discard_vSDNs(all=True)
        self.simulation_timesteps = timesteps

        for _ in range(self.simulation_timesteps):
            self.next_timestep(to_setup=False, **kwargs)
            self.vSDN_requests += list(self.network_operator.vSDNs.values())

            all_acceptable = (self._time > 1) and (np.sum(
                self.preprocess_vSDN_requests()) == self.
                                                   get_vSDN_request_count())
            current_placement = set(
                self.network_operator.get_active_hypervisors())

            if not all_acceptable:
                self.hypervisor_placement(
                    **{
                        'hp_type': 'ilp',
                        'hp_objective': 'acceptance ratio',
                        'vSDN_requests_ilp': self.vSDN_requests,
                        'h_count': self.get_minimal_hypervisor_count(),
                    })

            new_placement = set(self.network_operator.get_active_hypervisors())
            self.hp_changed = len(new_placement - current_placement)
            # print(f"Current: {current_placement}\nNew: {new_placement}")
            self.setup_vSDN_requests(time=self._time)
            _ = self.log_simulation()

        self.save_vSDN_history()
        return

    def run_multiple_dynamic_simulations(self,
                                         sim_repeat: int = 10,
                                         dynamic_type: str = 'basic',
                                         **kwargs) -> None:
        self.delete_logs()
        self.simulation_type = 'dynamic'
        self.sim_dynamic_type = dynamic_type
        self.min_h_count = self.get_minimal_hypervisor_count(recalculate=True)

        for sim_id in range(sim_repeat):
            self.simulation_id = sim_id
            if dynamic_type == 'basic':
                self.run_basic_dynamic_simulation(**kwargs)
            elif dynamic_type == 'conservative':
                self.run_conservative_dynamic_simulation(**kwargs)
            elif dynamic_type == 'liberal':
                self.run_liberal_dynamic_simulation(**kwargs)
            else:
                pass
        return

    def next_timestep(self,
                      to_setup: bool = True,
                      request_per_timestep: int = 10,
                      **kwargs) -> None:
        self._time += 1
        self.discard_vSDNs()

        switch_hpairs = self.network_operator.get_allowed_hypervisor_pairs_by_switch(
        )
        self.switch_hpair_count = [
            len(switch_hpairs[s]) for s in self.network_operator.nodes
        ]
        self.TTL_max = kwargs.get('TTL_range', 0)
        self.max_vSDN_size = kwargs.get('max_request_size', 0)
        self.vSDN_requests = self.request_generator.get_random_vSDN_requests(
            **dict(kwargs, total_count=request_per_timestep, time_=self._time))

        # ! Add vSDN preprocessing
        if to_setup:
            self.setup_vSDN_requests()

    def hypervisor_placement(self, **kwargs) -> None:
        if kwargs.get('hp_type', '') == 'ilp' and kwargs.get(
                'hp_objective', '') == 'acceptance ratio':

            # self.vSDN_count_ilp = len(vSDN_requests_ilp)
            # self.vSDN_max_size_ilp = max(
            #     [r.get_size() for r in vSDN_requests_ilp])
            self.network_operator.hypervisor_placement(
                **dict(kwargs,
                       vSDN_requests=self.get_vSDN_requests_ilp(**kwargs),
                       h_count=kwargs.get(
                           'h_count', self.get_minimal_hypervisor_count())))
        else:
            self.network_operator.hypervisor_placement(**kwargs)
        # _, _ = self.network_operator.get_hypervisor_switch_latencies()
        return

    def get_minimal_hypervisor_count(self, recalculate: bool = False) -> int:
        if recalculate:
            return self.network_operator.get_minimal_hypervisor_count()
        elif hasattr(self, 'min_h_count'):
            return getattr(self, 'min_h_count')
        else:
            return self.network_operator.get_minimal_hypervisor_count()

    def modify_hypervisor_placement(self, **kwargs) -> None:
        return

    def generate_vSDN_requests(self, request_size: int, **kwargs) -> None:
        self.vSDN_size = request_size
        (self.vSDN_requests, self.vSDN_coverage,
         self.vSDN_count) = self.request_generator.get_request_list(
             request_size, **dict(kwargs, time_=self._time))
        # print(self.vSDN_requests)
        return

    def get_vSDN_requests_ilp(self,
                              vSDN_count_ilp: int = 100,
                              vSDN_size_ilp: int = None,
                              **kwargs) -> List[vSDN_request.vSDN_request]:
        """Returns vSDN requests for the ILP.
        Generates new requests if a request list is not given."""
        if kwargs.get('vSDN_requests_ilp', None) is None:
            self.vSDN_count_ilp = vSDN_count_ilp
            self.vSDN_max_size_ilp = vSDN_size_ilp
            return self.request_generator_.get_random_vSDN_requests(
                max_request_size=vSDN_size_ilp,
                total_count=vSDN_count_ilp,
                time_=self._time)
        else:
            return kwargs.get('vSDN_requests_ilp', None)

    def preprocess_vSDN_requests(self):
        return self.network_operator.preprocess_vSDN_requests(
            request_list=self.vSDN_requests)

    @measure
    def setup_vSDN_requests(self, **kwargs) -> None:
        self.accepted_vSDN_requests = self.network_operator.process_vSDN_requests(
            request_list=self.vSDN_requests, **kwargs)
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
            'simulation_id':
            self.simulation_id,
            'dynamic_simulation_name':
            self.get_dynamic_simulation_name(),
            'static_simulation_name':
            self.get_static_simulation_name(),
            'simulation_type':
            self.get_simulation_type(),
            'sim_static_type':
            self.get_sim_static_type(),
            'sim_dynamic_type':
            self.get_sim_dynamic_type(),
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
            'hp_changed':
            self.get_hp_changed(),
            'switch_hpair_count':
            self.get_switch_hpair_count(),
            'mean_switch_hpair_count':
            np.mean(self.get_switch_hpair_count()),
            'vSDN_generator_seed':
            self.request_generator.get_seed(),
            'vSDN_size':
            self.get_vSDN_size(),
            'max_vSDN_size':
            self.get_max_vSDN_size(),
            'vSDN_count':
            self.get_vSDN_request_count(),
            'vSDN_coverage':
            self.get_vSDN_request_coverage(),
            'TTL_distribution':
            'uniform',
            'TTL_max':
            self.get_TTL_max(),
            'vSDN_count_ilp':
            self.get_vSDN_count_ilp(),
            'vSDN_max_size_ilp':
            self.get_vSDN_max_size_ilp(),
            'active_vSDN_count':
            self.network_operator.get_active_vSDN_count(),
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
            'timestep':
            self._time,
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

    def get_switch_hpair_count(self):
        return getattr(self, 'switch_hpair_count', 0)

    def get_hp_changed(self):
        return getattr(self, 'hp_changed', False)

    def get_simulation_timesteps(self):
        return getattr(self, 'simulation_timesteps', 0)

    def get_TTL_max(self):
        return getattr(self, 'TTL_max', 0)

    def get_max_vSDN_size(self):
        return getattr(self, 'max_vSDN_size', 0)

    def get_vSDN_max_size_ilp(self):
        return getattr(self, 'vSDN_max_size_ilp', 0)

    def get_vSDN_count_ilp(self):
        return getattr(self, 'vSDN_count_ilp', 0)

    def get_dynamic_simulation_name(self):
        return f"L{int(100*self.network_operator.get_latency_factor())}"
        # _mrs{self.get_max_vSDN_size()}_rpt{self.get_vSDN_request_count()}_ttl{self.get_TTL_max()}

    def get_static_simulation_name(self):
        return f"L{int(100*self.network_operator.get_latency_factor())}_rsi{int(self.get_vSDN_max_size_ilp())}_rci{int(self.get_vSDN_count_ilp())}"

    def get_simulation_type(self):
        return getattr(self, 'simulation_type', '')

    def get_sim_static_type(self):
        return getattr(self, 'sim_static_type', '')

    def get_sim_dynamic_type(self):
        return getattr(self, 'sim_dynamic_type', '')

    def save2pickle(self, path, obj):
        with open(path, 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def save_vSDN_history(self):
        self.save2pickle(
            self._result_folder + 'dynamic/' +
            f"{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.p",
            self.network_operator.vSDN_history)
        self.network_operator.vSDN_history = {}
