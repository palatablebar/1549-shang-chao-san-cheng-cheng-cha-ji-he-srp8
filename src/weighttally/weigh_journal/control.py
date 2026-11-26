from collections import Counter
from math import isfinite


def accountable_plan(rows, actual_balance, starting_capacity):
    seen = set()
    counts = Counter()
    total = 0
    for row in rows:
        if row['key'] in seen:
            raise ArithmeticError('复核凭证的关联单号不唯一')
        key = row['key']
        seen.add(key)
        state = row['state']
        counts[state] += 1
        if state == '已分派':
            total += row['cost']
        if not isfinite(row['estimate']):
            raise ArithmeticError('非有限估计不能签发')
    if total + actual_balance != starting_capacity:
        raise ArithmeticError('处置清册与工位余额不符')
    return counts, total


def register_weigh_journal(measurements, estimate):
    ticket_g = measurements['ticket_g']
    actual_g = measurements['actual_g']
    tare_g = measurements['tare_g']
    temp_c = measurements['temp_c']
    bins = measurements['bins']
    return_g = measurements['return_g']
    return {
        '净重加回退秤': round(actual_g-tare_g+return_g, 3),
        '净重与标签差': round(actual_g-tare_g+return_g-ticket_g, 3),
        '每格退秤分摊': round(return_g/bins, 3),
        '净重是否小于最小档': round(float(actual_g-tare_g<90), 3),
        '复核代价指标': round(abs(actual_g-tare_g+return_g-ticket_g)/max(120,ticket_g) + tare_g/160, 4),
    }


def document_control(rows):
    register = []
    for row in rows:
        if row['state'] not in {'已分派', '暂停', '人工判读'}:
            continue
        note = register_weigh_journal(row['measurements'], row['estimate'])
        register.append({'单号': row['key'], '区段': row['zone'], '处置': row['state'], **note})
    return register
