from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from .contracts import Job


@dataclass(frozen=True, slots=True)
class WorkOrder:
    job: Job
    assessment: Any

    def __post_init__(self):
        if self.job.key != self.assessment.raw.key:
            raise ValueError('处置工位与单据不匹配')


def apply_bench_reweigh(weighings, admit: Callable, wait: Callable):
    scale_slots = {}
    for ticket in weighings:
        label, gross, tare, temp, cells, refund = ticket.assessment.raw.input_values
        net = max(0, gross-tare+refund)
        category = (ticket.job.cohort, '轻称' if label<420 else '大称')
        used = scale_slots.get(category, 0)
        if refund and gross<=tare:
            wait(ticket, 'ORIGINAL_SLIP_REQUIRED', '净重和退秤记录互相冲突')
            continue
        if cells >= 12 and net != label and used >= 3:
            wait(ticket, 'SCALE_TARE_SLOT_FULL', '同类秤台本班复秤签满')
        elif admit(ticket):
            scale_slots[category] = used + 1
