import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import networkx as nx


def draw_graph(graph, day, char):
    colors = [graph.node[n]['alpha'] for n in graph.nodes()]
    labels = {}
    for node in graph.nodes:
        tname = graph.node[node]['tname']
        alpha = graph.node[node]['alpha']
        labels[node] = [tname, alpha]

    plt.figure(figsize=(10, 8))
    pos = nx.circular_layout(graph)
    pos_higher = {}
    for k, v in pos.items():
        pos_higher[k] = (v[0], v[1] + 0.15)
    ec = nx.draw_networkx_edges(graph, pos, alpha=0.2)
    nc = nx.draw_networkx_nodes(graph, pos, node_size=1000, node_color=colors, cmap=plt.cm.gist_rainbow, vmin=0.0, vmax=0.8)
    la = nx.draw_networkx_labels(graph, pos_higher, labels=labels)
    plt.colorbar(nc)
    plt.axis('off')
    plt.savefig(char + 'network' + str(day) + '.png', dpi=100) # TODO: change these
    plt.clf()
    plt.close('all')


####################- Trading Data -####################


# Find equilibrium price (theoretical + actual) from trader limits and prices
def find_eq(traders, n_traders):
    def find_intersect(bp, bnum, sp, snum):
        max_q = max(bnum, snum)

        # no active buyers or active sellers
        if bnum == 0 or snum == 0:
            price = np.nan
            quant = np.nan
        else:
            # lowest selling price > highest buying price -> no intersection
            if sp[0] > bp[0]:
                price = np.nan
                quant = np.nan
            # find intersection
            else:
                found = False
                for q in range(max_q):
                    if not found:
                        # straightforward intersection
                        if sp[q] > bp[q]:
                            price = (sp[q - 1] + bp[q - 1]) / 2.0
                            quant = q
                            found = True
                        else:
                            # last buyer, last seller
                            if (q + 1 == bnum) and (q + 1 == snum):
                                price = (sp[q] + bp[q]) / 2.0
                                quant = q + 1
                                found = True
                            elif q + 1 == bnum:
                                price = (sp[q] + sp[q + 1]) / 2.0
                                quant = q + 1
                                found = True
                            elif q + 1 == snum:
                                price = (bp[q] + bp[q + 1]) / 2.0
                                quant = q + 1
                                found = True

        return price, quant

    n_buyers = 0
    b_price = []
    b_limit = []

    n_sellers = 0
    s_price = []
    s_limit = []
    for t in range(n_traders):
        bname = 'B%02d' % t
        traders[bname].update_price_hist()
        if traders[bname].active:
            b_price.append(traders[bname].price)
            b_limit.append(traders[bname].limit)
            n_buyers += 1

        sname = 'S%02d' % t
        traders[sname].update_price_hist()
        if traders[sname].active:
            s_price.append(traders[sname].price)
            s_limit.append(traders[sname].limit)
            n_sellers += 1

    b_price.sort(reverse=True)
    s_price.sort()
    b_limit.sort(reverse=True)
    s_limit.sort()

    teq_p, teq_q = find_intersect(b_limit, n_buyers, s_limit, n_sellers)
    aeq_p, aeq_q = find_intersect(b_price, n_buyers, s_price, n_sellers)

    eq = [teq_p, teq_q, aeq_p, aeq_q]
    return eq


# Initialise trading data df
def init_tdat():
    df = pd.DataFrame(columns=['trialID', 'time', 'TEQ_P', 'TEQ_Q', 'AEQ_P', 'AEQ_Q', 'Transaction'])
    return df


# Update trading df with data (equilibrium prices + quantities, transaction price)
def update_tdat(tdat_df, trial, time, eq, trade):
    tdat = {'trialID': trial,
            'time': time,
            'TEQ_P': eq[0],
            'TEQ_Q': eq[1],
            'AEQ_P': eq[2],
            'AEQ_Q': eq[3],
            'Transaction': trade}
    tdat_df = tdat_df.append(tdat, ignore_index=True)
    return tdat_df


# Initialise day data df with class instantiation
def init_ddat(interval, buy_network, sell_network):
    df = pd.DataFrame(columns=['trialID', 'day', 'TEQ_P', 'AEQ_P', 'Transaction'])
    ddat = DayData(df, interval, buy_network, sell_network)
    return ddat

####################- End of Trading Data -####################
####################- Day Data -####################

class DayData:
    def __init__(self, df, interval, buy_network, sell_network):
        self.df = df
        self.interval = interval
        self.current_day = 0
        self.teq_p = None
        self.aeq_p = None
        self.transaction = None
        self.buy_network = buy_network
        self.sell_network = sell_network

    def update_ddat(self, trial, time, traders, n_traders, eq, trade):
        def update_arr(arr, value):
            if not np.isnan(value):
                if arr is None:
                    new_arr = np.array(value)
                else:
                    new_arr = np.append(arr, value)
            else:
                new_arr = arr
            return new_arr

        next_day = self.current_day + 1
        if time > (self.interval * next_day):
            self.end_day(trial, traders, n_traders, next_day)
            self.init_day()

        self.teq_p = update_arr(self.teq_p, eq[0])
        self.aeq_p = update_arr(self.aeq_p, eq[2])
        self.transaction = update_arr(self.transaction, trade)

    def end_day(self, trial, traders, n_traders, next_day):
        def find_mean(arr):
            mean = np.nan
            if arr is not None:
                mean = np.mean(arr)
            return mean

        def find_alpha(eq, arr):
            if arr:
                num = len(arr)
                sum_sqrd = sum(map(lambda x: (eq - x) ** 2, arr))
                a = (1.0 / eq) * math.sqrt((1.0 / num) * sum_sqrd)
            else:
                a = 1.0 # TODO: change this to a more reasonable value
            return a

        def update_alpha(network, nodeid, a):
            network.node[nodeid]['alpha'] = float("{0:.3f}".format(a))

        # For each trader, calc Smith's alpha using price history and teq as equilibrium
        teq = find_mean(self.teq_p)
        for n in range(n_traders):
            bname = 'B%02d' % n
            alpha = find_alpha(teq, traders[bname].price_hist)
            update_alpha(self.buy_network, traders[bname].nodeid, alpha)
            traders[bname].reset_price_hist()

            sname = 'S%02d' % n
            alpha = find_alpha(teq, traders[sname].price_hist)
            update_alpha(self.sell_network, traders[sname].nodeid, alpha)
            traders[sname].reset_price_hist()

        # Write graph to file
        draw_graph(self.buy_network, self.current_day, 'b')
        draw_graph(self.sell_network, self.current_day, 's')

        # Write previous days data to structure containing data for *all* days in trial
        ddat = {'trialID': trial,
                'day': self.current_day,
                'TEQ_P': teq,
                'AEQ_P': find_mean(self.aeq_p),
                'Transaction': find_mean(self.transaction)}
        ddat_df = self.df.append(ddat, ignore_index=True)
        self.df = ddat_df

        self.current_day = next_day

    def init_day(self):
        self.teq_p = None
        self.aeq_p = None
        self.transaction = None

    def get_df(self):
        return self.df

####################- End of Day Data -####################
