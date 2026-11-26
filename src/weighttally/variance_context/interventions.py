from dataclasses import replace
from statistics import median

from .contracts import VarianceContext, Proposal


def measure_variance_context(values) -> VarianceContext:
    ticket_g, actual_g, tare_g, temp_c, bins, return_g = values
    return VarianceContext(
        corrected_grams=actual_g-tare_g+return_g,
        gross_gap=actual_g-ticket_g,
        customer_gap=actual_g-tare_g+return_g-ticket_g,
        label_severity=1000*(actual_g-tare_g+return_g-ticket_g)/ticket_g,
        paper_tare=1000*tare_g/ticket_g,
        actual_drift=temp_c-24,
        return_units=return_g/bins,
        low_net=float(actual_g-tare_g<90),
    )


def propose_bench_reweigh(values, missing=()):
    ticket_g, actual_g, tare_g, temp_c, bins, return_g = values
    if 'tare_g' not in missing and (tare_g>=15):
        yield Proposal('按现标皮重重称', 'tare_g', tare_g, max(6,tare_g-9), 1)
    if 'return_g' not in missing and (return_g>=45):
        yield Proposal('取消争议退秤读数', 'return_g', return_g, 0, 2)
    if 'temp_c' not in missing and (abs(temp_c-24)>=4):
        yield Proposal('低温秤台复测温漂', 'temp_c', temp_c, 24, 1)
    if 'actual_g' not in missing and (abs(actual_g-tare_g-ticket_g)>=80):
        yield Proposal('按原标签重测净重', 'actual_g', actual_g, min(3300,ticket_g+tare_g), 2)
