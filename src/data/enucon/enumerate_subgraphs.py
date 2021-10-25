from igraph import *
from time import time
import networkx as nx
from itertools import combinations
import queue
import bisect
import sys
sys.setrecursionlimit(10000000)


def isint(value):
    """converts into int, if possible"""
    try:
        a = int(value)
        return a
    except ValueError:
        return value


def print_names(graph, vertices):
    """Return a string with the ordered names of the vertices of the subgraph.
    graph: Is the (i)graph.
    vertices: Are the ID's of the subgraph."""
    vertex_list = []
    for vertex in vertices:
        vertex_list.append(isint(graph.vs[vertex]["name"]))
    # sort list increasing
    vertex_list.sort()
    # now print vertices
    out_line = ""
    for entry in vertex_list:
        out_line += str(entry) + " "
    return out_line + "\n"


# new version of exgen with break condition
def enu_all_subgraphs_return(graph, k, time_max, subgraph_file, start_time,
                             options):
    """Exgen Return
    Exgen with the new pruning rule
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: An Algorithmic Framework for Fixed-Cardinality Optimization in Sparse Graphs Applied to Dense Subgraph Problems.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # return if we exceed max time
        if time() > time_max:
            break
        # {i} is set_p, and set() is set_w of the algorithm
        new_nodes, new_size_k, start_time, max_delay, time_limit = calc_nodes(
            graph, 0, 0, {i}, set(), set(), k, i, time_max, subgraph_file,
            start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# recursive function for Exgen Return
def calc_nodes(graph, nodes, numb_size_k, set_p, set_w, neighbors_w, k,
               max_index, time_max, subgraph_file, start_time, max_delay):
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay, True

    # check if setP = k, then evaluate this subgraph
    size_sub = len(set_p) + len(set_w)
    if size_sub == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, set_p.union(set_w)))
        return nodes + 1, numb_size_k + 1, start_time, max_delay, False

    # check if following conditions are met
    #   |W| < |P| < k  and
    #   N(P)\N(W) != {}  this condition will be checked automatically
    if 0 == len(set_p):
        return nodes + 1, numb_size_k, start_time, max_delay, False

    # if not returned yet, we can find more subgraphs
    # determined vertex u in P\W randomly
    vert_u = set_p.pop()
    new_w = set_w.union({vert_u})

    # determine neighborhood of the chosen vertex vert_u
    neighbors_u = set()
    for vertex in graph.neighbors(vert_u):
        if vertex >= max_index:
            break
        #if vertex in neighbors_w or vertex in set_p or vertex in set_w:
        #    continue
        neighbors_u.add(vertex)
    neighbors_u.difference_update(neighbors_w)
    neighbors_u.difference_update(set_p)
    neighbors_u.difference_update(set_w)
    neighbors_w = neighbors_w.union(neighbors_u)

    # find all subsets of setForM and check above conditions
    # only find subsets M such that |P| + |M| <= k
    # remember: all vertices in W belong also to P
    # calculate all subsets of a set up to size k
    size_ad_sets = min(k - size_sub, len(neighbors_u))
    for i in range(size_ad_sets, -1, -1):
        # stopping criterion: if there are no new size k subgraphs for i=j, then there cannot be new size k subgraphs for i<j
        old_size_k = numb_size_k
        for subset in combinations(neighbors_u, i):
            new_p = set_p.union(set(subset))
            nodes, numb_size_k, start_time, max_delay, time_limit = calc_nodes(
                graph, nodes, numb_size_k, new_p, new_w, neighbors_w, k,
                max_index, time_max, subgraph_file, start_time, max_delay)
            if time_limit == True:
                return nodes + 1, numb_size_k, start_time, max_delay, True
        if old_size_k == numb_size_k:
            return nodes + 1, numb_size_k, start_time, max_delay, False

    return nodes + 1, numb_size_k, start_time, max_delay, False


# old version of exgen
def enu_all_subgraphs_old(graph, k, time_max, subgraph_file, start_time,
                          options):
    """Exgen Old
    Exgen without the pruning rule
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: An Algorithmic Framework for Fixed-Cardinality Optimization in Sparse Graphs Applied to Dense Subgraph Problems.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # return if we exceed max time
        if time() > time_max:
            break
        # {i} is set_p, and set() is set_w of the algorithm
        new_nodes, new_size_k, start_time, max_delay, time_limit = calc_nodes2(
            graph, 0, 0, {i}, set(), set(), k, i, time_max, subgraph_file,
            start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# recursive function for Exgen Old
def calc_nodes2(graph, nodes, numb_size_k, set_p, set_w, neighbors_w, k,
                max_index, time_max, subgraph_file, start_time, max_delay):
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay, True

    # check if setP = k, then evaluate this subgraph
    size_sub = len(set_p) + len(set_w)
    if size_sub == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, set_p.union(set_w)))
        return nodes + 1, numb_size_k + 1, start_time, max_delay, False

    # check if following conditions are met
    #   |W| < |P| < k  and
    #   N(P)\N(W) != {}  this condition will be checked automatically
    if 0 == len(set_p):
        return nodes + 1, numb_size_k, start_time, max_delay, False

    # if not returned yet, we can find more subgraphs
    # determined vertex u in P\W randomly
    vert_u = set_p.pop()
    new_w = set_w.union({vert_u})

    # determine neighborhood of the chosen vertex vert_u
    neighbors_u = set()
    for vertex in graph.neighbors(vert_u):
        if vertex >= max_index:
            break
        if vertex in neighbors_w or vertex in set_p or vertex in set_w:
            continue
        neighbors_u.add(vertex)
    neighbors_w = neighbors_w.union(neighbors_u)

    # find all subsets of setForM and check above conditions
    # only find subsets M such that |P| + |M| <= k
    # remember: all vertices in W belong also to P
    # calculate all subsets of a set up to size k
    size_ad_sets = min(k - size_sub, len(neighbors_u))
    for i in range(size_ad_sets, -1, -1):
        for subset in combinations(neighbors_u, i):
            new_p = set_p.union(set(subset))
            nodes, numb_size_k, start_time, max_delay, time_limit = calc_nodes2(
                graph, nodes, numb_size_k, new_p, new_w, neighbors_w, k,
                max_index, time_max, subgraph_file, start_time, max_delay)
            if time_limit == True:
                return nodes + 1, numb_size_k, start_time, max_delay, True

    return nodes + 1, numb_size_k, start_time, max_delay, False


