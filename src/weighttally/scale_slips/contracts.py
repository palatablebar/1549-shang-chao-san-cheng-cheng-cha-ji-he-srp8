from dataclasses import dataclass

FIELDS = {'ticket_g': ('标签重量', 'g', 120, 3300),
 'actual_g': ('抽秤实际', 'g', 90, 3300),
 'tare_g': ('扣皮重量', 'g', 6, 120),
 'temp_c': ('秤台温度', '℃', 12, 37),
 'bins': ('称台分拣格', '格', 2, 21),
 'return_g': ('退秤扣减', 'g', 0, 155)}
LIMITS = {'result_max': 1}


class MeasureIssue(ValueError):
    def __init__(self, field: str, code: str):
        super().__init__(f'{field}:{code}')
        self.field = field
        self.code = code


@dataclass(frozen=True, slots=True)
class WeighttallyRecord:
    key: str
    cohort: str
    day: int
    received: int
    revision: int
    result_day: int | None
    outcome: float | None
    observed: bool
    ticket_g: float | None
    actual_g: float | None
    tare_g: float | None
    temp_c: float | None
    bins: float | None
    return_g: float | None

    def signature(self):
        return (self.key, self.cohort, self.day, self.revision, self.result_day, self.outcome, self.observed,
                *(getattr(self, key) for key in FIELDS))


@dataclass(frozen=True, slots=True)
class Issue:
    source_row: int
    key: str
    field: str
    code: str

    def evidence(self):
        return {'行号': self.source_row, '单号': self.key, '字段': FIELDS.get(self.field, (self.field,))[0],
                '原因': self.code}


@dataclass(frozen=True, slots=True)
class DecodeResult:
    entries: tuple[WeighttallyRecord, ...]
    issues: tuple[Issue, ...]
    source_rows: int
