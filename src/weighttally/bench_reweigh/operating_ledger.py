from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


def grams(readings, key):
    return Decimal(str(readings[key])).quantize(Decimal('1'),rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class SettlementTrial:
    identifier: str
    label: Decimal
    net: Decimal
    returned: Decimal
    allowed: Decimal
    corrected: Decimal
    issue: str

    def delta(self):
        return self.corrected - self.label


def reconcile_scale(ticket):
    sample = ticket['measurements']
    label = grams(sample,'ticket_g')
    gross = grams(sample,'actual_g')
    tare = grams(sample,'tare_g')
    adjustment = grams(sample,'return_g')
    tolerance = max(Decimal(3), (label * Decimal('.012')).quantize(Decimal(1),rounding=ROUND_HALF_UP))
    if sample['temp_c'] < 16 or sample['temp_c'] > 30:
        tolerance += Decimal(2)
    if tare >= gross or adjustment > gross-tare:
        balance = Decimal(0)
        issue = '净量无法对账'
    else:
        balance = gross-tare-adjustment
        issue = '复秤短量' if label-balance>tolerance else '复秤多量' if balance-label>tolerance else '误差带内'
    return SettlementTrial(ticket['key'],label,gross-tare,adjustment,tolerance,balance,issue)


def operating_ledger(rows):
    review = []
    balances = defaultdict(list)
    for entry in rows:
        if entry['unmeasured'] or entry['state']=='暂停':
            review.append({'业务安排': '冻结标签或补秤', '关联单据': entry['key'], '允许补差结算': False})
            continue
        sample = reconcile_scale(entry)
        balances[entry['zone']].append(sample)
        if sample.issue == '误差带内':
            continue
        review.append({'业务安排': sample.issue, '关联单据': sample.identifier, '门店': entry['zone'],
                       '扣皮后克': int(sample.net), '扣除退秤克': int(sample.returned),
                       '待核克差': int(sample.delta()), '允许误差克':int(sample.allowed),
                       '允许补差结算':False})
    for branch, accounts in sorted(balances.items()):
        usable = [item for item in accounts if item.issue!='净量无法对账']
        negative = sum(-item.delta() for item in usable if item.issue=='复秤短量')
        positive = sum(item.delta() for item in usable if item.issue=='复秤多量')
        review.append({'业务安排': '称差稽核凭证', '门店': branch, '短量待核克':int(negative), '多量待核克':int(positive),
                       '不入汇总标签':len(accounts)-len(usable), '有效复秤张数':len(usable)})
    return review