# new version of kavosh with the break condition
def kavosh_return(graph, k, time_max, subgraph_file, start_time, options):
    """Kavosh Return
    Kavosh with pruning rule
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: Kavosh: a new algorithm for finding network motifs.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # return if we exceed max time
        if time() > time_max:
            break
        # {i} is set_p, and set() is set_w of the algorithm
        # here: setP = Vertex set Last
        # setW = all other older vertices
        new_nodes, new_size_k, start_time, max_delay, time_limit = nodes_kavosh(
            graph, 0, 0, {i}, set(), set(), k, i, time_max, subgraph_file,
            start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# recursive function for Kavosh Return
def nodes_kavosh(graph, nodes, numb_size_k, set_p, set_w, neighbors_w, k,
                 max_index, time_max, subgraph_file, start_time, max_delay):
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay, True

    # check if setP = k, then evaluate this subgraph
    size_sub = len(set_p) + len(set_w)
    if size_sub == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, set_p.union(set_w)))
        return nodes + 1, numb_size_k + 1, start_time, max_delay, False

    # in a first step calculate the neighborhood of Last (setP)
    neighbor_set = set()
    for vertex in set_p:
        for neig in graph.neighbors(vertex):
            if neig >= max_index:
                break
            neighbor_set.add(neig)
    neighbor_set.difference_update(set_p)
    neighbor_set.difference_update(set_w)
    neighbor_set.difference_update(neighbors_w)
    # update neighbors_w
    neighbors_w = neighbors_w.union(neighbor_set)

    new_w = set_w.union(set_p)
    size_ad_sets = min(k - size_sub, len(neighbor_set))
    # new_p = emptyset is NO valid choice since this adds no new vertex
    for i in range(size_ad_sets, 0, -1):
        # stopping criterion: if there are no new size k subgraphs for i=j, then there cannot be new size k subgraphs for i<j
        # so a similar trick as for exgen, pivot and simple
        old_size_k = numb_size_k
        for subset in combinations(neighbor_set, i):
            new_p = set(subset)
            nodes, numb_size_k, start_time, max_delay, time_limit = nodes_kavosh(
                graph, nodes, numb_size_k, new_p, new_w, neighbors_w, k,
                max_index, time_max, subgraph_file, start_time, max_delay)
            if time_limit == True:
                return nodes + 1, numb_size_k, start_time, max_delay, True
        if old_size_k == numb_size_k:
            return nodes + 1, numb_size_k, start_time, max_delay, False
    return nodes + 1, numb_size_k, start_time, max_delay, False


# old version of kavosh without break condition
def kavosh_old(graph, k, time_max, subgraph_file, start_time, options):
    """Kavosh Old
    Kavosh without the pruning rule
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: Kavosh: a new algorithm for finding network motifs.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # return if we exceed max time
        if time() > time_max:
            break
        # {i} is set_p, and set() is set_w of the algorithm
        # here: setP = Vertex set Last
        # setW = all other older vertices
        new_nodes, new_size_k, start_time, max_delay, time_limit = nodes_kavosh2(
            graph, 0, 0, {i}, set(), set(), k, i, time_max, subgraph_file,
            start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# recursive function fpr Kavosh Old
def nodes_kavosh2(graph, nodes, numb_size_k, set_p, set_w, neighbors_w, k,
                  max_index, time_max, subgraph_file, start_time, max_delay):
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay, True

    # check if setP = k, then evaluate this subgraph
    size_sub = len(set_p) + len(set_w)
    if size_sub == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, set_p.union(set_w)))
        return nodes + 1, numb_size_k + 1, start_time, max_delay, False

    # in a first step calculate the neighborhood of Last (setP)
    neighbor_set = set()
    for vertex in set_p:
        for neig in graph.neighbors(vertex):
            if neig >= max_index:
                break
            neighbor_set.add(neig)
    neighbor_set.difference_update(set_p)
    neighbor_set.difference_update(set_w)
    neighbor_set.difference_update(neighbors_w)
    # update neighbors_w
    neighbors_w = neighbors_w.union(neighbor_set)

    new_w = set_w.union(set_p)
    size_ad_sets = min(k - size_sub, len(neighbor_set))
    # new_p = emptyset is NO valid choice since this adds no new vertex
    for i in range(size_ad_sets, 0, -1):
        for subset in combinations(neighbor_set, i):
            new_p = set(subset)
            nodes, numb_size_k, start_time, max_delay, time_limit = nodes_kavosh2(
                graph, nodes, numb_size_k, new_p, new_w, neighbors_w, k,
                max_index, time_max, subgraph_file, start_time, max_delay)
            if time_limit == True:
                return nodes + 1, numb_size_k, start_time, max_delay, True

    return nodes + 1, numb_size_k, start_time, max_delay, False


