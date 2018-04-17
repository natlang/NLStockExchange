import random
import sys

from order import Order


class AgentZIP:
    def __init__(self, ttype, tid, nodeid, job, margin):
        # All traders
        self.ttype = ttype
        self.tid = tid
        self.nodeid = nodeid
        self.job = job
        self.active = False
        self.order = None  # TODO in Cliff '97 this is self.price and self.quant - maybe I need to change this?
        self.limit = None
        self.price = None
        self.balance = 0.0  # called bank in Cliff '97
        # Specific to ZIP
        # self.deals_done = 0
        self.margin = margin  # called profit in Cliff '97
        self.beta = 0.1 * random.randrange(1, 6)
        self.momentum = 0.1 * random.random()
        self.prev_change = 0  # called last_d in Cliff '97
        # CONSTANTS
        self.c_abs = 0.05
        self.c_rel = 0.05

    def __str__(self):
        return '[TID %s type %s nodeid %s limit %s margin %s price %s]' \
               % (self.tid, self.ttype, self.nodeid, self.limit, self.margin, self.price)

    def add_order(self, order):
        self.active = True
        self.order = order
        self.limit = self.order.price
        self.set_price()

    def get_order(self, time):
        if self.order is None:
            self.active = False
            order = None
        else:
            self.active = True
            status = 'Shout'
            quoteprice = self.price
            order = Order(self.tid, self.order.otype, quoteprice, self.order.qty, status, time)

        return order

    def del_order(self):
        self.order = None
        self.active = False

    def set_price(self):
        quoteprice = int(round(self.limit * (1.0 + self.margin), 0))
        self.price = quoteprice
        return quoteprice

    # Is a trader willing to trade at a given price?
    def willing_to_trade(self, oprice):
        willing = False
        if self.job == 'Buy' and self.active and self.price >= oprice:
            willing = True
        elif self.job == 'Sell' and self.active and self.price <= oprice:
            willing = True
        return willing

    # Adjust bank balances of agent in deal
    def bookkeep(self, trade, verbose):
        outstr = '%s (%s) bookkeeping: order = %s' % (self.tid, self.ttype, self.order)

        transactionprice = trade['price']
        if self.job == 'Buy':
            profit = self.order.price - transactionprice
        else:
            profit = transactionprice - self.order.price

        if profit < 0.0:
            profit = 0.0
        self.balance += profit
        if verbose:
            print('%s profit=%d balance=%d' % (outstr, profit, self.balance))
        self.del_order()

    # Update buyer/seller strategy after a order
    def update(self, oprice, otype, status, verbose):
        # Update profit margin based on sale price using Widrow-Hoff style update rule with learning rate beta
        def profit_alter(target, verbose):
            diff = target - self.price
            change = ((1.0 - self.momentum) * (self.beta * diff)) + (self.momentum * self.prev_change)

            self.prev_change = change
            new_margin = ((self.price + change) / self.limit) - 1.0
            old_margin = self.margin

            if self.job == 'Buy':
                if new_margin < 0.0:
                    self.margin = new_margin
                # else:
                #     print('%s no new margin' % self.tid)
            else:
                if new_margin > 0.0:
                    self.margin = new_margin
                # else:
                #     print('%s no new margin' % self.tid)

            old_price = self.price
            new_price = self.set_price()

            if new_price != old_price and verbose:
                print('TID %s limit = %s : old margin = %s - new margin = %s, old price = %s - new price = %s' % (self.tid, self.limit, old_margin, new_margin, old_price, new_price))

        def target_up(price):
            # print('%s RAISE' % self.tid)
            ptrb_abs = self.c_abs * random.random()
            ptrb_rel = price * (1.0 + (self.c_rel * random.random()))
            target = int(round(ptrb_rel + ptrb_abs, 0))
            return target

        def target_down(price):
            # print('%s LOWER' % self.tid)
            ptrb_abs = self.c_abs * random.random()
            ptrb_rel = price * (1.0 - (self.c_rel * random.random()))
            target = int(round(ptrb_rel - ptrb_abs, 0))
            return target

        profit_verbose = verbose
        if self.job == 'Sell':
            if status == 'Deal':
                # Could sell for more? increase price (increase margin)
                if self.price <= oprice:
                    target_price = target_up(oprice)
                    profit_alter(target_price, profit_verbose)
                # Wouldn't have got deal, reduce price (reduce margin)
                else:
                    if otype == 'Bid' and self.active:
                        target_price = target_down(oprice)
                        profit_alter(target_price, profit_verbose)
            elif status == 'NoDeal':
                # Would've asked for more and lost deal, reduce price (reduce margin)
                if otype == 'Ask' and self.price >= oprice and self.active:
                    target_price = target_down(oprice)
                    profit_alter(target_price, profit_verbose)
            else:
                sys.exit('FATAL: status is neither Deal or NoDeal in Agent.update()\n')

        else:  # self.job == 'Buy'
            if status == 'Deal':
                # Could buy for less? reduce price (increase margin)
                if self.price >= oprice:
                    target_price = target_down(oprice)
                    profit_alter(target_price, profit_verbose)
                # Wouldn't have got deal, increase price (reduce margin)
                else:
                    if otype == 'Ask' and self.active:
                        target_price = target_up(oprice)
                        profit_alter(target_price, profit_verbose)
            elif status == 'NoDeal':
                # Would've bid less and lost deal, increase price (reduce margin)
                if otype == 'Bid' and self.price <= oprice and self.active:
                    target_price = target_up(oprice)
                    profit_alter(target_price, profit_verbose)
            else:
                sys.exit('FATAL: status is neither Deal or NoDeal in Agent.update()\n')
