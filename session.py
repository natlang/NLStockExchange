import sys
import random
import numpy as np

import config
import data
from order import Order


def customer_orders(time, traders, n_traders, order_sched, pending, verbose):
    def get_issue_times(num_traders, timemode, interval, fit_to_interval, shuffle):
        interval = float(interval)

        if num_traders < 1:
            sys.exit('FATAL: n_traders < 1 in get_issue_times() in customer_orders()')
        elif num_traders == 1:
            timestep = interval
        else:
            timestep = interval / (num_traders - 1)

        times = []
        arrival_time = 0

        for n in range(num_traders):
            if timemode == 'periodic':
                arrival_time = interval
            elif timemode == 'drip-fixed':
                arrival_time = n * timestep
            elif timemode == 'drip-jitter':
                arrival_time = n * timestep + timestep * random.random()
            elif timemode == 'drip-poisson':
                inter_arrival_time = random.expovariate(num_traders / interval)
                arrival_time += inter_arrival_time
            else:
                sys.exit('FATAL: unknown timemode in get_issue_times()')
            times.append(arrival_time)

        # At this point, arrival_time is the last arrival time
        if fit_to_interval and ((arrival_time > interval) or (arrival_time < interval)):
            # Generate sum of inter-arrival times
            # If longer than interval, squash back together so last arrival falls at t=interval
            for n in range(num_traders):
                times[n] = interval * (times[n] / arrival_time)

        # Optionally shuffle issue times
        if shuffle:
            for n in range(num_traders):
                i = (num_traders - 1) - n
                j = random.randint(0, i)
                tmp = times[i]
                times[i] = times[j]
                times[j] = tmp

        return times

    def get_sched_mode(current_time, o_sched):
        got_one = False
        for sched in o_sched:
            if (sched['from'] <= current_time) and (current_time < sched['to']):
                # within timezone for this schedule
                s_range = sched['ranges']
                s_mode = sched['stepmode']
                got_one = True  # jump out loop - first matching timezone has priority
                break
        if not got_one:
            sys.exit('FATAL: time = %5.2f not within any time in order_sched = %s' % (current_time, o_sched))

        return s_range, s_mode

    def get_order_price(trader, s_range, num_traders, s_mode):
        def sysmin_check(p):
            if p < config.MIN_PRICE:
                print('WARNING: price < MIN_PRICE')
                p = config.MIN_PRICE
            return p

        def sysmax_check(p):
            if p > config.MAX_PRICE:
                print('WARNING: price < MAX_PRICE')
                p = config.MAX_PRICE
            return p

        # # First schedule range includes optional dynamic offset function(s)
        # if len(s_range[0]) > 2:
        #     offset_fn = s_range[0][2]
        #     if callable(offset_fn):
        #         # Same offset for min and max
        #         offset_min = offset_fn(i_time)
        #         offset_max = offset_min
        #     else:
        #         sys.exit('FATAL: 3rd argument of sched in get_order_price() not callable')
        #     if len(s_range[0]) > 3:
        #         # If second offset function is specified, applies only to max value
        #         offset_fn = s_range[0][3]
        #         if callable(offset_fn):
        #             offset_max = offset_fn(i_time)
        #         else:
        #             sys.exit('FATAL: 4th argument of sched in get_order_price() not callable')
        # else:
        #     offset_min = 0.0
        #     offset_max = 0.0

        min_price = sysmin_check(min(s_range[0], s_range[1]))
        max_price = sysmax_check(max(s_range[0], s_range[1]))
        price_range = max_price - min_price
        step = price_range / (num_traders - 1)
        half_step = round(step / 2.0)

        if s_mode == 'fixed':
            price = min_price + int(trader * step)
        elif s_mode == 'jittered':
            price = min_price + int(trader * step) + random.randint(-half_step, half_step)
        # elif s_mode == 'random':
        #     # More than one schedule, choose one equiprobably
        #     if len(s_range) > 1:
        #         s = random.randint(0, len(s_range) - 1)
        #         min_price = sysmin_check(min(s_range[s][0], s_range[s][1]))
        #         max_price = sysmax_check(max(s_range[s][0], s_range[s][1]))
        #     price = random.randint(min_price, max_price)
        else:
            sys.exit('FATAL: Unknown mode in schedule in get_order_price()')
        price = sysmin_check(sysmax_check(price))

        return price

    # List of pending (to-be-issued) customer orders is empty so generates a new one
    if len(pending) < 1:
        new_pending = []
        fit_times_to_interval = True
        shuffle_times = True

        # BUYERS (demand-side)
        issue_times = get_issue_times(n_traders, order_sched['timemode'], order_sched['interval'],
                                      fit_times_to_interval, shuffle_times)
        (sched_range, mode) = get_sched_mode(time, order_sched['dem'])
        otype = 'Bid'

        for t in range(n_traders):
            issue_time = time + issue_times[t]
            tname = 'B%02d' % t
            oprice = get_order_price(t, sched_range, n_traders, mode)
            order = Order(tname, otype, oprice, 1, 'Pending', issue_time)
            new_pending.append(order)

        # SELLERS (supply-side)
        issue_times = get_issue_times(n_traders, order_sched['timemode'], order_sched['interval'],
                                      fit_times_to_interval, shuffle_times)
        (sched_range, mode) = get_sched_mode(time, order_sched['sup'])
        otype = 'Ask'

        for t in range(n_traders):
            issue_time = time + issue_times[t]
            tname = 'S%02d' % t
            oprice = get_order_price(t, sched_range, n_traders, mode)
            order = Order(tname, otype, oprice, 1, 'Pending', issue_time)
            new_pending.append(order)

    # List of pending orders not empty so issues any to traders where issue_time is in the past
    else:
        new_pending = []
        for order in pending:
            if time > order.time:
                # issue_time is in the past so issue order to trader
                tname = order.tid
                traders[tname].add_order(order)
                if verbose:
                    print('New order issued: %s' % traders[tname].order)
            # Only add order to new_pending if issue_time is in the past
            else:
                new_pending.append(order)

    return new_pending