# new improved version of pivot with the break condition
def pivot_subgraphs_return(graph, k, time_max, subgraph_file, start_time,
                           options):
    """Pivot Return
    Improved Pivot with pruning rule
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: Finding Dense Subgraphs of Sparse Graphs *.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # stop  if no time left
        if time() > time_max:
            break
        # choose a start vertex according to the choosed variant
        # at the start no subset of vertices is forbidden
        new_nodes, new_size_k, start_time, max_delay = pivot_subgrahs_one_vertex(
            graph, 0, 0, {i}, set(), k, set(), i, time_max, subgraph_file,
            start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# the third last entry is the list of forbidden vertices: every time we choose a new vertex u for the P-set then all vertices
#   with lower indices and also neighbors of the active vertices shouldn't be taken into P deeper in the search tree to
#   avoid double counting of solutions
def pivot_subgrahs_one_vertex(graph, nodes, numb_size_k, set_p, set_n, k,
                              forbidden, max_index, time_max, subgraph_file,
                              start_time, max_delay):
    # check if we exceed max time
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay
    # we found a subgraph of size k, so evaluate and return the calculated value
    l_p = len(set_p)
    if len(set_n) + l_p == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, set_p.union(set_n)))
        return nodes + 1, numb_size_k + 1, start_time, max_delay

    # subsequently choose each vertex in P as active vertex
    for i in range(l_p):
        # determine the element which will be popped (we cannot delete it yet since we need set_p for recursion)
        active = set_p.__iter__().next()

        # determine set X of new neighbors of the active vertex
        for vertex_u in graph.neighbors(active):
            if vertex_u >= max_index:
                break
            if vertex_u in forbidden or vertex_u in set_p or vertex_u in set_n:
                continue
            # add those vertices subsequently to P and try to iterate
            new_p = set_p.union({vertex_u})
            # if we cannot find a new size-k subgraph with vertex u, we cannot with another size-k subgraph with a
            #    vertex v with higher index in the neighborhood of the active vertex, also it is not possible with
            #    another active vertex, so we can reject
            old_size_k = numb_size_k
            nodes, numb_size_k, start_time, max_delay = pivot_subgrahs_one_vertex(
                graph, nodes, numb_size_k, new_p, set_n, k, forbidden,
                max_index, time_max, subgraph_file, start_time, max_delay)

            # afterwards we are done for vertex vertex_u, so we wont put it in another size-k subgraph
            forbidden = forbidden.union({vertex_u})

            # only take a new active vertex if we found at least one size-k subgraph before
            if old_size_k == numb_size_k:
                return nodes + 1, numb_size_k, start_time, max_delay

        # no more neighbors of active will be added here
        # vertex active will be inactive now
        set_p.pop()
        set_n = set_n.union({active})
    return nodes + 1, numb_size_k, start_time, max_delay


# new improved version of pivot without the break condition
def pivot_subgraphs_improved(graph, k, time_max, subgraph_file, start_time,
                             options):
    """Pivot Improved
    Pivot with worst case optimal number of search tree nodes and without the pruning rule
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: Finding Dense Subgraphs of Sparse Graphs *.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # stop  if no time left
        if time() > time_max:
            break
        # choose a start vertex according to the choosed variant
        # at the start no subset of vertices is forbidden
        new_nodes, new_size_k, start_time, max_delay = pivot_subgrahs_one_vertex2(
            graph, 0, 0, {i}, set(), k, set(), i, time_max, subgraph_file,
            start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# the third last entry is the list of forbidden vertices: every time we choose a new vertex u for the P-set then all vertices
#   with lower indices and also neighbors of the active vertices shouldn't be taken into P deeper in the search tree to
#   avoid double counting of solutions
def pivot_subgrahs_one_vertex2(graph, nodes, numb_size_k, set_p, set_n, k,
                               forbidden, max_index, time_max, subgraph_file,
                               start_time, max_delay):
    # check if we exceed max time
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay
    # we found a subgraph of size k, so evaluate and return the calculated value
    l_p = len(set_p)
    if len(set_n) + l_p == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, set_p.union(set_n)))
        return nodes + 1, numb_size_k + 1, start_time, max_delay

    # subsequently choose each vertex in P as active vertex
    for i in range(l_p):
        # determine the element which will be popped (we cannot delete it yet since we need set_p for recursion)
        active = set_p.__iter__().next()

        # determine set X of new neighbors of the active vertex
        for vertex_u in graph.neighbors(active):
            if vertex_u >= max_index:
                break
            if vertex_u in forbidden or vertex_u in set_p or vertex_u in set_n:
                continue
            # add those vertices subsequently to P and try to iterate
            new_p = set_p.union({vertex_u})
            # if we cannot find a new size-k subgraph with vertex u, we cannot with another size-k subgraph with a
            #    vertex v with higher index in the neighborhood of the active vertex, also it is not possible with
            #    another active vertex, so we can reject
            nodes, numb_size_k, start_time, max_delay = pivot_subgrahs_one_vertex2(
                graph, nodes, numb_size_k, new_p, set_n, k, forbidden,
                max_index, time_max, subgraph_file, start_time, max_delay)

            # afterwards we are done for vertex vertex_u, so we wont put it in another size-k subgraph
            forbidden = forbidden.union({vertex_u})

        # no more neighbors of active will be added here
        # vertex active will be inactive now
        set_p.pop()
        set_n = set_n.union({active})
    return nodes + 1, numb_size_k, start_time, max_delay


# old version of pivot without improved search tree and without the break condition
def pivot_subgraphs_old(graph, k, time_max, subgraph_file, start_time,
                        options):
    """Pivot Old
    Pivot without pruning rule and without worst case optimal number of search tree nodes
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: Finding Dense Subgraphs of Sparse Graphs *.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # stop  if no time left
        if time() > time_max:
            break
        # choose a start vertex according to the choosed variant
        # at the start no subset of vertices is forbidden
        # next entry is the active vertex (it is similar with the start vertex)
        new_nodes, new_size_k, start_time, max_delay = pivot_subgrahs_one_vertex3(
            graph, 0, 0, {i}, set(), k, i, set(), i, time_max, subgraph_file,
            start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# the third last entry is the list of forbidden vertices: every time we choose a new vertex u for the P-set then all vertices
#   with lower indices and also neighbors of the active vertices shouldn't be taken into P deeper in the search tree to
#   avoid double counting of solutions
def pivot_subgrahs_one_vertex3(graph, nodes, numb_size_k, set_p, set_n, k,
                               active, forbidden, max_index, time_max,
                               subgraph_file, start_time, max_delay):
    # check if we exceed max time
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay
    # we found a subgraph of size k, so evaluate and return the calculated value
    l_p = len(set_p)
    if len(set_n) + l_p == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, set_p.union(set_n)))
        return nodes + 1, numb_size_k + 1, start_time, max_delay

    # go further, if |P| < k
    # if there is no active vertex, choose a vertex in P\N as new active vertex v
    if active == -1:
        # pick element according to variant from this set
        # if setP=setN we found a new subgraph, since len(set_p)<k, we abort this branch
        if len(set_p) == 0:
            return nodes + 1, numb_size_k, start_time, max_delay
        active = set_p.__iter__().next()

    # now branch for each neighbour u of active in V\P that is not adjacent to any vertices in N, create node (P+u,N)
    # so we create one branch for each possibility to add a neighbor of active
    # keep active as the active vertex in each branch

    # determine set X of new neighbors of the active vertex
    for vertex_u in graph.neighbors(active):
        if vertex_u >= max_index:
            break
        if vertex_u in forbidden or vertex_u in set_p or vertex_u in set_n:
            continue

        # create new set_p and then recursive call
        new_p = set_p.union({vertex_u})
        nodes, numb_size_k, start_time, max_delay = pivot_subgrahs_one_vertex3(
            graph, nodes, numb_size_k, new_p, set_n, k, active, forbidden,
            max_index, time_max, subgraph_file, start_time, max_delay)
        # since vertex_u was added before, we do not have to add it later
        # note that it can be forbidden in the last branching too, where the active node changes, since vertexU is a
        #    neighbor of the active node and vertices in N have no neighbors in S\P
        forbidden = forbidden.union({vertex_u})

    # create one more branch (P, N+active)
    # no more neighbors of v will be added here
    # active will be inactive now
    set_p.remove(active)
    new_n = set_n.union({active})
    nodes, numb_size_k, start_time, max_delay = pivot_subgrahs_one_vertex3(
        graph, nodes, numb_size_k, set_p, new_n, k, -1, forbidden, max_index,
        time_max, subgraph_file, start_time, max_delay)
    return nodes + 1, numb_size_k, start_time, max_delay


# new version of the simple algorithm with break condition
def simple_enumeration_return(graph, k, time_max, subgraph_file, start_time,
                              options):
    """Simple Return
    Simple with pruning rule
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: A Faster Algorithm for Detecting Network Motifs.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # stop if we exceed max time
        if time() > time_max:
            break
        # put i in the neighbors of the subgraph, to fulfill the condition: index(u)<index(v) by expending ex_neighbors
        neighbors = set()
        for vertex in graph.neighbors(i):
            if vertex >= i:
                break
            neighbors.add(vertex)
        vertex = [i]
        neighbors_subgraph = neighbors.union(vertex)
        new_nodes, new_size_k, start_time, max_delay = extend_subgraph(
            graph, k, 0, 0, vertex, neighbors, neighbors_subgraph, i, time_max,
            subgraph_file, start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# standard notation for variables
# subgraph is the current subgraph, ex_neighborhood is the current neighborhood of the subgraph, which can be chosen
# neighbors_subgraph is the closed neighborhood of the current subgraph
def extend_subgraph(graph, k, nodes, numb_size_k, subgraph, ex_neighborhood,
                    neighbors_subgraph, max_index, time_max, subgraph_file,
                    start_time, max_delay):
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay
    # if we have a subgraph of size k, evaluate
    if len(subgraph) == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, subgraph))
        return nodes + 1, numb_size_k + 1, start_time, max_delay

    # wernicke choosed an arbitrary element of the extended neighborhood, we pick always the first vertex (pop)
    while len(ex_neighborhood) > 0:
        vertex_w = ex_neighborhood.pop()
        # only use those vertices with index smaller max_index
        neighbors_w = set()
        for vertex in graph.neighbors(vertex_w):
            if vertex >= max_index:
                break
            neighbors_w.add(vertex)
        # now calculate exclusive neighborhood of w, which is not contained in subgraph
        new_ex_neighborhood = neighbors_w.difference(neighbors_subgraph)
        new_ex_neighborhood.update(ex_neighborhood)
        # add vertex w to the subgraph
        subgraph.append(vertex_w)
        # recursive call
        # update neighbors_subgraph (set_union with the neighbors of the new vertex w)
        new_neighbors_subgraph = neighbors_subgraph.union(neighbors_w)
        old_size_k = numb_size_k
        nodes, numb_size_k, start_time, max_delay = extend_subgraph(
            graph, k, nodes, numb_size_k, subgraph, new_ex_neighborhood,
            new_neighbors_subgraph, max_index, time_max, subgraph_file,
            start_time, max_delay)
        # afterwards remove vertex w from the subgraph, such that we can evaluate the next vertex
        subgraph.pop()
        # same trick as in exgen, kavosh and pivot: if we cannot find a size k subgraph with this vertex it is not possible with other children
        if old_size_k == numb_size_k:
            return nodes + 1, numb_size_k, start_time, max_delay
    return nodes + 1, numb_size_k, start_time, max_delay


