# Standard library imports.
import random
import copy
from typing import List

# Related third party imports.
import numpy as np
import networkx as nx

# Local application/library specific imports.
from src.logger import measure

import src.data.routing as routing
import src.data.graph_utilities as gu
from src.models.hypervisor_placement import hypervisor_placement_solutions
from src.models import vSDN_request


# Network operator class
class NetworkOperator:
    def __init__(self, path: str, label: str = 'id', **kwargs):
        self.graph = nx.read_gml(path=path, label=label)
        self.nodes = list(self.graph.nodes)
        self.links = set(self.graph.edges)

        self.graph_diameter = gu.get_graph_diameter(self.graph)
        self.latency_factor = 1.
        self.max_length = self.latency_factor * self.graph_diameter
        self.shortest_k = 16

        # TODO Possible hypervisor and controller locations
        self.possible_hypervisors = list(self.graph.nodes)
        self.possible_controllers = list(self.graph.nodes)

        self.active_hypervisors = set()
        self.hypervisor_assignment = {}
        self.hypervisor_switch_control_paths = {}

        self.vSDNs = {}
        self.vSDN_control_paths = {}

    def __getattribute__(self, name: str):
        return object.__getattribute__(self, name)

    def get_graph_diameter(self):
        return self.graph_diameter

    def set_max_length(self, latency_factor, **kwargs):
        self.latency_factor = latency_factor
        self.max_length = self.latency_factor * self.graph_diameter

    def get_max_length(self):
        return int(self.max_length)

    def get_latency_factor(self):
        return self.latency_factor

    def set_shortest_k(self, shortest_k, **kwargs):
        self.shortest_k = shortest_k

    def get_shortest_k(self):
        return self.shortest_k

    def get_hp_type(self):
        return self.hp_type

    def get_hp_objective(self):
        return self.hp_objective

    def get_hp_greedy_repeat(self):
        return self.hp_greedy_repeat

    def get_ha_objective(self):
        return 'avg cp length'

    def get_hp_runtime(self):
        return float(f"{self.hp_runtime:.2f}")

    def get_cp_objective(self):
        return 'random'

    def get_active_hypervisors(self):
        return list(self.active_hypervisors)

    def get_active_hypervisor_count(self) -> int:
        return len(self.active_hypervisors)

    def get_chs_cp_stat(self, key):
        return int(self.cp_stats.get(key, -1))

    def get_node_count(self):
        return len(self.nodes)

    def get_hp_acceptance_ratio(self):
        return self.hp_acceptance_ratio

    def get_active_vSDN_count(self):
        return sum([vSDN.is_active() for _, vSDN in self.vSDNs.items()])

    #@measure
    def construct_possible_paths(self, **kwargs):
        if 'max_length' not in kwargs and 'shortest_k' not in kwargs:
            kwargs = {
                'max_length': self.max_length,
                'shortest_k': self.shortest_k
            }
        self.possible_paths = routing.get_all_paths(G=self.graph, **kwargs)
        return None

    #@measure
    def construct_path_disjoint_triplets(self, **kwargs):
        (self.triplets, self.triplets_by_hypervisors,
         self.triplets_by_switches) = gu.quartets_to_triplets(self.quartets)
        return None

    #@measure
    def construct_path_disjoint_quartets(self, **kwargs):
        (self.quartets, self.quartets_by_controllers,
         self.quartets_by_switches,
         self.quartets_by_cs) = gu.construct_quartets(
             all_paths=self.possible_paths,
             C=self.possible_controllers,
             S=self.nodes,
             H=self.possible_hypervisors,
             max_length=self.max_length)
        return None

    def get_allowed_hypervisor_pairs_by_switch(self, get_all: bool = False):
        """Return the hypervisor pairs that enable control paths
        with the current latency requirement."""
        _, active_controllers_by_switch = self.get_active_CS_pairs()
        allowed_hypervisor_pairs_by_switch = {}
        for s, triplets in self.triplets_by_switches.items():
            if s in active_controllers_by_switch.keys() and not get_all:
                for i, c in enumerate(active_controllers_by_switch[s]):
                    if i == 0:
                        allowed_hypervisor_pairs_by_switch[
                            s] = self.quartets_by_cs[(c, s)]
                    else:
                        allowed_hypervisor_pairs_by_switch[
                            s] = allowed_hypervisor_pairs_by_switch[
                                s].intersection(self.quartets_by_cs[(c, s)])
            else:
                allowed_hypervisor_pairs_by_switch[s] = set([
                    (i, j) for _, i, j in triplets if (i <= j)
                ])
        return allowed_hypervisor_pairs_by_switch

    def get_active_CS_pairs(self) -> set:
        active_cs_pairs = set()
        active_controllers_by_switch = {}
        for vSDN in self.get_active_vSDNs():
            c = vSDN.get_controller()
            for s in vSDN.get_switches():
                active_cs_pairs.add((c, s))
                active_controllers_by_switch.setdefault(s, set()).add(c)
        return active_cs_pairs, active_controllers_by_switch

    def control_path_calculation(self, **kwargs) -> None:
        self.construct_possible_paths(**kwargs)
        self.construct_path_disjoint_quartets(**kwargs)
        self.construct_path_disjoint_triplets(**kwargs)
        return

    #@measure
    def hypervisor_placement(self, **kwargs):
        # print(kwargs.keys())
        self.hp_type = kwargs.get('hp_type')
        self.hp_objective = kwargs.get('hp_objective')
        self.hp_greedy_repeat = kwargs.get('repeat')
        result, self.hp_runtime = hypervisor_placement_solutions(**dict(
            kwargs,
            network_operator=self,
        ))
        # print(result)
        self.active_hypervisors = result.get('active hypervisors', None)
        print("Active_hypervisors:", self.active_hypervisors)
        self.hp_acceptance_ratio = result.get('hp acceptance ratio', None)

        if 'hypervisor assignment' in result:
            self.hypervisor_assignment = result.get('hypervisor assignment',
                                                    None)
            self.hypervisor_switch_control_paths = result.get(
                'hypervisor2switch control paths', None)
        else:
            self.hypervisor_assignment, self.hypervisor_switch_control_paths = gu.assign_switches_to_hypervisors(
                S=self.nodes,
                Tc=result.get('Tc', self.triplets_by_switches),
                hypervisors=self.active_hypervisors,
                main_controller=result.get('main controller', None),
                Smc=result.get('S_controllable', []),
                all_paths=self.possible_paths,
                **kwargs)

        if 'request status' in result:
            print(result.get('request status'))
        return None

    def get_minimal_hypervisor_count(self, **kwargs) -> int:
        result, self.hp_runtime = hypervisor_placement_solutions(
            **{
                'hp_type': 'ilp',
                'hp_objective': 'hypervisor count',
                'network_operator': self
            })
        return len(result.get('active hypervisors', None))

    def get_hypervisor_switch_latencies(self):
        primary_paths, secondary_paths = [], []
        for s in self.nodes:
            h, h_ = self.hypervisor_assignment[s]
            p, q = self.hypervisor_switch_control_paths[(h, h_, s)]
            primary_paths.append(p['length'])
            secondary_paths.append(q['length'])
        print(f"Primary--\t{np.mean(primary_paths):5.1f}")
        print(f"Secondary--\t{np.mean(secondary_paths):5.1f}")
        print(f"Primary--\t{np.amax(primary_paths):5.1f}")
        print(f"Secondary--\t{np.amax(secondary_paths):5.1f}")
        return primary_paths, secondary_paths

    def find_controller_for_request(self, request: vSDN_request):
        possible_controllers_ = set()
        for idx, s in enumerate(request.get_switches()):
            h, h_ = self.hypervisor_assignment[s]
            possible_controllers_for_switch = set()
            for c in self.possible_controllers:
                if (((c, h, h_, s) in self.quartets_by_controllers[c])
                        or ((c, h_, h, s) in self.quartets_by_controllers[c])):
                    possible_controllers_for_switch.add(c)
            if idx == 0:
                possible_controllers_ |= possible_controllers_for_switch
            else:
                possible_controllers_ &= possible_controllers_for_switch
        if possible_controllers_:
            if request.get_controller() in possible_controllers_:
                return request.get_controller()
            else:
                return random.choice(
                    list(possible_controllers_))  # ! controller selection
        else:
            return None

    def preprocess_vSDN_requests(
            self, request_list: List[vSDN_request.vSDN_request]) -> List[bool]:
        return self.process_vSDN_requests(request_list, deploy=False)

    def process_vSDN_requests(self,
                              request_list: List[vSDN_request.vSDN_request],
                              deploy: bool = True,
                              **kwargs) -> List[bool]:

        accepted = [False] * len(request_list)

        for i, request in enumerate(request_list):
            self.vSDNs.setdefault(request.id, copy.deepcopy(request))
            #print(request)

            if not (set(request.get_switches()) <= set(self.nodes)):
                print("Invalid request:", "Wrong switches - ",
                      request.get_switches())
                continue

            c = self.find_controller_for_request(request)
            possible = c is not None
            if possible:
                for s in request.get_switches():
                    h, h_ = self.hypervisor_assignment[s]
                    if not (
                        ((c, h, h_, s) in self.quartets_by_controllers[c]) or
                        ((c, h_, h, s) in self.quartets_by_controllers[c])):
                        possible = False
                        break

            accepted[i] = possible

            if not deploy:
                continue

            if possible:
                self.deploy_vSDN(request, c, **kwargs)
            else:
                if request.is_active() and request.get_id() in self.vSDNs:
                    self.deactivate_vSDN(request.get_id(), **kwargs)

        print(f"Acceptance ratio: {np.mean(accepted):.3f}")
        return accepted

    def get_control_path_stats(self) -> None:
        primary_path_lengths, secondary_path_lengths = [], []
        for vSDN in self.get_active_vSDNs():
            for _, p in self.vSDN_control_paths[vSDN.get_id()].items():
                pl, ql = gu.control_path_length(p)
                primary_path_lengths.append(pl)
                secondary_path_lengths.append(ql)
        # print(f"Primary--\t{np.mean(primary_path_lengths):5.1f}")
        # print(f"Secondary--\t{np.mean(secondary_path_lengths):5.1f}")
        # print(f"Primary--\t{np.amax(primary_path_lengths):5.1f}")
        # print(f"Secondary--\t{np.amax(secondary_path_lengths):5.1f}")
        if primary_path_lengths and secondary_path_lengths:
            self.cp_stats = {
                'avg_p': np.mean(primary_path_lengths),
                'avg_b': np.mean(secondary_path_lengths),
                'max_p': np.amax(primary_path_lengths),
                'max_b': np.amax(secondary_path_lengths),
            }
            return
        else:
            self.cp_stats = {}
            return

    def deploy_vSDN(self,
                    request: vSDN_request,
                    c: int,
                    time: int = None,
                    **kwargs) -> None:
        request.set_controller(c)
        request.set_active()
        self.vSDNs[request.get_id()] = copy.deepcopy(request)

        self.vSDN_control_paths[request.get_id()] = {}
        for s in request.get_switches():
            h, h_ = self.hypervisor_assignment[s]
            self.vSDN_control_paths[request.get_id()][(
                c, s)] = routing.full_control_path(self.possible_paths, c, h,
                                                   h_, s, self.max_length)
        return

    def deactivate_vSDN(self, id, time) -> None:
        self.vSDNs[id].set_inactive()
        self.vSDNs[id].set_end_time(time)

        _ = self.vSDN_control_paths.pop(id, None)
        _ = self.cp_stats.pop(id, None)
        return

    def delete_all_vSDNs(self) -> None:
        self.vSDNs = {}
        self.vSDN_control_paths = {}
        self.cp_stats = {}
        return

    def deactivate_old_vSDNs(self, time) -> None:
        for vSDN in self.get_active_vSDNs():
            if vSDN.get_end_time() <= time:
                self.deactivate_vSDN(vSDN.get_id(), time)
        return

    def deactivate_all_vSDNs(self) -> None:
        for vSDN in self.get_active_vSDNs():
            self.deactivate_vSDN(vSDN.get_id(), vSDN.get_end_time())
        return

    def get_active_controllers(self) -> list:
        return [
            vSDN.get_controller() for _, vSDN in self.vSDNs.items()
            if vSDN.is_active()
        ]

    def get_active_vSDNs(self, only_ids: bool = False) -> list:
        if only_ids:
            return [
                vSDN_id for vSDN_id, vSDN in self.vSDNs.items()
                if vSDN.is_active()
            ]
        else:
            return [vSDN for _, vSDN in self.vSDNs.items() if vSDN.is_active()]
