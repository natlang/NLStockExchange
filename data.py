import os
import sys

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import networkx as nx

####################- Trading Data -####################


# Find equilibrium price (theoretical + actual) from trader limits and prices
# Update price_hist for each trader too
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
                            price = (sp[q - 1] + bp[q - 1]) * 0.5
                            quant = q
                            found = True
                        else:
                            # last buyer, last seller
                            if (q + 1 == bnum) and (q + 1 == snum):
                                price = (sp[q] + bp[q]) * 0.5
                                quant = q + 1
                                found = True
                            elif q + 1 == bnum:
                                price = (sp[q] + sp[q + 1]) * 0.5
                                quant = q + 1
                                found = True
                            elif q + 1 == snum:
                                price = (bp[q] + bp[q + 1]) * 0.5
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
        # Add price to price_hist for each trader
        traders[bname].update_price_hist()
        if traders[bname].active:
            b_price.append(traders[bname].price)
            b_limit.append(traders[bname].limit)
            n_buyers += 1

        sname = 'S%02d' % t
        # Add price to price_hist for each trader
        traders[sname].update_price_hist()
        if traders[sname].active:
            s_price.append(traders[sname].price)
            s_limit.append(traders[sname].limit)
            n_sellers += 1

    b_price.sort(reverse=True)
    s_price.sort()
    b_limit.sort(reverse=True)
    s_limit.sort()

    # Find actual equilibrium from trade limit prices
    aeq_p, aeq_q = find_intersect(b_price, n_buyers, s_price, n_sellers)
    # Find theoretical equilibrium from trade limit prices
    teq_p, teq_q = find_intersect(b_limit, n_buyers, s_limit, n_sellers)

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

####################- End of Trading Data -####################
####################- Day Data -####################


# Initialise day data df with class instantiation
def init_ddat(interval):
    df = pd.DataFrame(columns=['trialID', 'day', 'TEQ_P', 'AEQ_P', 'Transaction'])
    ddat = DayData(df, interval)
    return ddat


class DayData:
    def __init__(self, df, interval):
        self.df = df
        self.interval = interval
        self.current_day = 0
        self.teq_p = None
        self.aeq_p = None
        self.transaction = None

    def update_ddat(self, trial, time, traders, n_traders, eq, trade, ndat):
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
            self.end_day(trial, traders, n_traders, ndat, next_day)
            self.init_day()

        self.teq_p = update_arr(self.teq_p, eq[0])
        self.aeq_p = update_arr(self.aeq_p, eq[2])
        self.transaction = update_arr(self.transaction, trade)

    def end_day(self, trial, traders, n_traders, ndat, next_day):
        def calc_mean(arr):
            mean = np.nan
            if arr is not None:
                mean = np.mean(arr)
            return mean

        # Calculate Smith's alpha based on price history
        def calc_alpha(eq, arr):
            if arr:
                num = len(arr)
                sum_sqrd = sum(map(lambda x: (x - eq) ** 2, arr))
                a = (1.0 / eq) * math.sqrt((1.0 / num) * sum_sqrd)
            else:
                a = 0.0
            return a

        # Calculate best possible alpha value
        def calc_best_alpha(eq, limit, job):
            if limit:
                if job == 'Buy' and limit < teq:
                    a = (1.0 / teq) * abs(limit - eq)
                elif job == 'Sell' and limit > teq:
                    a = (1.0 / teq) * abs(limit - eq)
                else:
                    a = 0.0
            else:
                a = 1.0
            return a

        # For each trader, calc Smith's alpha using price history and teq as equilibrium
        teq = calc_mean(self.teq_p)
        aeq = calc_mean(self.aeq_p)
        for n in range(n_traders):
            bname = 'B%02d' % n
            alpha = calc_alpha(teq, traders[bname].price_hist)
            best_alpha = calc_best_alpha(teq, traders[bname].limit, 'Buy')
            update_ndat(ndat, bname, trial, self.current_day, alpha, best_alpha)
            traders[bname].reset_price_hist()

            sname = 'S%02d' % n
            alpha = calc_alpha(teq, traders[sname].price_hist)
            best_alpha = calc_best_alpha(teq, traders[sname].limit, 'Sell')
            update_ndat(ndat, sname, trial, self.current_day, alpha, best_alpha)
            traders[sname].reset_price_hist()

        # Write previous days data to structure containing data for *all* days in trial
        ddat = {'trialID': trial,
                'day': self.current_day,
                'TEQ_P': teq,
                'AEQ_P': aeq,
                'Transaction': calc_mean(self.transaction)}
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
####################- Network Data -####################


