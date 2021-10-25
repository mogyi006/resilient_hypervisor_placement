# from igraph import *
import src.data.enucon.read_data_white as read
import src.data.enucon.enumerate_subgraphs as enu
import src.data.enucon.sort_vertices as sortv
from time import time
import argparse
import sys
sys.setrecursionlimit(10000000)

# NETWORK_NAME="50_germany"; for i in {2..5}; do python enucon.py simple-return 120 ${i} ../../../data/processed/networks/txt_format/${NETWORK_NAME}.txt ../../../data/processed/requests/${NETWORK_NAME}/; done

# first input is the name of the algorithm
# second input is the time limit for each instance
# the third input is the parameter
# the fourth input is a file which contains all data sets and the according parameter k
# the fifth input is a path to a directory where the output is saved
parser = argparse.ArgumentParser(
    description='Enucon: Enumerate all size k subgraphs.')
parser.add_argument(
    "algo",
    type=str,
    help=
    'decides which enumeration algorithm is used, options: bdde, delay-new, delay-old, exgen-old, exgen-return, kavosh-old, kavosh-return, pivot-improved, pivot-old, pivot-return, reverse-new, reverse-old, simple-old, simple-return. Here -old is the variant from the literature, - improved the variant with a smaller numbre of search tree nodes, -return the varaint with the break condition, and -new is the variant with the improved delay.'
)
parser.add_argument('timelimit',
                    type=int,
                    help='time limit in seconds for each instance')
parser.add_argument('parameter',
                    type=int,
                    help='parameter k for size of the subgraphs')
parser.add_argument(
    'graph_file',
    type=str,
    help='graph file in which we want to enumerate all size k subgraphs')
parser.add_argument('folder',
                    type=str,
                    help='path to folder where result files are stored')
parser.add_argument(
    '--inverse',
    default=False,
    type=bool,
    help=
    'If this value is True, the parameter k is the order of the biggest connected component minus the input parameter'
)
args = parser.parse_args()

# load file and built graph
graph_file = open(args.graph_file.rstrip())
name = str(args.graph_file).split('/')[-1]
graph = read.read_data(graph_file)
# simplify graph, that is: remove self-loops and multiple edges
graph.simplify()

# if the parameter is order_of_biggest_component minus input parameter (so inverse=True)
if args.inverse:
    # determine connected components of G and determine the order l of the biggest
    # afterwards determine new parameter
    compos = graph.components()
    args.parameter = max(compos.sizes()) - args.parameter

# if polynomial delay algorithm is chosen, the vertices have to be sorted according to a DFS search tree
# sort vertices (we have to sort if delay-algo is chosen)
components = []
if args.algo == "delay-new" or args.algo == "delay-old" or args.algo == "reverse-new" or args.algo == "reverse-old":
    graph, components = sortv.sort_vertices(graph, 0, args.parameter)
graph_file.close()
# write results in result file
out_line = (name.rjust(30) + str(graph.vcount()).rjust(9) +
            str(graph.ecount()).rjust(11) + str(args.parameter).rjust(10))

# experiments
# file that stores the vertices of each size k subgraph
filename = str(args.folder) + "/" + str(name)[:-4] + "." + str(
    args.parameter) + ".subgraphs"
subgraph_file = open(filename, 'w+')
# log file that stores algorithm specific information
filename_log = str(args.folder) + "/" + str(name) + "." + str(
    args.parameter) + ".log"
log_file = open(filename_log, 'w+')
try:
    start_time = time()
    # choose evaluation algorithm from dictionary of parameters\
    # maximal time is start time + time limit
    # also start time is a parameter to obtain the maximal delay time to enumerate two size k subgraphs
    # max_delay is 0 at start
    nodes, numb_size_k, max_delay = enu.enumartion_function[args.algo](
        graph, args.parameter, start_time + args.timelimit, subgraph_file,
        start_time, components)
    end_time = time()
    subgraph_file.close()
    out_line += (str(round(end_time - start_time, 3)).rjust(15) +
                 str(nodes).rjust(20) + str(numb_size_k).rjust(20) +
                 str(round(max_delay, 3)).rjust(15))
except MemoryError:
    log_file.write("Not enough memory" + "\n")
log_file.write(str(out_line) + "\n")
log_file.close()