# old version of the simple algorithm without break condition
def simple_enumeration_old(graph, k, time_max, subgraph_file, start_time,
                           options):
    """Simple Old
    Simple withput the pruning rule
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: A Faster Algorithm for Detecting Network Motifs.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # stop if we exceed max time
        if time() > time_max:
            break
        # put i in the neighbors of the subgraph, to fulfill the condition: index(u)<index(v) by expending ex_neighbors
        neighbors = set()
        for vertex in graph.neighbors(i):
            if vertex >= i:
                break
            neighbors.add(vertex)
        vertex = [i]
        neighbors_subgraph = neighbors.union(vertex)
        new_nodes, new_size_k, start_time, max_delay = extend_subgraph2(
            graph, k, 0, 0, vertex, neighbors, neighbors_subgraph, i, time_max,
            subgraph_file, start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# standard notation for variables
# subgraph is the current subgraph, ex_neighborhood is the current neighborhood of the subgraph, which can be chosen
# neighbors_subgraph is the closed neighborhood of the current subgraph
def extend_subgraph2(graph, k, nodes, numb_size_k, subgraph, ex_neighborhood,
                     neighbors_subgraph, max_index, time_max, subgraph_file,
                     start_time, max_delay):
    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return nodes, numb_size_k, start_time, max_delay
    # if we have a subgraph of size k, evaluate
    if len(subgraph) == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, subgraph))
        return nodes + 1, numb_size_k + 1, start_time, max_delay

    # wernicke choosed an arbitrary element of the extended neighborhood, we pick always the first vertex (pop)
    while len(ex_neighborhood) > 0:
        vertex_w = ex_neighborhood.pop()
        # only use those vertices with index smaller max_index
        neighbors_w = set()
        for vertex in graph.neighbors(vertex_w):
            if vertex >= max_index:
                break
            neighbors_w.add(vertex)
        # now calculate exclusive neighborhood of w, which is not contained in subgraph
        new_ex_neighborhood = neighbors_w.difference(neighbors_subgraph)
        new_ex_neighborhood.update(ex_neighborhood)
        # add vertex w to the subgraph
        subgraph.append(vertex_w)
        # recursive call
        # update neighbors_subgraph (set_union with the neighbors of the new vertex w)
        new_neighbors_subgraph = neighbors_subgraph.union(neighbors_w)
        nodes, numb_size_k, start_time, max_delay = extend_subgraph2(
            graph, k, nodes, numb_size_k, subgraph, new_ex_neighborhood,
            new_neighbors_subgraph, max_index, time_max, subgraph_file,
            start_time, max_delay)
        # afterwards remove vertex w from the subgraph, such that we can evaluate the next vertex
        subgraph.pop()
    return nodes + 1, numb_size_k, start_time, max_delay


# enumeration algorithm by maxwell et al (optimal order condition fulfilled)
# for each connected subgraph S, we first evaluate each connected subgraph S' with S' /subseteq S
# depth visits new vertices, breadth copies already visited vertices
def bdde(graph, k, time_max, subgraph_file, start_time, options):
    """BDDE
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: Efficiently Enumerating All Connected Induced Subgraphs of a Large Molecular Network.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    options: Up to now, no use.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    # for each fixed vertex v find all connected subgraphs which include v
    # after the enumeration delete vertex v
    nodes = 0
    numb_size_k = 0
    max_delay = 0
    # consider only graphs with at least k vertices
    for i in range(graph.vcount() - 1, k - 2, -1):
        # check if we exceed max time
        if time() > time_max:
            break
        # search tree by maxwell
        search_tree = nx.DiGraph()
        active, search_tree, new_nodes, new_size_k, start_time, max_delay = depth(
            graph, k, 0, 0, [], i, [], search_tree, {i}, i, time_max,
            subgraph_file, start_time, max_delay)
        nodes += new_nodes
        numb_size_k += new_size_k
    return nodes, numb_size_k, max_delay


