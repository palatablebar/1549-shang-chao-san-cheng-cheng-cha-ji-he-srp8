from dataclasses import dataclass
from math import sqrt, fsum
from statistics import median


@dataclass(frozen=True, slots=True)
class DomainStudy:
    counts: tuple[int, int, int]
    rate: float | None
    midpoint: float | None
    expected: float | None
    drift: float | None

def store_mix_domains(vectors):
    corrected_grams = []
    gross_gap = []
    customer_gap = []
    label_severity = []
    paper_tare = []
    actual_drift = []
    return_units = []
    low_net = []
    for measurement in vectors:
        unobserved = frozenset(measurement.missing)
        ticket_g, actual_g, tare_g, temp_c, bins, return_g = measurement.input_values
        if unobserved.isdisjoint(('ticket_g', 'actual_g', 'tare_g', 'return_g')):
            corrected_grams.append((round(actual_g-tare_g+return_g, 4), ticket_g<420))
        if unobserved.isdisjoint(('ticket_g', 'actual_g', 'tare_g')):
            gross_gap.append((round(actual_g-ticket_g, 4), tare_g>=85))
        if unobserved.isdisjoint(('ticket_g', 'actual_g', 'tare_g', 'return_g')):
            customer_gap.append((round(actual_g-tare_g+return_g-ticket_g, 4), return_g>=60))
        if unobserved.isdisjoint(('ticket_g', 'actual_g', 'tare_g', 'temp_c', 'return_g')):
            label_severity.append((round(1000*(actual_g-tare_g+return_g-ticket_g)/ticket_g, 4), temp_c>=30))
        if unobserved.isdisjoint(('ticket_g', 'tare_g', 'bins')):
            paper_tare.append((round(1000*tare_g/ticket_g, 4), bins>=14))
        if unobserved.isdisjoint(('ticket_g', 'temp_c')):
            actual_drift.append((round(temp_c-24, 4), ticket_g<420))
        if unobserved.isdisjoint(('tare_g', 'bins', 'return_g')):
            return_units.append((round(return_g/bins, 4), tare_g>=85))
        if unobserved.isdisjoint(('actual_g', 'tare_g', 'return_g')):
            low_net.append((round(float(actual_g-tare_g<90), 4), return_g>=60))
    return {
        '净重加回退秤 · 轻称签': tuple(corrected_grams),
        '标签到盘面差 · 高扣皮档': tuple(gross_gap),
        '净重与标签差 · 退秤非零': tuple(customer_gap),
        '差额千克比 · 高温巡档': tuple(label_severity),
        '每公斤扣皮量 · 多格分拣台': tuple(paper_tare),
        '秤台温度与中点差 · 轻称签': tuple(actual_drift),
        '每格退秤分摊 · 高扣皮档': tuple(return_units),
        '净重是否小于最小档 · 退秤非零': tuple(low_net),
    }


def evaluate_domains(training, current):
    references = store_mix_domains(training)
    activity = store_mix_domains(current)
    diagnostics = []
    for domain, observed in activity.items():
        baseline = references.get(domain, ())
        study = characterize(baseline, observed)
        diagnostics.append({'观察维度': domain, '训练有效量': study.counts[0], '当班有效量': study.counts[1],
                            '越线量':study.counts[2], '越线比例':study.rate, '参考中位':study.midpoint,
                            '当班中位':study.expected, '相对训练变化':study.drift})
    return diagnostics


def characterize(before, after):
    history = tuple(value for value, _ in before)
    observed = tuple(value for value, _ in after)
    violating = sum(flag for _, flag in after)
    old = median(history) if history else None
    new = median(observed) if observed else None
    pct = round(violating / len(after), 4) if after else None
    movement = round(new - old, 4) if old is not None and new is not None else None
    return DomainStudy((len(before),len(after),violating),pct,old,new,movement)
