from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JointAction:
    case: str
    work_units: int
    notes: str
    changes: dict[str, tuple[float, float]]

    def evidence(self, old_value, new_value, extrapolates):
        return {'联动推演':self.case, '用量':self.work_units, '先决条件':self.notes,
                '原预测':round(old_value,4), '替换预测':round(new_value,4),
                '变化':round(new_value-old_value,4), '超训练域':bool(extrapolates),
                '联动量测':{item:{'原值':before,'替换值':after} for item,(before,after) in self.changes.items()}}


def simulate_reverse_void_tare(readings, invalid):
    tare_g, return_g = readings[2], readings[5]
    if invalid.intersection(('tare_g', 'return_g')):
        return None
    if not (return_g>=23 and tare_g>=18):
        return None
    return_g_adjusted = 0
    tare_g_adjusted = tare_g-8
    inspected = {
        'return_g': (return_g, return_g_adjusted),
        'tare_g': (tare_g, tare_g_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('置零退秤重称', 2, '先核对原签退秤再复核扣皮', inspected)
    return None


def simulate_reference_temp(readings, invalid):
    temp_c, bins = readings[3], readings[4]
    if invalid.intersection(('temp_c', 'bins')):
        return None
    if not (abs(temp_c-24)>=4 and bins>=6):
        return None
    temp_c_adjusted = 24
    bins_adjusted = bins-3
    inspected = {
        'temp_c': (temp_c, temp_c_adjusted),
        'bins': (bins, bins_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('移低温档复秤', 1, '同包进入低温抽检秤', inspected)
    return None


def simulate_full_reweigh(readings, invalid):
    ticket_g, actual_g = readings[0], readings[1]
    if invalid.intersection(('ticket_g', 'actual_g')):
        return None
    if not (actual_g>=115 and ticket_g>=150):
        return None
    actual_g_adjusted = actual_g-15
    ticket_g_adjusted = ticket_g-20
    inspected = {
        'actual_g': (actual_g, actual_g_adjusted),
        'ticket_g': (ticket_g, ticket_g_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('核对实称和标签', 2, '站点发现写签量偏高后双签确认', inspected)
    return None


def simulate_reorg_returns(readings, invalid):
    bins, return_g = readings[4], readings[5]
    if invalid.intersection(('bins', 'return_g')):
        return None
    if not (return_g>=37 and bins>=7):
        return None
    return_g_adjusted = return_g-23
    bins_adjusted = bins-4
    inspected = {
        'return_g': (return_g, return_g_adjusted),
        'bins': (bins, bins_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('退秤拆框', 2, '避免同批箱签自动回冲两次', inspected)
    return None


def simulate_swap_product_tare(readings, invalid):
    actual_g, tare_g = readings[1], readings[2]
    if invalid.intersection(('actual_g', 'tare_g')):
        return None
    if not (tare_g>=24 and actual_g>121):
        return None
    tare_g_adjusted = tare_g-14
    actual_g_adjusted = actual_g-12
    inspected = {
        'tare_g': (tare_g, tare_g_adjusted),
        'actual_g': (actual_g, actual_g_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('较轻包装退秤', 2, '换掉外盒后复核客户实得量', inspected)
    return None


def options(values, missing):
    measurements=tuple(values)
    unobserved=frozenset(missing)
    cases=(
        simulate_reverse_void_tare(measurements, unobserved),
        simulate_reference_temp(measurements, unobserved),
        simulate_full_reweigh(measurements, unobserved),
        simulate_reorg_returns(measurements, unobserved),
        simulate_swap_product_tare(measurements, unobserved),
    )
    return tuple(action for action in cases if action is not None)
