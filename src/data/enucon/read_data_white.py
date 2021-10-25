from igraph import Graph


def read_data(file):
    """Reads a data file in the following form: Lines starting with # or % are command lines and hence ignored.
    Each line consists of exactly two entries separated by blanks. Both entries are the vertex names
    of an edge.
    The function returns a (i)graph consisting of the edges of the inputfile."""
    graph = Graph()
    names = set()
    name_2_id = dict()
    edges = []
    graph.vs["name"] = []

    # read graph line-wise
    for line in file:
        if line.startswith('%') or line.startswith('#'): continue
        # get the two (or three) entries of a line
        entries = line.split()
        # check if there is a new vertex
        for i in range(2):
            vertex = entries[i]
            if vertex not in names:
                graph.add_vertex()
                name_2_id[vertex] = graph.vcount() - 1
                graph.vs[graph.vcount() - 1]["name"] = vertex
                names.add(vertex)

        # add the new edge
        edges += [(name_2_id[entries[0]], name_2_id[entries[1]])]

    graph.add_edges(edges)
    return graph
