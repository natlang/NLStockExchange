# Order has a trader id, type (bid/ask), price, quantity, time it was issued and status (pending/accepted/rejected)
class Order:

    def __init__(self, tid, otype, price, qty, status, time):
        self.tid = tid
        self.otype = otype
        self.price = price
        self.qty = qty
        self.status = status
        self.time = time

    def __str__(self):
        return '[%s %s %s P=%03d Q=%s T=%5.2f]' % (self.tid, self.otype, self.status, self.price, self.qty, self.time)