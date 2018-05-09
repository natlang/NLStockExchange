import random
import numpy as np

import config
from order import Order


class AgentZIC:
    def __init__(self, ttype, tid, nodeid, job):
        # All traders
        self.ttype = ttype
        self.tid = tid
        self.nodeid = nodeid
        self.job = job
        self.active = False
        self.order = None
        self.limit = None
        self.price = None
        self.balance = 0.0
        self.price_hist =[]

    def __str__(self):
        return '[TID %s type %s nodeid %s limit %s]' \
               % (self.tid, self.ttype, self.nodeid, self.limit)

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
        if self.job == 'Buy':
            quoteprice = random.randint(config.MIN_PRICE, self.limit)
        else:
            quoteprice = random.randint(self.limit, config.MAX_PRICE)
        self.price = quoteprice
        return quoteprice

    # Add price to price_hist
    def update_price_hist(self):
        if self.price is not None:
            if self.price_hist:
                prev_price = self.price_hist[-1]
                if self.price != prev_price:
                    self.price_hist.append(self.price)
            else:
                self.price_hist.append(self.price)

    # At end of each day, reset price_hist
    def reset_price_hist(self):
        self.price_hist = []

    # Is a trader willing to trade at a given price?
    def willing_to_trade(self, oprice):
        willing = False
        if self.order is not None:
            if self.job == 'Buy' and self.active and self.price >= oprice:
                willing = True
            elif self.job == 'Sell' and self.active and self.price <= oprice:
                willing = True
        return willing

    # Adjust bank balances of agent in deal
    # Adjust bank balances of agent in deal
    def bookkeep(self, trade, verbose):
        outstr = '%s (%s) bookkeeping: order = %s' % (self.tid, self.ttype, self.order)

        transactionprice = trade['price']
        if self.job == 'Buy':
            profit = self.limit - transactionprice
        else:
            profit = transactionprice - self.limit

        if profit < 0.0:
            profit = 0.0
        self.balance += profit
        if verbose:
            print('%s profit=%d balance=%d' % (outstr, profit, self.balance))
        self.del_order()

    # Update buyer/seller strategy after a order
    def update(self, oprice, otype, status, verbose):
        pass
