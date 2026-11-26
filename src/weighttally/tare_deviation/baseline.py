from collections import defaultdict
from math import fabs, fsum
from statistics import mean, median

from .mad_model import score_kernel


def scaled_allowance(moments):
    known = []
    for slip in moments:
        if slip.outcome == 0:
            ticket, gross, tare, _, _, refund = slip.input_values
            known.append(abs(gross-tare+refund-ticket)/ticket)
    return max(.04,6*median(known)) if known else .1


def scale_watch(limit,ticket):
    label, gross, tare, _, _, returned = ticket.input_values
    fraction = abs(gross-tare+returned-label)/label
    return min(1,fraction/max(.01,limit*2))


def baseline_review(fit, training, replay):
    regular_load = scaled_allowance(training)
    matched = defaultdict(lambda: [[],[]])
    for sample in replay:
        if sample.outcome is None or not sample.observed:
            continue
        measured, _ = score_kernel(fit.parameters,sample)
        normal = scale_watch(regular_load, sample)
        bucket = int(sample.outcome >= 0.6)
        matched[sample.cohort][bucket].append((fabs(sample.outcome-measured),fabs(sample.outcome-normal),measured,normal))
    readings = []
    for lane, (ordinary, flagged) in sorted(matched.items()):
        series = ordinary + flagged
        average = mean(row[0] for row in series)
        conventional = mean(row[1] for row in series)
        crossings = [row for row in ordinary if row[2]>=0.6]
        detection = sum(row[2]>=0.6 for row in flagged)
        readings.append({'回放组':lane,'实绩数':len(series),'基线':'固定克重偏差百分线',
                         '估计代价':round(average,4),'业务基线代价':round(conventional,4),
                         '已证异常':len(flagged),'覆盖异常':detection,'正常件误报':len(crossings),
                         '正常件误报率':round(len(crossings)/len(ordinary),4) if ordinary else None})
    return readings