def process_order(order, time, traders, buy_network, sell_network, verbose):
    # Form a list of agents willing to deal
    def get_willing(price, traders, neighbors, char):
        willing_list = []
        for n in neighbors:
            tname = char % n
            if traders[tname].willing_to_trade(price):
                willing_list.append(tname)
        return willing_list

    nodeid = traders[order.tid].nodeid
    if order.otype == 'Bid':
        neighbors = list(sell_network.neighbors(nodeid))
        willing = get_willing(order.price, traders, neighbors, 'S%02d')
    elif order.otype == 'Ask':
        neighbors = list(buy_network.neighbors(nodeid))
        willing = get_willing(order.price, traders, neighbors, 'B%02d')
    else:
        sys.exit('FATAL: order type is neither Bid or Ask in process_order()\n')

    if len(willing) > 0:
        order.status = 'Deal'
        counterparty = random.choice(willing)
        transaction_record = {'time': time,
                              'price': order.price,
                              'party1': counterparty,
                              'party2': order.tid,
                              'qty': order.qty}
        if verbose:
            print('>>>>>>>>>>>>>>>>>TRADE t=%5.2f $%d %s %s' % (time, order.price, counterparty, order.tid))
    else:
        order.status = 'NoDeal'
        transaction_record = None
        if verbose:
            print('************* NO TRADE t=%5.2f $%d %s' % (time, order.price, order.tid))

    return transaction_record


def update_traders(order, traders, buy_network, sell_network, verbose):
    nodeid = traders[order.tid].nodeid

    buyers = list(buy_network.neighbors(nodeid))
    buyers.append(nodeid)
    for b in buyers:
        bname = 'B%02d' % b
        traders[bname].update(order.price, order.otype, order.status, verbose)

    sellers = list(sell_network.neighbors(nodeid))
    sellers.append(nodeid)
    for s in sellers:
        sname = 'S%02d' % s
        traders[sname].update(order.price, order.otype, order.status, verbose)


def run(trial_id, start_time, end_time, order_sched, traders, n_traders, buy_network, sell_network):
    orders_verbose = False
    trade_verbose = False
    update_verbose = False
    bookkeep_verbose = False

    # Initialise trading data + day data
    tdat = data.init_tdat()
    ddat = data.init_ddat(order_sched['interval'])

    timestep = 1.0 / float(n_traders * 2)  # TODO: need to check this
    time = start_time

    pending_orders = []

    while time <= end_time:
        trade_price = np.nan
        eq = data.find_eq(traders, n_traders)

        pending_orders = customer_orders(time, traders, n_traders, order_sched, pending_orders, orders_verbose)

        # Get shout (order) from randomly chosen trader
        tid = random.choice(list(traders.keys()))
        order = traders[tid].get_order(time)
        if order is not None:
            trade = process_order(order, time, traders, buy_network, sell_network, trade_verbose)
            if trade is not None:
                traders[trade['party1']].bookkeep(trade, bookkeep_verbose)
                traders[trade['party2']].bookkeep(trade, bookkeep_verbose)
                trade_price = trade['price']

            update_traders(order, traders, buy_network, sell_network, update_verbose)

        ddat.update_ddat(trial_id, time, eq, trade_price)
        tdat = data.update_tdat(tdat, trial_id, time, eq, trade_price)
        time += timestep

    ddat.update_ddat(trial_id, time, eq, trade_price)
    # tdat = data.update_tdat(tdat, trial_id, time, eq, trade_price)
    ddat_df = ddat.get_df()
    return ddat_df, tdat