# set_s is set S of maxwells algorithm, this stores the connected subgraph up to now
# active_vertex is the actual vertex (name) which will be considered in this step (v in maxwell paper)
# vertices_to_clone this stores vertices which have already been visited; they will be cloned with breadth (beta in maxwell)
# all remaining parameters are similar to the remaining algorithms
# numb_size_k is the number of size_k subgraphs already enumerated
def depth(graph, k, nodes, numb_size_k, set_s, active_vertex,
          vertices_to_clone, search_tree, neighbors_s, max_index, time_max,
          subgraph_file, start_time, max_delay):
    # evaluation and stopping

    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        set_s.append(active_vertex)
        return -1, search_tree, nodes, numb_size_k, start_time, max_delay

    # if we have a subgraph of size k, evaluate
    if len(set_s) + 1 == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        set_s.append(active_vertex)
        subgraph_file.write(print_names(graph, set_s))
        return -1, search_tree, nodes + 1, numb_size_k + 1, start_time, max_delay

    # calculate x_vertex
    neighbors_a = set()
    for vertex in graph.neighbors(active_vertex):
        if vertex >= max_index:
            break
        neighbors_a.add(vertex)
    # determine d_vertex from the active vertex and the set S, note: the first vertex in S is the "root"
    # since x_vertex = c_vertex\d_vertex, just subtract the closed neighborhood of S from x_vertex
    x_vertex = neighbors_a.difference(neighbors_s)
    # add active_vertices to the set S
    set_s.append(active_vertex)

    # create new search tree node
    actual_index = len(search_tree)
    search_tree.add_node(actual_index, name=active_vertex)

    # new clones, will be updated if breadth does something
    new_clones = []

    # recursive call of breadth
    for clone in vertices_to_clone:
        new_node, search_tree, nodes, numb_size_k, start_time, max_delay = breadth(
            graph, k, nodes, numb_size_k, set_s, clone, x_vertex, search_tree,
            time_max, subgraph_file, start_time, max_delay)
        set_s.pop()
        if new_node != -1:
            # update search tree structure
            new_clones.append(new_node)
            search_tree.add_edge(actual_index, new_node)

    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        set_s.append(active_vertex)
        return -1, search_tree, nodes, numb_size_k, start_time, max_delay

    # recursive call of depth
    new_neighbors_s = neighbors_s.union(neighbors_a)
    for vertex in x_vertex:
        new_node, search_tree, nodes, numb_size_k, start_time, max_delay = depth(
            graph, k, nodes, numb_size_k, set_s, vertex, new_clones,
            search_tree, new_neighbors_s, max_index, time_max, subgraph_file,
            start_time, max_delay)
        set_s.pop()
        if new_node != -1:
            # update search tree structure
            new_clones.append(new_node)
            search_tree.add_edge(actual_index, new_node)
    return actual_index, search_tree, nodes + 1, numb_size_k, start_time, max_delay


# function to copy siblings of the enumeration tree
def breadth(graph, k, nodes, numb_size_k, set_s, actual_vertex_id, forbidden,
            search_tree, time_max, subgraph_file, start_time, max_delay):
    # append the vertex (name) of the actual search tree node to the set S
    vertex_name = search_tree.node[actual_vertex_id]["name"]
    set_s.append(vertex_name)
    # stop condition
    if vertex_name in forbidden:
        return -1, search_tree, nodes, numb_size_k, start_time, max_delay

    time_now = time()
    if time_now > time_max:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        return -1, search_tree, nodes, numb_size_k, start_time, max_delay

    # if we have a subgraph of size k, evaluate
    if len(set_s) == k:
        time_difference = time_now - start_time
        if time_difference > max_delay:
            max_delay = time_difference
        start_time = time_now
        subgraph_file.write(print_names(graph, set_s))
        return -1, search_tree, nodes + 1, numb_size_k + 1, start_time, max_delay

    # create new search tree node
    actual_index = len(search_tree)
    search_tree.add_node(actual_index, name=vertex_name)

    # copy clones; to this end use the tree-structure, saved in tree edges
    for vertex in search_tree.neighbors(actual_vertex_id):
        new_node, search_tree, nodes, numb_size_k, start_time, max_delay = breadth(
            graph, k, nodes, numb_size_k, set_s, vertex, forbidden,
            search_tree, time_max, subgraph_file, start_time, max_delay)
        set_s.pop()
        if new_node != -1:
            # update search tree structure
            search_tree.add_edge(actual_index, new_node)
    return actual_index, search_tree, nodes + 1, numb_size_k, start_time, max_delay


