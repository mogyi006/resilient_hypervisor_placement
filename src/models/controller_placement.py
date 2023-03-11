# Standard library imports.
import random

# Related third party imports.

# Local application/library specific imports.

algorithms = {}
algo = lambda f: algorithms.setdefault(f.__name__, f)


@algo
def random_controller(network_operator, vSDN_request):
    # print("Random controller placement...")
    possible_controllers_ = find_possible_controllers(network_operator,
                                                      vSDN_request)
    if possible_controllers_:
        if vSDN_request.get_controller() in possible_controllers_:
            return vSDN_request.get_controller()
        else:
            # print(vSDN_request)
            # print(possible_controllers_)
            return random.choice(list(possible_controllers_))
    else:
        return None


@algo
def max_total_hpair(network_operator, vSDN_request):
    # print("Hpair maximized controller placement...")
    possible_controllers_ = find_possible_controllers(network_operator,
                                                      vSDN_request)

    if possible_controllers_:
        if vSDN_request.get_controller() in possible_controllers_:
            return vSDN_request.get_controller()
        else:
            hpair_stats = {
                c: get_hpair_stats(network_operator, c)
                for c in possible_controllers_
            }
            hpair_sums = {
                key: sum(val.values())
                for key, val in hpair_stats.items()
            }
            print(hpair_sums)
            return max(hpair_sums, key=hpair_sums.get)
    else:
        return None


def find_possible_controllers(network_operator, vSDN_request):
    possible_controllers_ = set(network_operator.possible_controllers)
    for s in vSDN_request.get_switches():
        # print(s, possible_controllers_)
        h, h_ = network_operator.hypervisor_assignment[s]
        possible_controllers_for_switch = set()
        for c in network_operator.possible_controllers:
            if (((c, h, h_, s) in network_operator.quartets_by_controllers[c])
                    or ((c, h_, h,
                         s) in network_operator.quartets_by_controllers[c])):
                possible_controllers_for_switch.add(c)
        possible_controllers_ &= possible_controllers_for_switch
    return possible_controllers_


def get_hpair_stats(network_operator, controller):
    hpair_stats = {s: 0 for s in network_operator.get_switches()}
    for (c, h, h_, s) in network_operator.quartets_by_controllers[controller]:
        hpair_stats[s] += 1
    return hpair_stats
