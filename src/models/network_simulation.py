# Standard library imports.
import os
import datetime
import pickle
import pathlib
import itertools
from typing import List
import logging

# Related third party imports.
import numpy as np

# Local application/library specific imports.
from src.models import network_operator
from src.models import vSDN_request
from src.logger import measure, save2json

logging.basicConfig(
    format="[%(funcName)30s()] %(message)s",
    level=logging.INFO,
)


def generate_setting_list(setting_dict: dict) -> list:
    if setting_dict is None:
        raise ValueError
    param_names = list(setting_dict.keys())
    return [
        dict(zip(param_names, x))
        for x in itertools.product(*setting_dict.values())
    ]


class NetworkSimulation:
    def __init__(self, **kwargs) -> None:
        self.settings = {}
        self.results = {}

        self.settings['simulation_id'] = datetime.datetime.now().strftime(
            '%Y-%m-%d-%H-%M-%S')
        self.results['simulation_round'] = 0
        self.results['timestep'] = 0
        self.settings['network_name'] = kwargs.pop('network_name')
        self.settings['auto_accept'] = False

        self.init_folders(**kwargs)

        save2json(path=self.settings['result_folder'] + 'settings.json',
                  data=dict(kwargs,
                            simulation_id=self.settings['simulation_id']))

        self.init_network_operator(**kwargs)
        self.init_request_generators(**kwargs)

        self.logs = []
        self.vSDN_history = {}
        return

    def init_folders(self, **kwargs) -> None:
        self.settings[
            'network_path'] = f"../data/processed/networks/{self.settings['network_name']}.gml"
        self.settings[
            'request_folder'] = f"../data/processed/requests/{self.settings['network_name']}/"
        self.settings[
            'network_operator_folder'] = f"../data/processed/network_operators/{self.settings['network_name']}/"
        self.settings['result_folder'] = kwargs.get(
            'simulation_group_folder',
            f"../results/{self.settings['network_name']}/"
        ) + self.settings['simulation_id'] + '/'
        if not os.path.isdir(self.settings['result_folder']):
            os.mkdir(self.settings['result_folder'])
        return

    def get_network_operator_path(self, latency_factor, shortest_k, **kwargs):
        return pathlib.Path(
            f"{self.settings['network_operator_folder']}{self.settings['network_name']}_L{str(int(latency_factor*100))}_k{shortest_k}.p"
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
                path=self.settings['network_path'])
        return

    def save_network_operator(self, **kwargs) -> None:
        network_operator_path = self.get_network_operator_path(**kwargs)
        if not self.is_network_operator_file_available(**kwargs):
            self.save2pickle(network_operator_path, self.network_operator)
        return

    def init_request_generators(self, **kwargs) -> None:
        self.request_generator_static = vSDN_request.vSDN_request_generator(
            self.settings['network_name'], self.settings['request_folder'],
            **kwargs)
        self.request_generator_dynamic = vSDN_request.vSDN_request_generator(
            self.settings['network_name'], self.settings['request_folder'],
            **kwargs)
        self.request_generator_representative = vSDN_request.vSDN_request_generator(
            self.settings['network_name'], self.settings['request_folder'],
            **kwargs)
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
        self.delete_all_vSDNs()
        request_setting_list = generate_setting_list(possible_request_settings)

        self.hypervisor_placement(**kwargs)
        for request_setting in request_setting_list:
            self.run_static_request_simulation(**request_setting)
            _ = self.log_simulation()
            logging.info(f"Simulation results:" + ', '.join(
                f'{q:5.2f}' if isinstance(q, float) else f'{q:4d}'
                for q in self.results.values()))

            if (self.settings['auto_accept'] == False
                    and self.settings['vSDN_coverage'] == 1
                    and self.results['vSDN_acceptance_ratio'] == 1):
                logging.info("Auto accept enabled...")
                self.settings['auto_accept'] = True

        self.settings['auto_accept'] = False
        return

    def run_optimal_static_simulation(self,
                                      possible_request_settings: dict = None,
                                      **kwargs) -> None:
        self.delete_all_vSDNs()
        request_setting_list = generate_setting_list(possible_request_settings)

        for request_setting in request_setting_list:
            self.run_static_request_simulation(to_setup=False,
                                               **request_setting)
            self.hypervisor_placement(
                **{
                    'hp_type': 'ilp',
                    'hp_objective': 'acceptance ratio',
                    'vSDN_requests_ilp': self.vSDN_requests,
                    'n_hypervisors': self.get_minimal_hypervisor_count(),
                })

            _, self.results[
                'request_processing_time'] = self.setup_vSDN_requests(**kwargs)
            _ = self.log_simulation()
        return

    def run_multiple_static_simulation(self,
                                       sim_repeat: int = 10,
                                       static_type: str = 'basic',
                                       **kwargs) -> None:
        self.delete_logs()
        self.settings['simulation_type'] = 'static'
        self.settings['sim_static_type'] = static_type
        self.results['min_h_count'] = self.get_minimal_hypervisor_count(
            recalculate=True, **kwargs)

        for sim_id in range(sim_repeat):
            self.results['simulation_round'] = sim_id
            if static_type == 'opt':
                self.run_optimal_static_simulation(**kwargs)
            else:
                self.run_static_simulation(**kwargs)
        return

    def run_static_request_simulation(self,
                                      to_setup: bool = True,
                                      **kwargs) -> None:
        self.delete_all_vSDNs()
        self.generate_vSDN_requests(**kwargs)
        if to_setup:
            _, self.results[
                'request_processing_time'] = self.setup_vSDN_requests(**kwargs)
        return

    def run_basic_dynamic_simulation(self,
                                     timesteps: int = 100,
                                     **kwargs) -> None:
        """
        t=0 Hypervisor placement.
        t>0 Requests are arriving, reject new if not acceptable.
            No Reconfiguration!
        """
        self.results['timestep'] = 0
        self.delete_all_vSDNs()
        self.settings['simulation_timesteps'] = timesteps

        self.hypervisor_placement(**kwargs)

        for _ in range(self.settings['simulation_timesteps']):
            self.next_timestep(**kwargs)
            self.timestep_statistics()
            _ = self.log_simulation()

        self.deactivate_vSDNs(all=True)
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
        self.results['timestep'] = 0
        self.delete_all_vSDNs()
        self.settings['simulation_timesteps'] = timesteps

        for _ in range(self.settings['simulation_timesteps']):
            self.next_timestep(to_setup=False, **kwargs)

            all_acceptable = (self.results['timestep'] > 1) and (np.sum(
                self.preprocess_vSDN_requests(
                )) == self.get_vSDN_request_count())
            if self.results['timestep'] == 1:
                current_placement = set()
            else:
                current_placement = set(
                    self.network_operator.get_active_hypervisors())

            if not all_acceptable:
                self.hypervisor_placement(**dict(
                    kwargs,
                    vSDN_requests_ilp=(
                        self.vSDN_requests +
                        self.network_operator.get_active_vSDNs()),
                    required_vSDN_requests=self.network_operator.
                    get_active_vSDNs(only_ids=True),
                    n_hypervisors=self.get_minimal_hypervisor_count(),
                    prev_active_hypervisors=current_placement,
                ))

            new_placement = set(self.network_operator.get_active_hypervisors())
            self.results['hp_changed'] = len(new_placement - current_placement)
            # print(f"Current: {current_placement}\nNew: {new_placement}")
            self.setup_vSDN_requests()
            self.timestep_statistics()
            _ = self.log_simulation()

        self.deactivate_vSDNs(all=True)
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
        self.results['timestep'] = 0
        self.delete_all_vSDNs()
        self.settings['simulation_timesteps'] = timesteps

        for _ in range(self.settings['simulation_timesteps']):
            self.next_timestep(to_setup=False, **kwargs)
            self.vSDN_requests += self.network_operator.get_active_vSDNs()

            all_acceptable = (self.results['timestep'] > 1) and (np.sum(
                self.preprocess_vSDN_requests(
                )) == self.get_vSDN_request_count())
            current_placement = set(
                self.network_operator.get_active_hypervisors())

            if not all_acceptable:
                self.hypervisor_placement(
                    **dict(kwargs,
                           vSDN_requests_ilp=self.vSDN_requests,
                           n_hypervisors=self.get_minimal_hypervisor_count()))

            new_placement = set(self.network_operator.get_active_hypervisors())
            self.results['hp_changed'] = len(new_placement - current_placement)
            # print(f"Current: {current_placement}\nNew: {new_placement}")
            self.setup_vSDN_requests(time=self.results['timestep'])
            self.timestep_statistics()
            _ = self.log_simulation()

        self.deactivate_vSDNs(all=True)
        return

    def run_multiple_dynamic_simulations(self,
                                         sim_repeat: int = 10,
                                         dynamic_type: str = 'basic',
                                         **kwargs) -> None:
        self.delete_logs()
        self.settings['simulation_type'] = 'dynamic'
        self.settings['sim_dynamic_type'] = dynamic_type
        self.results['min_h_count'] = self.get_minimal_hypervisor_count(
            recalculate=True, **kwargs)

        for sim_round in range(sim_repeat):
            self.results['simulation_round'] = sim_round
            if dynamic_type == 'basic':
                self.run_basic_dynamic_simulation(**kwargs)
            elif dynamic_type == 'conservative':
                self.run_conservative_dynamic_simulation(**kwargs)
            elif dynamic_type == 'liberal':
                self.run_liberal_dynamic_simulation(**kwargs)
            else:
                pass
            self.save_vSDN_history(only_current_round=True)
            self.vSDN_history[sim_round] = self.network_operator.vSDNs
            self.delete_all_vSDNs()
        self.save_vSDN_history()
        return

    def next_timestep(self,
                      to_setup: bool = True,
                      request_per_timestep: int = 10,
                      **kwargs) -> None:
        self.results['timestep'] += 1
        self.deactivate_vSDNs()

        switch_hpairs = self.network_operator.get_allowed_hypervisor_pairs_by_switch(
        )
        self.results['switch_hpair_count'] = [
            len(switch_hpairs[s]) for s in self.network_operator.nodes
        ]
        self.results['mean_switch_hpair_count'] = np.mean(
            self.results['switch_hpair_count'])
        self.settings['TTL_max'] = kwargs.get('TTL_range', 0)
        self.settings['max_vSDN_size'] = kwargs.get('max_request_size', 0)
        self.vSDN_requests = self.request_generator_dynamic.get_random_vSDN_requests(
            **dict(kwargs,
                   total_count=request_per_timestep,
                   time_=self.results['timestep']))

        # ! Add vSDN preprocessing
        if to_setup:
            self.setup_vSDN_requests()

    def hypervisor_placement(self, **kwargs) -> None:
        self.network_operator.hypervisor_placement(**dict(
            kwargs,
            vSDN_requests=self.get_vSDN_requests_ilp(**kwargs),
            n_hypervisors=(kwargs.get(
                'n_hypervisors', self.get_minimal_hypervisor_count(**kwargs)) +
                           kwargs.get('n_extra_hypervisors', 0))))
        return

    def get_minimal_hypervisor_count(self,
                                     recalculate: bool = False,
                                     **kwargs) -> int:
        logging.debug(
            f"Minimal hypervisor count: {self.results.get('min_h_count')}")
        logging.debug(f"Recalculate: {recalculate}")

        if not recalculate and 'min_h_count' in self.results:
            return self.results['min_h_count']
        else:
            self.results[
                'min_h_count'] = self.network_operator.get_minimal_hypervisor_count(
                    **kwargs)
            return self.results['min_h_count']

    def modify_hypervisor_placement(self, **kwargs) -> None:
        return

    def generate_vSDN_requests(self, request_size: int, **kwargs) -> None:
        self.settings['vSDN_size'] = request_size
        (self.vSDN_requests, self.settings['vSDN_coverage'],
         self.settings['vSDN_count']
         ) = self.request_generator_static.get_request_list(
             request_size, **dict(kwargs, time_=self.results['timestep']))
        # print(self.vSDN_requests)
        return

    def get_vSDN_requests_ilp(self,
                              vSDN_count_ilp: int = 100,
                              vSDN_size_ilp: int = None,
                              **kwargs) -> List[vSDN_request.vSDN_request]:
        """Returns vSDN requests for the ILP.
        Generates new requests if a request list is not given."""
        if kwargs.get('vSDN_requests_ilp', None) is None:
            self.settings['vSDN_count_ilp'] = vSDN_count_ilp
            self.settings['vSDN_max_size_ilp'] = vSDN_size_ilp
            return self.request_generator_representative.get_random_vSDN_requests(
                max_request_size=vSDN_size_ilp,
                total_count=vSDN_count_ilp,
                time_=self.results['timestep'])
        else:
            return kwargs.get('vSDN_requests_ilp', None)

    def preprocess_vSDN_requests(self):
        return self.network_operator.preprocess_vSDN_requests(
            request_list=self.vSDN_requests)

    @measure
    def setup_vSDN_requests(self, **kwargs) -> None:
        if self.settings['auto_accept']:
            self.accepted_vSDN_requests = [True] * len(self.vSDN_requests)
        else:
            self.accepted_vSDN_requests = self.network_operator.process_vSDN_requests(
                request_list=self.vSDN_requests, **kwargs)

        self.results['vSDN_accepted_count'] = sum(self.accepted_vSDN_requests)
        self.results['vSDN_acceptance_ratio'] = self.results[
            'vSDN_accepted_count'] / len(self.vSDN_requests)
        _ = self.network_operator.get_control_path_stats()
        # print(latency_factor, max_length, request_size,
        #       len(self.network_operator.active_hypervisors), acceptance_ratio,
        #       *x)
        return

    def deactivate_vSDNs(self, all: bool = False) -> None:
        if all:
            self.network_operator.deactivate_all_vSDNs()
        else:
            self.network_operator.deactivate_old_vSDNs(
                self.results['timestep'])
        return

    def delete_all_vSDNs(self):
        self.network_operator.delete_all_vSDNs()

    def log_simulation(self):
        log = {**self.settings, **self.results, **self.network_operator.info}
        del log['vSDN_requests']
        self.logs.append(log)
        return log

    def get_logs(self):
        return self.logs

    def delete_logs(self):
        self.logs = []

    def get_vSDN_requests(self):
        return getattr(self, 'vSDN_requests', [])

    def get_vSDN_request_count(self):
        return len(self.get_vSDN_requests())

    def timestep_statistics(self):
        self.results[
            't_n_active_vSDNs'] = self.network_operator.get_active_vSDN_count(
            )
        self.results[
            't_switch_load_total'] = self.network_operator.get_switch_load_total(
            )
        self.results[
            't_revenue_total'] = self.network_operator.get_revenue_total(
                one_timestep=True)

    # def get_dynamic_simulation_name(self):
    #     return f"L{int(100*self.network_operator.get_latency_factor())}"
    #     # _mrs{self.get_max_vSDN_size()}_rpt{self.get_vSDN_request_count()}_ttl{self.get_TTL_max()}

    # def get_static_simulation_name(self):
    #     return f"L{int(100*self.network_operator.get_latency_factor())}_rsi{int(self.get_vSDN_max_size_ilp())}_rci{int(self.get_vSDN_count_ilp())}"

    def save2pickle(self, path, obj):
        with open(path, 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def save_vSDN_history(self, only_current_round: bool = False):
        if only_current_round:
            self.save2pickle(
                self.settings['result_folder'] +
                f"history_{self.results['simulation_round']}.p",
                self.network_operator.vSDNs)
        else:
            self.save2pickle(self.settings['result_folder'] + f"history.p",
                             self.vSDN_history)
