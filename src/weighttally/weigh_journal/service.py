from .work_order import check_weigh_journal as site_checklist
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json

from .control import accountable_plan, document_control
from .contracts import BatchReceipt, LedgerCheck, POLICY_VERSION


def canonical_json(content):
    return json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def data_fingerprint(records):
    # Input ordering and import line numbers are kept in intake evidence.
    # The reference stamp is a separate content identity and ignores input order.
    lines = sorted(canonical_json(record) for record in records)
    return sha256('\n'.join(lines).encode()).hexdigest()


def policy_fingerprint(capacity, mode, feature_id, model_kind):
    inputs = (POLICY_VERSION, capacity, mode, feature_id, model_kind)
    return sha256(canonical_json(inputs).encode()).hexdigest()[:16]


def check_flow(intake, windows, dispatched):
    ledger_keys = {row.key for row in dispatched.jobs}
    live_keys = {row.key for row in windows.live}
    if len(ledger_keys) != len(dispatched.jobs):
        raise ArithmeticError('同一个单据占用了两次处置名额')
    if ledger_keys != live_keys:
        raise ArithmeticError('处置台账与当班对象不一致')
    counts = Counter(item.state for item in dispatched.jobs)
    consumed = sum(item.cost for item in dispatched.jobs if item.state == '已分派')
    if consumed + dispatched.balance != dispatched.capacity:
        raise ArithmeticError('班次额度收支不平')
    if consumed != sum(cost for _, cost in dispatched.used_by_group):
        raise ArithmeticError('班次总账和分区账不平')
    partitioned = sum(len(items) for _, items in windows.partitions())
    if partitioned + len(windows.excluded) != len(intake.entries):
        raise ArithmeticError('入站与分窗记录无法对齐')
    if partitioned + len(windows.excluded) + len(intake.issues) != intake.source_rows:
        raise ArithmeticError('原始单数与分窗单数无法对齐')
    return LedgerCheck(intake.source_rows, len(intake.issues), len(windows.excluded), len(windows.live),
                       dispatched.capacity, consumed, dispatched.balance, tuple(sorted(counts.items())))


def close_batch(dataset, intake, windows, dispatched, feature_id, model_kind, mode):
    receipt = check_flow(intake, windows, dispatched)
    upstream = data_fingerprint(dataset)
    version = policy_fingerprint(dispatched.capacity, mode, feature_id, model_kind)
    decisions = tuple((job.key, job.state, job.cost, job.reason, job.estimate) for job in dispatched.jobs)
    verified = sha256(canonical_json((upstream, version, decisions, asdict(receipt))).encode()).hexdigest()[:16]
    return BatchReceipt(verified, upstream, version, receipt, decisions)


def compare(before, after):
    old = {row[0]: row[1:] for row in before.decisions}
    current = {row[0]: row[1:] for row in after.decisions}
    new = current.keys() - old.keys()
    obsolete = old.keys() - current.keys()
    changed = {key for key in old.keys() & current.keys() if old[key] != current[key]}
    return {'新增': tuple(sorted(new)), '移出': tuple(sorted(obsolete)), '变更': tuple(sorted(changed)),
            '策略变化': before.policy_hash != after.policy_hash, '样本变化': before.batch_hash != after.batch_hash}


def reconciliation_evidence(receipt):
    ledger = receipt.totals
    rows = [{'核对项': '原始记录', '数量': ledger.raw}, {'核对项': '入站隔离', '数量': ledger.isolated},
            {'核对项': '窗口隔离', '数量': ledger.mature_excluded}, {'核对项': '当班对象', '数量': ledger.scored},
            {'核对项': '已用额度', '数量': ledger.resource_used}, {'核对项': '额度结余', '数量': ledger.balance}]
    rows.extend({'核对项': state, '数量': count} for state, count in ledger.states)
    return rows


def sign_field_evidence(rows, allocation):
    counts, spent = accountable_plan(rows, allocation.balance, allocation.capacity)
    if dict(counts) != dict(Counter(job.state for job in allocation.jobs)):
        raise ArithmeticError('展示单据和签发方案的处置统计不符')
    selected = {row['key']: row['cost'] for row in rows if row['state'] == '已分派'}
    original = {job.key: job.cost for job in allocation.jobs if job.state == '已分派'}
    if selected != original:
        raise ArithmeticError('分派凭证与作业单互相矛盾')
    return {'工位使用':spent, '执行业务单':document_control(rows)}


def intervention_summary(rows):
    actions = {}
    for record in rows:
        for sample in record['alternatives']:
            label = sample['情形']
            observed = actions.setdefault(label,[0,0,0,0])
            observed[0] += 1
            observed[1] += bool(sample['超训练域'])
            observed[2] += sample['用量']
            observed[3] += sample['预测变化']
    return [{'单项安排': key, '可比较单量': attempts, '超出拟合域': outlier,
             '总用量': units, '平均预测变化': round(delta/attempts,4)}
            for key,(attempts,outlier,units,delta) in sorted(actions.items())]
