from dataclasses import dataclass
from ..tare_deviation.contracts import Prediction

RISK_MODE = True


@dataclass(frozen=True, slots=True)
class Verification:
    method: str
    parameters: tuple
    size: int
    positives: int | None

    def __post_init__(self):
        if self.size < 0 or self.positives is not None and not 0 <= self.positives <= self.size:
            raise ValueError('校准回查计数失衡')


@dataclass(frozen=True, slots=True)
class TrialFrame:
    source: str
    input_values: tuple[float, ...]
    estimate: float
    excursions: tuple[str, ...]
    rule_hits: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TrialRisk:
    frames: tuple[TrialFrame, ...]
    lower: float | None
    upper: float | None
    blocked: str | None = None
    pause_risk: bool = False

    def __post_init__(self):
        if self.blocked is None and not self.frames:
            raise ValueError('试算缺少同档口成套依据')
        if self.frames and (self.lower is None or self.upper is None or self.lower > self.upper):
            raise ValueError('试算风险范围不完整')
        if not self.frames and (self.lower is not None or self.upper is not None):
            raise ValueError('无依据的试算不能给出风险范围')
        if self.blocked is not None and self.pause_risk:
            raise ValueError('无成套依据的试算不能声明暂停风险')


@dataclass(frozen=True, slots=True)
class Assessment:
    raw: Prediction
    estimate: float
    lower: float | None
    upper: float | None
    uncertain: bool
    # Missing measurements are never dispatched from a single frozen fill value.
    # A trial keeps every same-cohort completed reading the estimate can take.
    trial: TrialRisk | None = None


@dataclass(frozen=True, slots=True)
class CalibrationRow:
    index: int
    predicted: float | None
    observed: float | None
    count: int


@dataclass(frozen=True, slots=True)
class ModelReport:
    status: str
    count: int
    mae: float | None
    error: float | None
    buckets: tuple[CalibrationRow, ...]
    auxiliary: int | float | None
