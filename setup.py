import random
import sys
import networkx as nx

from agentZIP import AgentZIP
from agentZIC import AgentZIC


# Build graph of traders, identical graphs for seller and buyer communities
def build_network(traders_spec, network):
    # n_traders equal to number of each trader type (buyers OR sellers), half of total number of traders
    n_traders = sum(n for _, n in traders_spec)

    if network[0] == 'FC':
        buyers_network = nx.complete_graph(n_traders)
    elif network[0] == 'Random':
        buyers_network = nx.fast_gnp_random_graph(n_traders, network[1])
    elif network[0] == 'SW':
        buyers_network = nx.watts_strogatz_graph(n_traders, network[2], network[1])
    elif network[0] == 'SF':
        buyers_network = nx.barabasi_albert_graph(n_traders, network[2])
    else:
        sys.exit('FATAL: don\'t know robot type %s\n' % network)

    sellers_network = buyers_network.copy()
    return n_traders, buyers_network, sellers_network


def initialise_agent(ttype, tname, node_id, job):
    if ttype == 'ZIP':
        if job == 'Buy':
            margin = -0.01 * random.randrange(5, 36)
            return AgentZIP('ZIP', tname, node_id, job, margin)
        else:
            margin = 0.01 * random.randrange(5, 36)
            return AgentZIP('ZIP', tname, node_id, job, margin)
    elif ttype == 'ZIC':
        return AgentZIC('ZIC', tname, node_id, job)
    else:
        sys.exit('FATAL: agent type %s does not exit %s\n' % ttype)


def populate_market(traders_spec, traders, buyers_network, sellers_network, verbose):
    # Initialise buyers
    n_buyers = 0
    for ts in traders_spec:
        ttype = ts[0]
        for i in range(ts[1]):
            tname = 'B%02d' % n_buyers  # Set buyer ID string
            traders[tname] = initialise_agent(ttype, tname, n_buyers, 'Buy')
            buyers_network.node[n_buyers]['tname'] = tname
            buyers_network.node[n_buyers]['alpha'] = 0
            n_buyers += 1

    if n_buyers < 1:
        sys.exit('FATAL: no buyers specified\n')

    if verbose:
        for n in range(n_buyers):
            bname = 'B%02d' % n
            print(traders[bname])

    # Initialise sellers
    n_sellers = 0
    for ts in traders_spec:
        ttype = ts[0]
        for i in range(ts[1]):
            tname = 'S%02d' % n_sellers  # Set seller ID string
            traders[tname] = initialise_agent(ttype, tname, n_sellers, 'Sell')
            sellers_network.node[n_sellers]['tname'] = tname
            sellers_network.node[n_sellers]['alpha'] = 0
            n_sellers += 1

    if n_sellers < 1:
        sys.exit('FATAL: no sellers specified\n')

    if verbose:
        for n in range(n_sellers):
            sname = 'S%02d' % n
            print(traders[sname])

    # return buyers_network, sellers_network
