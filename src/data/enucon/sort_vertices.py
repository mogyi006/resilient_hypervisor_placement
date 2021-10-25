from igraph import Graph


def sort_vertices(graph, ordering, k=0):
    """Returns a (i)graph where the vertices are sorted increasing or decreasing according to their degree OR they are
    sorted concerning a DFS search tree.
    The input is also an (i)graph.
    graph: Is the (i)graph.
    ordering: If this number is 0, then the ordering is concerning a DFS search tree,
                                1, then the ordering is increasing,
                                otherwise, then the ordering is decreasing.
    k: This is the size of each subgraph we want to enumerate. This parameter is only necessary for ordering=0.

    The first output is the new graph.
    The second output is a list of the start subgraphs of size k of components with at least k vertices.
    This list is only non-empty if the ordering is 0 (DFS-search tree)."""
    list_compo = []
    if ordering == 0:
        # "inverse DFS-ordering" This means we start with vertex ID graph.vcount() and decrease it to zero
        #    The advantage of this method is the neighbor function of igraph. Now by determining the neighborhood
        #    of a size k subgraph by deleting v we can break the loop over the neighbors if index(neighbor)>v
        dict_old_new = dict()
        sorted_vertex_names = []
        numb_vertices = graph.vcount()
        index = numb_vertices - 1
        visited = [0] * numb_vertices
        for vertex in range(numb_vertices):
            # do not start a DFS search from a visited vertex
            if visited[vertex] == 1:
                continue
            component = set()
            stack = [vertex]
            # new smallest ID of the vertex in this component
            smallest = numb_vertices - len(sorted_vertex_names)
            while stack:
                element = stack.pop()
                if element not in component:
                    component.add(element)
                    dict_old_new.update({element: index})
                    index -= 1
                    for neighbor in graph.neighbors(element):
                        if neighbor not in component:
                            stack.append(neighbor)
                    visited[element] = 1
                    sorted_vertex_names.insert(0, graph.vs[element]["name"])
                    if len(component) == k:
                        # we have to invert the vertex IDs to obtain above properties
                        list_compo.append(range(smallest - k, smallest))
    else:
        deg = []
        names = []
        # get vertex names
        for i in range(graph.vcount()):
            deg.append(graph.vs[i].degree())
            names.append(graph.vs[i]["name"])
            # now order vertex names according to degree
        if ordering == 1:
            sorted_vertex_names = [el for _, el in sorted(zip(deg, names))]
        else:
            sorted_vertex_names = [
                el for _, el in sorted(zip(deg, names), reverse=True)
            ]
    # create a new graph with the new ordering
    new_g = Graph()
    new_g.add_vertices(graph.vcount())
    new_g.vs["name"] = sorted_vertex_names
    new_edges = []
    for edge in graph.es:
        e_t = graph.vs[edge.target]["name"]
        e_s = graph.vs[edge.source]["name"]
        new_edges += [(new_g.vs.find(name=e_t), new_g.vs.find(name=e_s))]
    new_g.add_edges(new_edges)
    return new_g, list_compo
