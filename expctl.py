from ast import literal_eval


def get_params(filename):
    n_trials = 0
    traders_spec = []
    network_type = None
    p = 0
    k = 0
    days = None
    order_schedule = {}
    demand_schedule = []
    supply_schedule = []
    interval = None
    start_time = 0.0
    end_time = None

    def get_sched(ls, x):
        start = int(ls[x + 1]) * interval
        end = (int(ls[x + 2]) + 1) * interval
        ranges = literal_eval(ls[x + 3].strip())
        stepmode = ls[x + 4].strip('\n')
        s = {'from': start, 'to': end, 'ranges': ranges, 'stepmode': stepmode}
        return s

    with open(filename) as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith('#trials'):
                n_trials = int(lines[i + 1])
            elif line.startswith('#agents'):
                traders = lines[i + 1].split()
                for t in range(0, len(traders), 2):
                    ttype = traders[t]
                    num = int(traders[t + 1])
                    traders_spec.append((ttype, num))
            elif line.startswith('#network'):
                network_type = lines[i + 1].strip('\n')
                if network_type == 'Random':
                    p = float(lines[i+2])
                elif network_type == 'SW':
                    p = float(lines[i+2])
                    k = int(lines[i+3])
                elif network_type == 'SF':
                    k = int(lines[i+2])
            elif line.startswith('#order_interval'):
                interval = float(lines[i + 1])
                order_schedule['interval'] = interval
            elif line.startswith('#days'):
                days = int(lines[i + 1])
                end_time = days * interval
            elif line.startswith('#order_timemode'):
                order_schedule['timemode'] = lines[i + 1].strip('\n')
            elif line.startswith('#demand_schedule'):
                if interval is not None:
                    sched = get_sched(lines, i)
                    demand_schedule.append(sched)
            elif line.startswith('#supply_schedule'):
                if interval is not None:
                    sched = get_sched(lines, i)
                    supply_schedule.append(sched)

    if demand_schedule:
        order_schedule['dem'] = demand_schedule
    if supply_schedule:
        order_schedule['sup'] = supply_schedule

    params = {'n_trials': n_trials,
              'network': [network_type, p, k],
              'n_days': days,
              'start': start_time,
              'end': end_time,
              'traders_spec': traders_spec,
              'order_sched': order_schedule}
    return params
