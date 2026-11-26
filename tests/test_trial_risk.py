"""缺测当班单据的同档口成套试算与去向判定。"""

from dataclasses import replace

import pytest

from weighttally.basket_backtest.contracts import TrialFrame, TrialRisk
from weighttally.basket_backtest.service import check_point, prepare_verification
from weighttally.basket_backtest.trial import build_trial, range_state
from weighttally.bench_reweigh.contracts import RISK_CUTOFF, Policy
from weighttally.bench_reweigh.service import recommend
from weighttally.pipeline import execute, open_fixture, preview
from weighttally.scale_slips.service import load_samples
from weighttally.tare_deviation.service import fit_model, predict
from weighttally.tare_versions.service import build_windows
from weighttally.variance_context.service import fit_features, numeric_fields, transform_windows

RAW = ('ticket_g', 'actual_g', 'tare_g', 'temp_c', 'bins', 'return_g')


def constant(value, hard=False):
    return lambda vector, filled: (value, (), ('UNDERRECORDED_TARE',) if hard else (), hard)


def trial_context():
    dataset = open_fixture()
    intake = load_samples(dataset['records'], dataset['as_of'])
    windows = build_windows(intake.entries)
    reference = fit_features(windows.train)
    prepared = transform_windows(windows, reference)
    target = next(vector for vector in prepared.live if vector.missing)
    return windows, reference, prepared, target


def calibrated_assessment(target, reference):
    """与线上一致：用回放前 16 条已确认标签拟合校准，再核对当班单据。"""
    _, _, prepared, _ = trial_context()
    model = fit_model(prepared.train, reference.fingerprint)
    labelled = [replace(point, outcome=float(index % 2), observed=True)
                for index, point in enumerate(predict(model, prepared.calibration, reference.fingerprint)[:16])]
    anchor = prepare_verification(labelled)
    point = predict(model, (target,), reference.fingerprint)[0]
    return check_point(point, anchor)


def test_trial_uses_only_complete_same_cohort_training_donors():
    windows, _, _, target = trial_context()
    trial = build_trial(target, windows.train, constant(.2))
    assert trial is not None and trial.blocked is None
    contributions = {tuple(getattr(row, field) for field in RAW if field in target.missing)
                     for row in windows.train
                     if row.cohort == target.cohort and all(getattr(row, field) is not None for field in RAW)}
    assert len(trial.frames) == len(contributions)
    for frame in trial.frames:
        for field, value in zip(RAW, frame.input_values):
            if field not in target.missing:
                assert value == target.input_values[RAW.index(field)]


def test_trial_feeds_same_feature_pipeline_as_online():
    windows, reference, _, target = trial_context()
    captured = []

    def evaluate(vector, filled):
        normalized, factors, flags = numeric_fields(filled, reference)
        captured.append((vector, filled, normalized, factors))
        return .1, flags, (), False

    build_trial(target, windows.train, evaluate)
    assert captured
    for vector, filled, normalized, factors in captured:
        assert vector is target
        expected = numeric_fields(filled, reference)
        assert (normalized, factors) == (expected[0], expected[1])


def test_risk_range_covers_minimum_and_maximum_frames():
    windows, _, _, target = trial_context()
    values = iter(range(1000))
    trial = build_trial(target, windows.train, lambda vector, filled: (next(values) / 1000, (), (), False))
    assert trial.lower == min(frame.estimate for frame in trial.frames)
    assert trial.upper == max(frame.estimate for frame in trial.frames)
    assert trial.lower <= trial.upper


def test_lowest_risk_reaching_line_becomes_candidate():
    windows, _, _, target = trial_context()
    trial = build_trial(target, windows.train, constant(RISK_CUTOFF + .1))
    assert range_state(trial.lower, trial.upper, RISK_CUTOFF) == ('候选', 'TRIAL_ABOVE_TRIGGER')


def test_range_below_line_stays_observation():
    windows, _, _, target = trial_context()
    trial = build_trial(target, windows.train, constant(RISK_CUTOFF - .1))
    assert range_state(trial.lower, trial.upper, RISK_CUTOFF) == ('观察', 'TRIAL_BELOW_TRIGGER')


def test_straddling_range_goes_to_manual_review():
    windows, _, _, target = trial_context()
    fills = iter([RISK_CUTOFF - .2, RISK_CUTOFF + .2])
    trial = build_trial(target, windows.train, lambda vector, filled: (next(fills, RISK_CUTOFF + .2), (), (), False))
    assert trial.lower < RISK_CUTOFF <= trial.upper
    assert range_state(trial.lower, trial.upper, RISK_CUTOFF) == ('人工判读', 'TRIAL_STRADDLES')


def test_no_same_cohort_donor_blocks_with_reference_code():
    windows, _, _, target = trial_context()
    other_cohort = [row for row in windows.train if row.cohort != target.cohort]
    trial = build_trial(target, other_cohort, constant(.9))
    assert trial.blocked == 'NO_COHORT_REFERENCE'
    assert trial.frames == () and trial.lower is None and trial.upper is None


def test_missing_ticket_weight_blocks_before_trial():
    windows, _, _, target = trial_context()
    trial = build_trial(replace(target, missing=('ticket_g',)), windows.train, constant(.9))
    assert trial.blocked == 'MISSING_TICKET_WEIGHT'


def test_trial_pause_risk_forces_manual_review():
    windows, reference, _, target = trial_context()
    trial = build_trial(target, windows.train, constant(.1, hard=True))
    assert trial.pause_risk
    graded = replace(calibrated_assessment(target, reference), trial=trial)
    decision = recommend(graded, frozenset(), Policy.select(12, 'balanced'))
    assert decision.state == '人工判读' and decision.reason == 'TRIAL_PAUSE_RISK'


def test_blocked_trial_decision_is_manual_review():
    _, reference, _, target = trial_context()
    graded = replace(calibrated_assessment(target, reference),
                     trial=TrialRisk((), None, None, 'NO_COHORT_REFERENCE'))
    decision = recommend(graded, frozenset(), Policy.select(12, 'balanced'))
    assert decision.state == '人工判读' and decision.reason == 'NO_COHORT_REFERENCE'


def test_trial_contract_rejects_incomplete_range():
    with pytest.raises(ValueError, match='依据'):
        TrialRisk((), None, None, None)
    with pytest.raises(ValueError, match='范围'):
        TrialRisk((TrialFrame('x', (1.,), .2, ()),), .5, None, None)
    with pytest.raises(ValueError, match='暂停'):
        TrialRisk((), None, None, 'NO_COHORT_REFERENCE', pause_risk=True)


def test_preview_exposes_trial_range_and_stays_deterministic():
    first = preview()
    assert first == preview()
    trial_rows = [row for row in first['rows'] if row['trial_risk']]
    assert trial_rows, '样例应包含缺测试算单'
    assert any(row['state'] == '观察' for row in trial_rows)
    assert sum(row['cost'] for row in first['rows'] if row['state'] == '已分派') + first['metrics'][-1]['value'] == 12


def test_reversed_import_keeps_trial_and_disposition():
    dataset = open_fixture()
    forward = execute(dataset['records'])
    backward = execute(list(reversed(dataset['records'])))
    assert forward['run_id'] == backward['run_id']
    assert forward['rows'] == backward['rows']
