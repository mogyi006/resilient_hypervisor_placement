# Standard library imports.
import random

# Related third party imports.
import numpy as np
import networkx as nx

# Local application/library specific imports.
from src.logger import measure

import src.data.routing as routing
import src.data.graph_utilities as gu
from src.models.hypervisor_placement import hypervison_placement_solutions


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

    def get_active_hypervisor_count(self):
        return len(self.active_hypervisors)

    def get_chs_cp_stat(self, key):
        return int(self.cp_stats.get(key, -1))

    def get_node_count(self):
        return len(self.nodes)

    def get_hp_acceptance_ratio(self):
        return self.hp_acceptance_ratio

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

    def control_path_calculation(self, **kwargs) -> None:
        self.construct_possible_paths(**kwargs)
        self.construct_path_disjoint_quartets(**kwargs)
        self.construct_path_disjoint_triplets(**kwargs)
        return

    #@measure
    def hypervisor_placement(
        self,
        #  hp_type: str = 'heuristics',
        #  repeat: int = None,
        #  hp_objective: str = 'hypervisor count',
        **kwargs):
        # print(kwargs.keys())
        self.hp_type = kwargs.get('hp_type')
        self.hp_objective = kwargs.get('hp_objective')
        self.hp_greedy_repeat = kwargs.get('repeat')
        result, self.hp_runtime = hypervison_placement_solutions(**dict(
            kwargs,
            network_operator=self,
        ))
        # print(result)
        self.active_hypervisors = result.get('active hypervisors', [])
        # print("Active_hypervisors:", len(self.active_hypervisors))
        self.hp_acceptance_ratio = result.get('hp acceptance ratio', None)

        if 'hypervisor assignment' in result:
            self.hypervisor_assignment = result.get('hypervisor assignment',
                                                    [])
            self.hypervisor_switch_control_paths = result.get(
                'hypervisor2switch control paths', [])
        else:
            self.hypervisor_assignment, self.hypervisor_switch_control_paths = gu.assign_switches_to_hypervisors(
                S=self.nodes,
                Tc=result.get('Tc', self.triplets_by_switches),
                hypervisors=self.active_hypervisors,
                main_controller=result.get('main controller', None),
                Smc=result.get('S_controllable', []),
                all_paths=self.possible_paths,
                **kwargs)
        return None

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

    def find_controller_for_request(self, request):
        possible_controllers_ = set()
        for idx, s in enumerate(request._switches):
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
            return random.choice(
                list(possible_controllers_))  # ! controller selection
        else:
            None

    def process_vSDN_requests(self, request_list, to_process: bool = True):
        accepted = 0
        if not to_process:
            return accepted
        for request in request_list:
            #print(request)
            # if request._controller not in self.possible_controllers:
            #     print("Invalid request:", "Wrong controller - ", request._controller)
            #     continue
            if not (set(request._switches) <= set(self.nodes)):
                print("Invalid request:", "Wrong switches - ",
                      request._switches)
                continue

            c = self.find_controller_for_request(request)
            if c is None:
                # print("Invalid request:", "No controller")
                continue

            possible = True
            for s in request._switches:
                h, h_ = self.hypervisor_assignment[s]
                if (((c, h, h_, s) in self.quartets_by_controllers[c])
                        or ((c, h_, h, s) in self.quartets_by_controllers[c])):
                    continue
                else:
                    #print(f"No path-disjoint control path")
                    #print(c,h,h_,s)
                    #print(self.quartets_by_controllers[c])
                    possible = False
                    break

            if possible:
                accepted += 1
                self.active_vSDNs[request._id] = request
                self.vSDN_control_paths[request._id] = {}
                for s in request._switches:
                    h, h_ = self.hypervisor_assignment[s]
                    self.vSDN_control_paths[request._id][(
                        c, s)] = routing.full_control_path(
                            self.possible_paths, c, h, h_, s, self.max_length)
        # print("Acceptance ratio: ", accepted/len(request_list))
        return accepted

    def get_control_path_stats(self):
        primary_path_lengths, secondary_path_lengths = [], []
        for request_id in self.active_vSDNs.keys():
            for _, p in self.vSDN_control_paths[request_id].items():
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

    def discard_vSDN(self, id):
        _ = self.active_vSDNs.pop(id, None)
        _ = self.vSDN_control_paths.pop(id, None)
        _ = self.cp_stats.pop(id, None)

    def discard_all_vSDNs(self):
        self.active_vSDNs = {}
        self.vSDN_control_paths = {}
        self.cp_stats = {}

    def discard_old_vSDNs(self, _time):
        for id, vSDN in list(self.active_vSDNs.items()):
            if vSDN.get_end_time() == _time:
                self.discard_vSDN(id)
        return

    def get_active_controllers(self):
        return [vSDN._controller for _, vSDN in self.active_vSDNs.items()]