# this is the new version of this algorithm with an improved delay
# faster delay algorithm with exponential space
def delay_new(graph, k, time_max, subgraph_file, start_time, start_subs):
    """RwD New
    Reverse with Dictionary with improved calculating of common neighborhood
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: A Polynomial Delay Algorithm for Generating Connected Induced Subgraphs of a Given Cardinality.
    This algorithm uses the supergraph method.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    start_subs: This list stores the start vertices of each component with at least k vertices.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    reduced_size = k - 1
    max_delay = 0
    # set of all size k subgraphs
    size_k_subs = set()
    subgraph_queue = queue.Queue()
    # run the enumeration algorithm for each connected component with at least k vertices
    for component in start_subs:
        # initialize queue with this subgraph
        subgraph_queue.put(component)
        size_k_subs.add(print_names(graph, component))
        while subgraph_queue.empty() == False:
            time_now = time()
            if time_now > time_max:
                time_difference = time_now - start_time
                if time_difference > max_delay:
                    max_delay = time_difference
                break
            time_difference = time_now - start_time
            if time_difference > max_delay:
                max_delay = time_difference
            start_time = time_now
            subgraph = subgraph_queue.get()
            # output this subgraph
            subgraph_file.write(print_names(graph, subgraph))
            # remove each vertex from the set and try to replace it with another vertex such that its connected
            subgraph_co = set(subgraph[:])
            # subsequently remove each vertex from the subgraph
            for vertex in subgraph_co:
                time_now = time()
                if time_now > time_max:
                    time_difference = time_now - start_time
                    if time_difference > max_delay:
                        max_delay = time_difference
                    return "no search tree", len(size_k_subs), max_delay
                # first determine the connected components of subgraph\{vertex}
                subgraph.remove(vertex)
                U = union_find(list(subgraph))
                for i in range(reduced_size):
                    vertex1 = subgraph[i]
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", len(size_k_subs), max_delay
                    for j in range(i + 1, reduced_size):
                        vertex2 = subgraph[j]
                        if graph.are_connected(vertex1, vertex2):
                            U.union(vertex1, vertex2)
                coms_sub = U.components()

                # determine common neighborhood of each connected component of the "reduced" graph
                pos_neighs = set()
                check = False
                for i in range(len(coms_sub)):
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", len(size_k_subs), max_delay
                    neighbors_compo = set()
                    for vertex_compo in coms_sub[i]:
                        time_now = time()
                        if time_now > time_max:
                            time_difference = time_now - start_time
                            if time_difference > max_delay:
                                max_delay = time_difference
                            return "no search tree", len(
                                size_k_subs), max_delay
                        for neig in graph.neighbors(vertex_compo):
                            if neig > vertex:
                                break
                            neighbors_compo.add(neig)
                    if check == True:
                        pos_neighs.intersection_update(neighbors_compo)
                    else:
                        pos_neighs = neighbors_compo.difference(subgraph_co)
                        check = True
                    # stopping criterion: if pos_neighs set is empty, then no vertex is connected with each component
                    if len(pos_neighs) == 0:
                        break

                # now, all vertices in pos_ are common neighbors of all connected components, so add them subsequently
                for neig in pos_neighs:
                    subgraph.append(neig)
                    sub_name = print_names(graph, subgraph)
                    # check if this is a new subgraph
                    if sub_name not in size_k_subs:
                        size_k_subs.add(sub_name)
                        subgraph_queue.put(subgraph[:])
                    subgraph.remove(neig)
                # this enumeration step ended, hence insert the removed vertex
                subgraph.append(vertex)
    return "no search tree", len(size_k_subs), max_delay


# this is the old version of this algorithm with the delay by  elbassoni
# faster delay algorithm with exponential space
def delay_old(graph, k, time_max, subgraph_file, start_time, start_subs):
    """RwD Old
    Reverse with Dictionary without improved calculating of common neighborhood
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: A Polynomial Delay Algorithm for Generating Connected Induced Subgraphs of a Given Cardinality.
    This algorithm uses the supergraph method.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    start_vertices: This list stores the start vertices of each component with at least k vertices.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    reduced_size = k - 1
    max_delay = 0
    # set of all size k subgraphs
    size_k_subs = set()
    subgraph_queue = queue.Queue()
    # run the enumeration algorithm for each connected component with at least k vertices
    for component in start_subs:
        # initialize queue with this subgraph
        subgraph_queue.put(component)
        size_k_subs.add(print_names(graph, component))
        while subgraph_queue.empty() == False:
            time_now = time()
            if time_now > time_max:
                time_difference = time_now - start_time
                if time_difference > max_delay:
                    max_delay = time_difference
                break
            time_difference = time_now - start_time
            if time_difference > max_delay:
                max_delay = time_difference
            start_time = time_now
            subgraph = subgraph_queue.get()
            # output this subgraph
            subgraph_file.write(print_names(graph, subgraph))
            # determine all neighbors of this subgraph
            # remove each vertex from the set and try to replace it with another vertex such that its connected
            subgraph_co = subgraph[:]
            for vertex in subgraph_co:
                time_now = time()
                if time_now > time_max:
                    time_difference = time_now - start_time
                    if time_difference > max_delay:
                        max_delay = time_difference
                    return "no search tree", len(size_k_subs), max_delay
                # first determine the connected components of subgraph\{vertex}
                subgraph.remove(vertex)
                U = union_find(list(subgraph))
                for i in range(reduced_size):
                    vertex1 = subgraph[i]
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", len(size_k_subs), max_delay
                    for j in range(i + 1, reduced_size):
                        vertex2 = subgraph[j]
                        if graph.are_connected(vertex1, vertex2):
                            U.union(vertex1, vertex2)
                coms_sub = U.components()

                # add subsequently each possible neighbor to this subgraph
                pos_neighbors = set()
                for v in subgraph:
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", len(size_k_subs), max_delay
                    for neig in graph.neighbors(v):
                        # the new subgraph is lexicographically larger, hence neig>vertex holds
                        if neig > vertex:
                            break
                        if neig not in pos_neighbors and neig not in subgraph_co:
                            pos_neighbors.add(neig)
                            # check for connectivity and add edges
                            conn = True
                            for i in range(len(coms_sub)):
                                check = False
                                time_now = time()
                                if time_now > time_max:
                                    time_difference = time_now - start_time
                                    if time_difference > max_delay:
                                        max_delay = time_difference
                                    return "no search tree", len(
                                        size_k_subs), max_delay
                                for vertex_compo in coms_sub[i]:
                                    if graph.are_connected(vertex_compo, neig):
                                        check = True
                                        break
                                if check == False:
                                    conn = False
                                    break
                            # only go further if the graph is connected
                            if conn == False:
                                continue
                            subgraph.append(neig)
                            sub_name = print_names(graph, subgraph)
                            # check if this is a new subgraph
                            if sub_name not in size_k_subs:
                                size_k_subs.add(sub_name)
                                subgraph_queue.put(subgraph[:])
                            subgraph.remove(neig)
                # this enumeration step ended, hence insert vertex and the removed edges
                subgraph.append(vertex)
    return "no search tree", len(size_k_subs), max_delay


# union find structure used for the polynomial delay algorithm
# union by rank and path compensation are implemented
class union_find:
    """Union-Find data structure implemented with path compression and union by rank."""
    def __init__(self, names):
        n = len(names)
        rang = range(len(names))
        self.parent = rang
        self.rank = [0] * n
        self.name_to_index = dict(zip(names, rang))
        self.name = names

    def find_index(self, name_s):
        return self.name_to_index[name_s]

    def find(self, index):
        if not index == self.parent[index]:
            self.parent[index] = self.find(self.parent[index])
        return self.parent[index]

    # input are vertex names, NOT indices
    def union(self, ind_a, ind_b):
        ind_a = self.find(self.find_index(ind_a))
        ind_b = self.find(self.find_index(ind_b))
        if ind_a == ind_b:
            return
        if self.rank[ind_a] > self.rank[ind_b]:
            self.parent[ind_b] = ind_a
        else:
            self.parent[ind_a] = ind_b
            if self.rank[ind_a] == self.rank[ind_b]:
                self.rank[ind_b] += 1

    def printParent(self):
        print("parent: ", self.parent)
        print("names", self.name_to_index)

    def representives(self):
        representatives = []
        for i in range(len(self.name)):
            if i == self.parent[i]:
                representatives.append(self.name[i])
        return representatives

    # returns the set of vertices in each component as sets
    def components(self):
        reps = self.representives()
        for i in range(len(reps)):
            reps[i] = self.find_index(reps[i])
        compos = [set() for x in range(len(reps))]
        for i in range(len(self.name)):
            compos[reps.index(self.find(i))].add(self.name[i])
        return compos


