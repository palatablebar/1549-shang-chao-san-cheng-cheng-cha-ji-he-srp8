from math import exp, log, fsum, sqrt
from statistics import median, mean, quantiles

from .mad_model import score_kernel



def explain_tare_deviation(fit, calibration, replay, live):
    truth = []
    for receipt in replay:
        if receipt.outcome is None:
            continue
        actual_units = receipt.input_values[1] - receipt.input_values[2] + receipt.input_values[-1]
        gram_debit = actual_units - receipt.input_values[0]
        predicted, causes = score_kernel(fit.parameters,receipt)
        sensitivity = causes[0]/max(1,max(causes[1:]))
        truth.append({'散称签':receipt.key,'净量差克数':round(gram_debit,2),'净差主导强度':round(sensitivity,3),
                      '异常估计':round(predicted,3),'复秤确认':bool(receipt.outcome)})
    return sorted(truth,key=lambda row:-abs(row['净量差克数']))[:12]
