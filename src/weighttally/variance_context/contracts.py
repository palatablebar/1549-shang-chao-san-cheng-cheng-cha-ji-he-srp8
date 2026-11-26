from dataclasses import dataclass
from math import isfinite
from ..scale_slips.contracts import WeighttallyRecord as RawObservation

RAW_KEYS = ('ticket_g', 'actual_g', 'tare_g', 'temp_c', 'bins', 'return_g')
FEATURE_KEYS = ('net_gap', 'tare_ratio', 'return_rate', 'thermal_offset', 'bin_load')
FEATURE_NAMES = ('相对实称差', '扣皮比', '退秤比', '温漂因子', '分拣格负荷')


@dataclass(frozen=True, slots=True)
class FeatureState:
    fill: tuple[float, ...]
    offsets: tuple[float, ...]
    scales: tuple[float, ...]
    floor: tuple[float, ...]
    ceil: tuple[float, ...]
    fingerprint: str

    def __post_init__(self):
        if len(self.fill) != len(RAW_KEYS):
            raise ValueError('补值向量维数与字段表不匹配')
        if any(len(column) != len(FEATURE_KEYS) for column in (self.offsets, self.scales, self.floor, self.ceil)):
            raise ValueError('特征状态维数不匹配')
        if min(self.scales) <= 0:
            raise ValueError('特征尺度必须为正')


@dataclass(frozen=True, slots=True)
class FeatureVector:
    key: str
    cohort: str
    day: int
    values: tuple[float, ...]
    factors: tuple[float, ...]
    missing: tuple[str, ...]
    excursions: tuple[str, ...]
    outcome: float | None
    observed: bool
    input_values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PreparedRuns:
    train: tuple[FeatureVector, ...]
    calibration: tuple[FeatureVector, ...]
    replay: tuple[FeatureVector, ...]
    live: tuple[FeatureVector, ...]

    def segments(self):
        return tuple((name, getattr(self, name)) for name in ('train', 'calibration', 'replay', 'live'))


@dataclass(frozen=True, slots=True)
class Proposal:
    name: str
    field: str
    before: float
    after: float
    work: int

    def __post_init__(self):
        if self.before == self.after or not isfinite(self.after) or self.work < 0:
            raise ValueError('推演动作需要实质变动和有效额度')

    def evidence(self):
        return {'情形': self.name, '变更项': self.field, '原值': self.before,
                '置换值': self.after, '用量': self.work}

@dataclass(frozen=True, slots=True)
class VarianceContext:
    corrected_grams: float
    gross_gap: float
    customer_gap: float
    label_severity: float
    paper_tare: float
    actual_drift: float
    return_units: float
    low_net: float

    def __post_init__(self):
        if not all(isfinite(amount) for amount in (self.corrected_grams, self.gross_gap, self.customer_gap, self.label_severity, self.paper_tare, self.actual_drift, self.return_units, self.low_net)):
            raise ValueError('散称签存在无效的作业量测')

    def explain(self, labels=None):
        return (
            ('净重加回退秤', round(self.corrected_grams, 4)),
            ('标签到盘面差', round(self.gross_gap, 4)),
            ('净重与标签差', round(self.customer_gap, 4)),
            ('差额千克比', round(self.label_severity, 4)),
            ('每公斤扣皮量', round(self.paper_tare, 4)),
            ('秤台温度与中点差', round(self.actual_drift, 4)),
            ('每格退秤分摊', round(self.return_units, 4)),
            ('净重是否小于最小档', round(self.low_net, 4)),
        )