# the new version of this algorithm with an improved delay
# delay algorithm based on reversed search
def reverse_new(graph, k, time_max, subgraph_file, start_time, start_subs):
    """RwP New
    Reverse with Predecessor with improved calculating of common neighborhood
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: A Polynomial Delay Algorithm for Generating Connected Induced Subgraphs of a Given Cardinality.
    This algorithm uses the reverse search method.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    start_vertices: This list stores the start vertices of each component with at least k vertices.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    max_delay = 0
    reduced_size = k - 1
    numb_size_k = 0
    # run the enumeration algorithm for each connected component with at least k vertices
    for component in start_subs:
        # save all size-k subgraphs we still have to work on in a queue (to get rid of recursion)
        subgraph_queue = queue.Queue()
        subgraph_queue.put(component)
        while subgraph_queue.empty() == False:
            numb_size_k += 1
            time_now = time()
            if time_now > time_max:
                time_difference = time_now - start_time
                if time_difference > max_delay:
                    max_delay = time_difference
                break
            time_difference = time_now - start_time
            if time_difference > max_delay:
                max_delay = time_difference
            start_time = time_now
            subgraph = subgraph_queue.get()
            # output this subgraph
            subgraph_file.write(print_names(graph, subgraph))

            subgraph_co = subgraph[:]
            # subsequently remove each vertex from the subgraph to get new size-k subgraphs
            for vertex in subgraph_co:
                time_now = time()
                if time_now > time_max:
                    time_difference = time_now - start_time
                    if time_difference > max_delay:
                        max_delay = time_difference
                    return "no search tree", numb_size_k, max_delay
                subgraph.remove(vertex)
                # determine the connected components of the components of the "reduced" graph
                U = union_find(subgraph)
                for i in range(reduced_size):
                    vertex1 = subgraph[i]
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", numb_size_k, max_delay
                    for j in range(i + 1, reduced_size):
                        vertex2 = subgraph[j]
                        if graph.are_connected(vertex1, vertex2):
                            U.union(vertex1, vertex2)
                coms_sub = U.components()

                # now determine the common neighborhood of all connected components
                check = False
                for i in range(len(coms_sub)):
                    neighbors_compo = set()
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", numb_size_k, max_delay
                    for vertex_compo in coms_sub[i]:
                        time_now = time()
                        if time_now > time_max:
                            time_difference = time_now - start_time
                            if time_difference > max_delay:
                                max_delay = time_difference
                            return "no search tree", numb_size_k, max_delay
                        for neig in graph.neighbors(vertex_compo):
                            if neig > vertex:
                                break
                            neighbors_compo.add(neig)
                    if check == True:
                        pos_neighs.intersection_update(neighbors_compo)
                    else:
                        pos_neighs = neighbors_compo.difference(subgraph_co)
                        check = True
                    # stopping criterion: if pos_neighs set is empty, then no vertex is connected with each component
                    if len(pos_neighs) == 0:
                        break

                # now we add subsequently each possible neighbor to the set
                for neig in pos_neighs:
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", numb_size_k, max_delay
                    # add this vertex to get a size k subgraph, insert it sorted to find f(subgraph) faster
                    bisect.insort(subgraph, neig)
                    # only add this neighbor, if f(neighbor)=subgraph
                    # Here, f(X)=X\{v}\cup{u}, where v is the smallest vertex_id and u the largest vertex_id such that
                    #   f(X) is connected (we have to check each possibility to get f(X)...)

                    f_subgraph = subgraph[:]
                    # so check for increasing vertex if its removal and adding another vertex obtains f(neighbor)
                    for vert_r in subgraph:
                        time_now = time()
                        if time_now > time_max:
                            time_difference = time_now - start_time
                            if time_difference > max_delay:
                                max_delay = time_difference
                            return "no search tree", numb_size_k, max_delay
                        f_subgraph.remove(vert_r)
                        # get the connected components of the "new reduced" graph
                        u_V = union_find(f_subgraph)
                        for i in range(reduced_size):
                            time_now = time()
                            if time_now > time_max:
                                time_difference = time_now - start_time
                                if time_difference > max_delay:
                                    max_delay = time_difference
                                return "no search tree", numb_size_k, max_delay
                            vertex1 = f_subgraph[i]
                            for j in range(i + 1, reduced_size):
                                vertex2 = f_subgraph[j]
                                if graph.are_connected(vertex1, vertex2):
                                    u_V.union(vertex1, vertex2)
                        coms_sub2 = u_V.components()

                        # determine common neighborhood of the "new reduced" subgraph
                        check2 = False
                        for i in range(len(coms_sub2)):
                            time_now = time()
                            if time_now > time_max:
                                time_difference = time_now - start_time
                                if time_difference > max_delay:
                                    max_delay = time_difference
                                return "no search tree", numb_size_k, max_delay
                            neighbors_compo2 = set()
                            for vertex_compo2 in coms_sub2[i]:
                                for neig2 in graph.neighbors(vertex_compo2):
                                    # no break, since we search the vertex with highest index
                                    # only put vertices in this set which have higher index than the removed vertex
                                    if neig2 not in f_subgraph and neig2 > vert_r:
                                        neighbors_compo2.add(neig2)
                            if check2 == True:
                                neighs_f.intersection_update(neighbors_compo2)
                            else:
                                neighs_f = neighbors_compo2
                                check2 = True
                            # stopping criterion: if pos_neighs set is empty, then no vertex is connected with each component
                            if len(neighs_f) == 0:
                                break
                        # take maximal element in this list and check if we get the initial subgraph
                        if len(neighs_f) > 0:
                            if vert_r == neig and max(neighs_f) == vertex:
                                subgraph_queue.put(subgraph[:])
                            break
                        # f_subgraph must not be sorted
                        f_subgraph.append(vert_r)
                    # afterwards remove the new added neighbors of neig from the possible neighbor set
                    subgraph.remove(neig)
                # this enumeration step ended, hence insert the deleted vertex in the ordered list
                bisect.insort(subgraph, vertex)
    return "no search tree", numb_size_k, max_delay


# the old version of this algorithm with the delay by elbassoni
# delay algorithm based on reversed search
def reverse_old(graph, k, time_max, subgraph_file, start_time, start_subs):
    """RwP Old
    Reverse with Predecessor without improved calculating of common neighborhood
    Finds all subgraphs of a graph G with size exactly k which are connected. The algorithm was introduced in the
    paper: A Polynomial Delay Algorithm for Generating Connected Induced Subgraphs of a Given Cardinality.
    This algorithm uses the reverse search method.

    Input:
    graph: Is the (i)graph.
    k: Is the parameter for the size of each connected subgraph.
    time_max: iIs the maximal time the algorithm can run for this instance.
    subgraph_file: Is the file name where the vertex names of each connected subgraph of size k are saved.
    start_time: Is the time when the last size k subgraph was enumerated.
    start_vertices: This list stores the start vertices of each component with at least k vertices.

    Output:
    nodes: Are the number of search tree nodes.
    numb_size_k: Are the number of enumerated size k subgraphs.
    max_delay: Is the maximal time which goes by by the enumeration of two size k subgraphs."""
    max_delay = 0
    reduced_size = k - 1
    numb_size_k = 0
    # run the enumeration algorithm for each connected component with at least k vertices
    for component in start_subs:
        # save all size-k subgraphs we still have to work on in a queue (to get rid of recursion)
        subgraph_queue = queue.Queue()
        subgraph_queue.put(component)
        while subgraph_queue.empty() == False:
            numb_size_k += 1
            time_now = time()
            if time_now > time_max:
                time_difference = time_now - start_time
                if time_difference > max_delay:
                    max_delay = time_difference
                break
            time_difference = time_now - start_time
            if time_difference > max_delay:
                max_delay = time_difference
            start_time = time_now
            subgraph = subgraph_queue.get()
            # output this subgraph
            subgraph_file.write(print_names(graph, subgraph))

            subgraph_co = subgraph[:]
            # subsequently remove each vertex from the subgraph to get new size-k subgraphs
            for vertex in subgraph_co:
                time_now = time()
                if time_now > time_max:
                    time_difference = time_now - start_time
                    if time_difference > max_delay:
                        max_delay = time_difference
                    return "no search tree", numb_size_k, max_delay
                subgraph.remove(vertex)
                # determine the connected components of the components of the "reduced" graph
                U = union_find(subgraph)
                for i in range(reduced_size):
                    vertex1 = subgraph[i]
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", numb_size_k, max_delay
                    for j in range(i + 1, reduced_size):
                        vertex2 = subgraph[j]
                        if graph.are_connected(vertex1, vertex2):
                            U.union(vertex1, vertex2)
                coms_sub = U.components()

                # now determine the common neighborhood of all connected components
                # we first determine its neighborhood, and then we try to find the predecessor, since for this we need N[subgraph]
                pos_neighbors = set()
                sorted_pos_neighbors = set()
                for v in subgraph:
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", numb_size_k, max_delay
                    for neig in graph.neighbors(v):
                        # the new subgraph is lexicographically larger, hence neig>vertex holds
                        if neig > vertex:
                            sorted_pos_neighbors.add(neig)
                            continue
                        if neig not in subgraph_co:
                            pos_neighbors.add(neig)
                sorted_pos_neighbors.add(vertex)
                sorted_pos_neighbors.update(pos_neighbors)
                sorted_pos_neighbors = sorted(sorted_pos_neighbors,
                                              reverse=True)
                # put the deleted vertex also in the set of possible vertices to find the predecessor

                # now check for each possible neighbor if the resulting subgraph is connected
                for neig in pos_neighbors:
                    time_now = time()
                    if time_now > time_max:
                        time_difference = time_now - start_time
                        if time_difference > max_delay:
                            max_delay = time_difference
                        return "no search tree", numb_size_k, max_delay
                    conn = True
                    for i in range(len(coms_sub)):
                        check = False
                        time_now = time()
                        if time_now > time_max:
                            time_difference = time_now - start_time
                            if time_difference > max_delay:
                                max_delay = time_difference
                            return "no search tree", numb_size_k, max_delay
                        for vertex_compo in coms_sub[i]:
                            if graph.are_connected(vertex_compo, neig):
                                check = True
                                break
                        if check == False:
                            conn = False
                            break
                    # only go further if the graph is connected, in this case we found a new candidate
                    if conn == False:
                        continue

                    # in a next step add all its neighbors to the set of candidates for vert_a, afterwards delete them
                    to_delete = set()
                    for neig2 in graph.neighbors(neig):
                        if neig2 not in pos_neighbors:
                            to_delete.add(neig2)
                            insort_decreasing_list(sorted_pos_neighbors, neig2)

                    bisect.insort(subgraph, neig)

                    # now determine the predecessor of this size-k subgraph
                    f_subgraph = subgraph[:]
                    found = False
                    for vert_r in subgraph:
                        time_now = time()
                        if time_now > time_max:
                            time_difference = time_now - start_time
                            if time_difference > max_delay:
                                max_delay = time_difference
                            return "no search tree", numb_size_k, max_delay
                        if found == True:
                            break
                        # remove this vertex and determine the associated connected components
                        f_subgraph.remove(vert_r)
                        # get the connected components of the "new reduced" graph
                        u_V = union_find(f_subgraph)
                        for i in range(reduced_size):
                            time_now = time()
                            if time_now > time_max:
                                time_difference = time_now - start_time
                                if time_difference > max_delay:
                                    max_delay = time_difference
                                return "no search tree", numb_size_k, max_delay
                            vertex1 = f_subgraph[i]
                            for j in range(i + 1, reduced_size):
                                vertex2 = f_subgraph[j]
                                if graph.are_connected(vertex1, vertex2):
                                    u_V.union(vertex1, vertex2)
                        coms_sub2 = u_V.components()

                        # now try to add a vertex with high index such that the resulting size-k subgraph is connected
                        for vert_a in sorted_pos_neighbors:
                            time_now = time()
                            if time_now > time_max:
                                time_difference = time_now - start_time
                                if time_difference > max_delay:
                                    max_delay = time_difference
                                return "no search tree", numb_size_k, max_delay
                            # only try to add this vertex if its index is high enough
                            if vert_a <= vert_r:
                                break
                            if vert_a in subgraph:
                                continue

                            # otherwise check if this vertex is connected which each connected component
                            conn = True
                            for i in range(len(coms_sub2)):
                                time_now = time()
                                if time_now > time_max:
                                    time_difference = time_now - start_time
                                    if time_difference > max_delay:
                                        max_delay = time_difference
                                    return "no search tree", numb_size_k, max_delay
                                check = False
                                for vertex_compo in coms_sub2[i]:
                                    if graph.are_connected(
                                            vertex_compo, vert_a):
                                        check = True
                                        break
                                if check == False:
                                    conn = False
                                    break

                            # only go further if the graph is connected, in this case we found the predecessor
                            if conn == False:
                                continue
                            found = True
                            # now check if this predecessor is equal with the initial size-k subgraph
                            if vert_r == neig and vert_a == vertex:
                                subgraph_queue.put(subgraph[:])
                            break
                        # f_subgraph must not be sorted
                        f_subgraph.append(vert_r)
                    # afterwards remove the new neighbors of neig from the possible neighbor set
                    subgraph.remove(neig)
                    # also delete the new vertices from the set of sorted vertices
                    for vert_remove in to_delete:
                        sorted_pos_neighbors.remove(vert_remove)
                # this enumeration step ended, hence insert the deleted vertex in the ordered list
                bisect.insort(subgraph, vertex)
    return "no search tree", numb_size_k, max_delay


# insert elements in decreasing list
def insort_decreasing_list(a, x, lo=0, hi=None):
    """Insert item x in list a, and keep it reverse-sorted assuming a
    is reverse-sorted.

    If x is already in a, insert it to the right of the rightmost x.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.
    """
    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if x > a[mid]: hi = mid
        else: lo = mid + 1
    a.insert(lo, x)


# dictionary to choose the enumeration algorithm
enumartion_function = {
    'pivot-return': pivot_subgraphs_return,
    'pivot-improved': pivot_subgraphs_improved,
    'pivot-old': pivot_subgraphs_old,
    'exgen-return': enu_all_subgraphs_return,
    'exgen-old': enu_all_subgraphs_old,
    'simple-return': simple_enumeration_return,
    'simple-old': simple_enumeration_old,
    'bdde': bdde,
    'kavosh-return': kavosh_return,
    'kavosh-old': kavosh_old,
    'delay-new': delay_new,
    'delay-old': delay_old,
    'reverse-new': reverse_new,
    'reverse-old': reverse_old
}
