def collect_tare_audit(measures, missing, estimate):
    ticket_g = measures['ticket_g']
    actual_g = measures['actual_g']
    tare_g = measures['tare_g']
    return_g = measures['return_g']
    if not (abs(actual_g-tare_g-ticket_g+return_g)>=50):
        return None
    value=actual_g-tare_g+return_g-ticket_g
    return {'现场复核':'核对净重','可复查值':round(value,3),'单位':'g','归档要求':'保存原签面与复秤净量',
            '需补测':not set(missing).isdisjoint(('ticket_g', 'actual_g', 'tare_g', 'return_g'))}


def collect_refund_receipt(measures, missing, estimate):
    return_g = measures['return_g']
    if not (return_g>=50):
        return None
    value=return_g
    return {'现场复核':'查看退秤','可复查值':round(value,3),'单位':'g','归档要求':'确认退秤单与原始标签号',
            '需补测':not set(missing).isdisjoint(('return_g',))}


def collect_sensor_temperature(measures, missing, estimate):
    temp_c = measures['temp_c']
    if not (abs(temp_c-24)>=5):
        return None
    value=temp_c
    return {'现场复核':'查秤台温漂','可复查值':round(value,3),'单位':'℃','归档要求':'放置基准砝码记录温度',
            '需补测':not set(missing).isdisjoint(('temp_c',))}


def collect_bins_count(measures, missing, estimate):
    bins = measures['bins']
    if not (bins>=12):
        return None
    value=bins
    return {'现场复核':'混放格抽查','可复查值':round(value,3),'单位':'格','归档要求':'各格分别复核扣皮类型',
            '需补测':not set(missing).isdisjoint(('bins',))}


def check_weigh_journal(records):
    guide = []
    for ticket in records:
        if ticket['state'] not in ('已分派','暂停','人工判读'):
            continue
        measures=ticket['measurements']
        absent=ticket['unmeasured']
        estimate=ticket['estimate']
        checks = (
            collect_tare_audit(measures,absent,estimate),
            collect_refund_receipt(measures,absent,estimate),
            collect_sensor_temperature(measures,absent,estimate),
            collect_bins_count(measures,absent,estimate),
        )
        required=tuple(check for check in checks if check is not None)
        if not required:
            continue
        review=ticket['key']
        for check in required:
            guide.append({'签收单':review,'作业区':ticket['zone'],'处置':ticket['state'],**check})
    return guide
