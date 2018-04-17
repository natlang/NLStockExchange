import pandas as pd
import numpy as np
from collections import defaultdict


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
        if traders[bname].active:
            b_price.append(traders[bname].price)
            b_limit.append(traders[bname].limit)
            n_buyers += 1

        sname = 'S%02d' % t
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

    def update_ddat(self, trial, time, eq, trade):
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
            self.end_day(trial, next_day)
            self.init_day()

        self.teq_p = update_arr(self.teq_p, eq[0])
        self.aeq_p = update_arr(self.aeq_p, eq[2])
        self.transaction = update_arr(self.transaction, trade)

    def end_day(self, trial, next_day):
        def find_mean(arr):
            mean = np.nan
            if arr is not None:
                mean = np.mean(arr)
            return mean
        # Write previous days data to structure containing data for *all* days in trial
        ddat = {'trialID': trial,
                'day': self.current_day,
                'TEQ_P': find_mean(self.teq_p),
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

