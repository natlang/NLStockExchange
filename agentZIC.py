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
        self.price_hist = None

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
    def bookkeep(self, trade):
        transactionprice = trade['price']
        if self.order.otype == 'Bid':
            profit = self.order.price - transactionprice
        else:
            profit = transactionprice - self.order.price

        if profit < 0.0:
            profit = 0.0

        self.balance += profit
        self.del_order()

    # Update buyer/seller strategy after a order
    def update(self, oprice, otype, status, verbose):
        pass
