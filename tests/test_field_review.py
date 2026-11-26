from weighttally.pipeline import preview
from weighttally.bench_reweigh.service import operating_ledger


def note(key, measures, *, zone='甲区', state='已分派', estimate=0, hits=(), missing=()):
    return {'key':key,'zone':zone,'state':state,'estimate':estimate,'hits':hits,
            'unmeasured':missing,'measurements':dict(zip(('ticket_g', 'actual_g', 'tare_g', 'temp_c', 'bins', 'return_g'),measures,strict=True))}


def test_field_plan_is_visible_and_references_real_tickets():
    desk = preview()
    plan = desk['sections'][6]
    assert plan['operating_title'] == '逐票复秤凭证'
    assert plan['operating_rows']
    scoped = {item['关联单据'] for item in plan['operating_rows'] if '关联单据' in item}
    assert scoped and scoped <= {row['key'] for row in desk['rows']}
    assert all(item['业务安排'] for item in plan['operating_rows'])


def test_invalid_return_mass_is_excluded_from_store_shortfall():
    invalid = note('WT-1',(200,120,90,22,8,42))
    shortage = note('WT-2',(200,203,15,22,8,0))
    result = operating_ledger([invalid, shortage])
    assert result[0]['业务安排']=='净量无法对账'
    assert result[1]['待核克差']==-12
    journal = result[-1]
    assert journal['短量待核克']==12 and journal['不入汇总标签']==1
