from dataclasses import replace
import json
from pathlib import Path

from .scale_slips import service as intake_service
from .tare_versions import service as cohort_service
from .variance_context import service as feature_service
from .tare_deviation import service as model_service
from .basket_backtest import service as calibration_service
from .store_mix import service as monitor_service
from .bench_reweigh import service as dispatch_service
from .weigh_journal import service as audit_service
from .tare_versions import contracts as window_contract

PRESET = Path(__file__).resolve().parents[2] / 'sample_data' / 'scale_slips_sample.json'
MODULES = (('scale_slips', '称重签'),
 ('tare_versions', '扣皮版次'),
 ('variance_context', '称差因素'),
 ('tare_deviation', '扣皮异常'),
 ('basket_backtest', '称差回放'),
 ('store_mix', '秤台分组'),
 ('bench_reweigh', '复秤分派'),
 ('weigh_journal', '称差结算'))
DISPLAY = {'title': '商超散称称差稽核',
 'object_name': '散称签',
 'unit': '异常分',
 'role': '门店散称巡查员',
 'endpoint': 'weighttally',
 'identity': 'WEIGH RECEIPT',
 'location': '门店质管 · 散称结算',
 'visual': '分店称差核对',
 'queue': '称差复秤联',
 'resource': '复秤值班位',
 'action': '安排称差复秤',
 'lane': 'L9',
 'field_title': '逐票复秤凭证'}


def open_fixture(path=PRESET):
    document = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(document, dict) or not isinstance(document.get('records'), list):
        raise ValueError('样例必须包含 records 数组')
    if len(document['records']) > 2500:
        raise ValueError('单次导入最多处理 2500 条单据')
    return document


def stage_at(index, details, records, issues=()):
    code, title = MODULES[index]
    return {'key': code, 'title': title, 'summary': details, 'records': list(records), 'errors': list(issues)}


def rows_for(plan, scored, vectors):
    by_key = {item.key: item for item in scored}
    factor_names = ('相对实称差', '扣皮比', '退秤比', '温漂因子', '分拣格负荷')
    order = []
    for job in plan.jobs:
        point = by_key[job.key]
        if len(point.contributions) == len(factor_names):
            reasons = sorted(zip(factor_names, point.contributions, strict=True), key=lambda val: (-abs(val[1]), val[0]))
            driver = ' · '.join(f'{key} {amount:+.2f}' for key, amount in reasons[:2])
        else:
            driver = ' · '.join(f'{amount:+.2f}' for amount in point.contributions)
        interval = ('–' if job.lower is None else f'{job.lower:.2f}–{job.upper:.2f}')
        order.append({'key': job.key, 'zone': job.cohort, 'estimate': job.estimate, 'interval': interval,
                      'state': job.state, 'cost': job.cost, 'reason': job.reason, 'evidence': job.summary,
                      'drivers': driver, 'missing': len(point.missing), 'hits': list(job.rule_hits),
                      'measurements': dict(zip(('ticket_g', 'actual_g', 'tare_g', 'temp_c', 'bins', 'return_g'), point.input_values, strict=True)),
                      'unmeasured': list(point.missing), 'operations': feature_service.business_factors(vectors[job.key])})
    return order


def comparison_rows(predictions):
    return [{'单号': point.key, '分组': point.cohort, '原始估计': round(point.score, 4),
             '补值字段': len(point.missing), '偏离特征': '、'.join(point.excursions) or '—'}
            for point in predictions[:14]]


def replay_metrics(report):
    result = [{'label': '回放实绩样本', 'value': report.count}, {'label': '回放绝对误差', 'value': report.mae}]
    return result


class ShiftDossier:
    def __init__(self, request, as_of):
        self.raw_forms = request
        self.calendar = replace(window_contract.WindowRule.standard(allow_censor=False),as_of=as_of)
        self.accepted = intake_service.load_samples(request,as_of)
        self.history = cohort_service.build_windows(self.accepted.entries,self.calendar)
        cohort_service.model_inputs(self.history)
        self.feature_stamp = feature_service.fit_features(self.history.train)
        self.prepared = feature_service.transform_windows(self.history,self.feature_stamp)
        self.forecaster = model_service.fit_model(self.prepared.train,self.feature_stamp.fingerprint)

    def grading(self):
        predictions = {}
        for name, points in self.prepared.segments():
            if name != 'train':
                predictions[name] = model_service.predict(self.forecaster,points,self.feature_stamp.fingerprint)
        checked = calibration_service.prepare_verification(predictions['calibration'])
        return checked, predictions

    def verification(self, observed, calibration):
        holdout = calibration_service.validate_predictions(observed['replay'],calibration)
        assignment = calibration_service.validate_predictions(observed['live'],calibration)
        prepared = self.prepared
        baseline = monitor_service.fit_baseline(prepared.train,self.feature_stamp.fingerprint)
        detection = monitor_service.scan_current(baseline,prepared.live,self.feature_stamp.fingerprint)
        return holdout, assignment, detection

    def seal(self, plan, mode):
        return audit_service.close_batch(self.raw_forms,self.accepted,self.history,plan,self.feature_stamp.fingerprint,self.forecaster.name,mode)


