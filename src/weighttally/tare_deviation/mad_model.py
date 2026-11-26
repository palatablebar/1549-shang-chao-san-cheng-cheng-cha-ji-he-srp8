from collections import defaultdict
from math import expm1
from statistics import median


def robust_reference(vectors):
    columns = tuple(zip(*vectors, strict=True))
    centres = tuple(median(values) for values in columns)
    mad = tuple(median(abs(point - anchor) for point in values) for values, anchor in zip(columns, centres, strict=True))
    return centres, tuple(max(.11, 1.4826 * value) for value in mad)


def fit_kernel(rows):
    known = tuple(record for record in rows if record.outcome < .5)
    if len(known) < 8:
        known = tuple(rows)
    location = defaultdict(list)
    for item in known:
        location[item.cohort].append(item.values)
    overall = robust_reference(tuple(item.values for item in known))
    calibrated = tuple((name, robust_reference(vectors)) for name, vectors in sorted(location.items()) if len(vectors) >= 10)
    return (overall, calibrated), (('组内标定台', len(calibrated)), ('正常基线票', len(known)))


def score_kernel(references, sample):
    chain, local = references
    location, scale = dict(local).get(sample.cohort, chain)
    z = tuple(abs(v - m) / s for v,m,s in zip(sample.values, location, scale, strict=True))
    combined = max(z[0], .44 * max(z[1:]))
    return -expm1(-max(0, combined - 1) / 2.1), z
