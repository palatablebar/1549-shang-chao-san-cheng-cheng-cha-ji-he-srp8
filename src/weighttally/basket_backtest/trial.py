"""同档口成套试算：为缺测当班单据给出风险范围。

缺测单据不能凭一个拟合补值直接派单：同一缺项在不同同档口成套实测下
可能一侧过线、一侧不过线，按单一补值占用的工位就会错。试算只取训练期
内与当班单据同作业区、六项量测齐全的记录逐条补缺，再走与线上一致的特征
处理和当班校准，得到估计的最低与最高值。

风险范围的判定：
- 最低值达线：整段落在线以上，进入候选；
- 最高值仍低于线：整段留观；
- 跨线：无法确定去向，先转人工判读。
"""

from .contracts import TrialFrame, TrialRisk

RAW_KEYS = ('ticket_g', 'actual_g', 'tare_g', 'temp_c', 'bins', 'return_g')


def complete_donors(training, cohort):
    """训练期内同档口、六项量测齐全的记录，按工日和单号排序。"""
    selected = []
    for record in sorted(training, key=lambda row: (row.day, row.key)):
        if record.cohort != cohort:
            continue
        if any(getattr(record, field) is None for field in RAW_KEYS):
            continue
        selected.append(record)
    return selected


def build_trial(vector, training, evaluate):
    """为缺测特征向量构造同档口成套试算；无缺测返回 None。

    ``evaluate`` 接收 ``(当班向量, 补全后的六项量测)``，返回 ``(估计, 偏离
    特征, 命中规则码, 是否命中硬规则)``。它的实现必须复用当班特征版本、模型
    与校准，保证试算与线上单条推断同口径。

    不同来源对缺项取值相同时只算一条；风险范围取全部试算的最低与最高值，
    不做截断，避免人为收窄范围。
    """
    missing = tuple(vector.missing)
    if not missing:
        return None
    # 工位数按票面重量计算，缺票面重量时补值会直接把工位档次定错。
    if 'ticket_g' in missing:
        return TrialRisk((), None, None, 'MISSING_TICKET_WEIGHT')
    frames = []
    seen = set()
    pause_risk = False
    for record in complete_donors(training, vector.cohort):
        filled = tuple(getattr(record, field) if field in missing else value
                       for field, value in zip(RAW_KEYS, vector.input_values, strict=True))
        contribution = tuple(value for field, value in zip(RAW_KEYS, filled, strict=True) if field in missing)
        if contribution in seen:
            continue
        seen.add(contribution)
        estimate, excursions, rule_hits, hard = evaluate(vector, filled)
        pause_risk = pause_risk or hard
        frames.append(TrialFrame(record.key, filled, estimate, tuple(excursions), tuple(rule_hits)))
    if not frames:
        return TrialRisk((), None, None, 'NO_COHORT_REFERENCE')
    frames.sort(key=lambda frame: (frame.estimate, frame.source))
    return TrialRisk(tuple(frames), frames[0].estimate, frames[-1].estimate, None, pause_risk)


def range_state(lower, upper, trigger):
    """整段最低/最高估计相对阈值的去向。"""
    if lower >= trigger:
        return '候选', 'TRIAL_ABOVE_TRIGGER'
    if upper < trigger:
        return '观察', 'TRIAL_BELOW_TRIGGER'
    return '人工判读', 'TRIAL_STRADDLES'


def range_text(trial):
    if trial is None or trial.blocked is not None:
        return None
    return f'{trial.lower:.4f}–{trial.upper:.4f}'


BLOCKED_SUMMARY = {'NO_COHORT_REFERENCE': '试算缺少同档口成套实测，需人工判读',
                   'MISSING_TICKET_WEIGHT': '缺少票面重量，工位档次无法确定，需人工判读'}


def blocked_summary(trial):
    return BLOCKED_SUMMARY.get(trial.blocked, '试算依据不足，需人工判读')


def frame_evidence(frames, limit=24):
    """按估计排序后均匀取样，保证换序重算的展示顺序一致。"""
    if len(frames) <= limit:
        chosen = list(frames)
    else:
        step = (len(frames) - 1) / (limit - 1)
        chosen = [frames[round(index * step)] for index in range(limit)]
    return [{'来源单号': frame.source, '估计': round(frame.estimate, 4),
             '偏离特征': '、'.join(frame.excursions) or '—',
             '命中规则': '、'.join(frame.rule_hits) or '—'} for frame in chosen]