# Initialise network data classes
def init_ndat(traders_spec, n_days):
    n_traders = sum(n for _, n in traders_spec)
    ndat_alpha = {}
    ndat_best = {}
    for n in range(n_traders):
        bname = 'B%02d' % n
        ndat_alpha[bname] = np.zeros(n_days)
        ndat_best[bname] = np.ones(n_days)
        sname = 'S%02d' % n
        ndat_alpha[sname] = np.zeros(n_days)
        ndat_best[sname] = np.ones(n_days)
    ndat = {'alpha': ndat_alpha, 'best': ndat_best}

    return ndat


def update_ndat(ndat, tname, trial, current_day, alpha, best_alpha):
    old_mean = ndat['alpha'][tname][current_day]
    new_mean = (((trial - 1) * old_mean) + alpha) / trial
    ndat['alpha'][tname][current_day] = new_mean
    ndat['best'][tname][current_day] = best_alpha


def get_ndat_df(ndat, n_days, graph):
    df_alpha = pd.DataFrame.from_dict(ndat['alpha'], orient='index').reset_index()
    df_best = pd.DataFrame.from_dict(ndat['best'], orient='index').reset_index()
    df = pd.merge(df_alpha, df_best, on='index')

    df.rename(columns={'index': 'tname'}, inplace=True)
    df.rename(columns=lambda x: x.replace('x', 'alpha'), inplace=True)
    df.rename(columns=lambda x: x.replace('y', 'best'), inplace=True)

    return df


def draw_network(ndat, n_days, buy_network, sell_network, zipfile):
    def draw_graph(graph, d, char, zip_file):
        colors = [graph.node[x]['alpha'] for x in graph.nodes()]
        d_dict = dict(nx.degree(graph))
        sizes = [v * 70 for v in d_dict.values()]
        labels = {}
        for node in graph.nodes:
            a = graph.node[node]['alpha']
            b = graph.node[node]['best']
            deg = d_dict[node]
            # labels[node] = t + '\n' + str(a)
            labels[node] = str(a) + '-' + str(b) + '\n\n' + str(deg)
            # labels[node] = str(graph.node[node]['alpha'])

        plt.figure(figsize=(12,9))
        pos = nx.circular_layout(graph, center=(0, 0))
        pos_higher = {}
        for k, v in pos.items():
            pos_higher[k] = (v[0], v[1] + 0.06)
        nx.draw_networkx_edges(graph, pos, alpha=0.2)
        network = nx.draw_networkx_nodes(graph, pos, node_size=sizes, node_color=colors, alpha=0.8, cmap=plt.cm.gist_rainbow_r, vmin=0.0, vmax=0.75)
        nx.draw_networkx_labels(graph, pos_higher, labels=labels, font_size=12)
        # cbar = plt.colorbar(network)
        # cbar.ax.tick_params(labelsize=18)
        plt.axis('off')
        filename = char + 'network' + str(d) + '.png'
        plt.savefig(filename, dpi=300)
        zip_file.write(filename)
        os.remove(filename)
        plt.clf()
        plt.close('all')

    for n in range(n_days):
        for tname in ndat['alpha'].keys():
            nodeid = int(tname[-2:])
            if tname[:1] == 'B':
                buy_network.node[nodeid]['alpha'] = float("{0:.3f}".format(ndat['alpha'][tname][n]))
                buy_network.node[nodeid]['best'] = float("{0:.3f}".format(ndat['best'][tname][n]))
            elif tname[:1] == 'S':
                sell_network.node[nodeid]['alpha'] = float("{0:.3f}".format(ndat['alpha'][tname][n]))
                sell_network.node[nodeid]['best'] = float("{0:.3f}".format(ndat['best'][tname][n]))
            else:
                sys.exit('FATAL tname %s is not in correct format.' % tname)

        draw_graph(buy_network, n, 'B', zipfile)
        draw_graph(sell_network, n, 'S', zipfile)


# Write network data adjaceny matrix
def write_adj_matrix(zipfile, network):
    nx.write_adjlist(network, 'network.txt')
    zipfile.write('network.txt')
    os.remove('network.txt')

####################- End of Network Data -####################