def execute(documents, capacity=12, mode='balanced', *, as_of=96):
    if type(as_of) is not int or as_of not in range(91,3651):
        raise ValueError('截至工日超出当前排班表')
    if not isinstance(documents,(tuple,list)) or not 1<=len(documents)<=2500:
        raise ValueError('需要 1 至 2500 份可识别单据')
    dossier = ShiftDossier(documents,as_of)
    fitted_calibration, estimates = dossier.grading()
    evaluated, checked_live, drift = dossier.verification(estimates,fitted_calibration)
    allocation = dispatch_service.plan_jobs(checked_live,drift.domain,capacity,mode)
    closed = dossier.seal(allocation,mode)
    intake,windows,state,features,kernel = dossier.accepted,dossier.history,dossier.feature_stamp,dossier.prepared,dossier.forecaster
    scored = estimates['live']
    performance = calibration_service.performance(evaluated)
    coverage = monitor_service.coverage_by_group(features.calibration,features.live)
    states = dict(closed.totals.states)
    overview = [
        {'label': '当班散称签', 'value': len(allocation.jobs)},
        {'label': '已分派', 'value': states.get('已分派', 0)},
        {'label': '候补', 'value': states.get('候补', 0)},
        {'label': '暂停及人工判读', 'value': states.get('暂停', 0) + states.get('人工判读', 0)},
        {'label': '额度结余', 'value': allocation.balance},
    ]
    vectors = {item.key: item for item in features.live}
    row_list = rows_for(allocation, scored, vectors)
    operating_rows = dispatch_service.operating_ledger(row_list)
    overtime = calibration_service.boundary_diagnostics(evaluated, 0.6)
    sector = calibration_service.sector_replay(evaluated, 0.6)
    operating_shift = monitor_service.shop_floor_shift(features.train, features.live)
    field_evidence = audit_service.sign_field_evidence(row_list, allocation)
    features_glance = feature_service.feature_evidence(state) + feature_service.measure_review(features)
    weight_rows = [{'量测': key, '取值': value} for key, value in kernel.evidence]
    ignored = [issue.evidence() for issue in intake.issues]
    details = [
        stage_at(0, f'接收 {intake.source_rows} 条，采用 {len(intake.entries)} 条', intake_service.preliminary_evidence(intake), ignored),
        stage_at(1, f'拟合 {len(windows.train)} 条，校准 {len(windows.calibration)} 条，回放 {len(windows.replay)} 条', cohort_service.window_evidence(windows) + cohort_service.readiness_evidence(windows, as_of)),
        stage_at(2, '特征转换版本 ' + state.fingerprint, features_glance),
        stage_at(3, kernel.name, weight_rows + model_service.inspection_rows(kernel, features) + comparison_rows(scored)),
        stage_at(4, f'{fitted_calibration.method} · {performance.status} · {performance.count} 条回放实绩', calibration_service.calibration_evidence(performance) + [overtime] + sector),
        stage_at(5, f'{drift.status} · {len(drift.domain)} 张单据需外推判读', monitor_service.shift_evidence(drift, coverage) + operating_shift),
        stage_at(6, f'本班占用 {allocation.capacity-allocation.balance} / {allocation.capacity} 个工位单位', dispatch_service.action_evidence(allocation) + dispatch_service.operating_group(checked_live, allocation)),
        stage_at(7, f'处置凭证 {closed.stamp} · 额度守恒', audit_service.reconciliation_evidence(closed) + field_evidence['执行业务单']),
    ]
    details[6]['operating_rows'] = operating_rows
    details[6]['operating_title'] = '逐票复秤凭证'
    points = [{'label': row['key'], 'value': row['estimate'], 'state': row['state'], 'zone': row['zone'],
               'upper': row['interval'], 'cost': row['cost']} for row in sorted(row_list, key=lambda row: row['key'])]
    def estimate(vector):
        return calibration_service.check_point(model_service.predict_one(kernel, vector), fitted_calibration).estimate

    # Compare interventions against frozen features, model and calibration;
    # scenario estimates never overwrite the base ticket or its decision.
    for row in row_list:
        current = vectors[row['key']]
        row['alternatives'] = feature_service.render_interventions(current, state, estimate)
        row['joint_experiments'] = feature_service.render_joint_experiments(current,state,estimate)
    details[7]['records'].extend(audit_service.site_checklist(row_list))
    details[7]['records'].extend(audit_service.intervention_summary(row_list))
    overview_report = {'capacity' : capacity, 'mode': mode, 'as_of': as_of, 'sample_hash': closed.batch_hash,
              'policy_hash': closed.policy_hash, 'feature_stamp': state.fingerprint,
              'model': kernel.name, 'run_id': closed.stamp, 'object_name': DISPLAY['object_name'],
              'unit': DISPLAY['unit'], 'sections': details, 'flow_counts': list(states.items()),
              'measures': {'ticket_g': ('标签重量', 'g'),
 'actual_g': ('抽秤实际', 'g'),
 'tare_g': ('扣皮重量', 'g'),
 'temp_c': ('秤台温度', '℃'),
 'bins': ('称台分拣格', '格'),
 'return_g': ('退秤扣减', 'g')}, 'metrics': overview, 'performance': replay_metrics(performance), 'rows': row_list, 'series': points}
    return overview_report


def preview(capacity=12, mode='balanced'):
    fixture = open_fixture()
    return execute(fixture['records'], capacity, mode, as_of=fixture['as_of'])
