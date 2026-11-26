from dataclasses import replace
from statistics import mean, median
from collections import Counter
from math import fsum

from .contracts import FEATURE_NAMES, FEATURE_KEYS, RAW_KEYS


def current_corrected_grams(vector):
    actual_g = vector.input_values[1]
    tare_g = vector.input_values[2]
    return_g = vector.input_values[5]
    return float(actual_g-tare_g+return_g)


def compare_corrected_grams(training, target):
    usual_corrected_grams = take_sample(training, current_corrected_grams)
    recent_corrected_grams = take_sample(target, current_corrected_grams)
    if len(usual_corrected_grams) < 4 or not recent_corrected_grams:
        return {'作业量': '净重加回退秤', '有效读数': len(recent_corrected_grams), '判断': '参考不足'}
    anchor_corrected_grams = median(usual_corrected_grams)
    measured_corrected_grams = median(recent_corrected_grams)
    band_corrected_grams = max(1.0, abs(anchor_corrected_grams)*.2, median(abs(value-anchor_corrected_grams) for value in usual_corrected_grams))
    change_corrected_grams = (measured_corrected_grams-anchor_corrected_grams) / band_corrected_grams
    outside_corrected_grams = sum(abs(value-anchor_corrected_grams)>2.5*band_corrected_grams for value in recent_corrected_grams)
    return {'作业量': '净重加回退秤', '训练参考': round(anchor_corrected_grams, 4), '现场中位': round(measured_corrected_grams, 4),
            '变动': round(change_corrected_grams, 4), '越界量': outside_corrected_grams, '有效读数': len(recent_corrected_grams)}


def current_gross_gap(vector):
    ticket_g = vector.input_values[0]
    actual_g = vector.input_values[1]
    return float(actual_g-ticket_g)


def compare_gross_gap(training, target):
    usual_gross_gap = take_sample(training, current_gross_gap)
    recent_gross_gap = take_sample(target, current_gross_gap)
    if len(usual_gross_gap) < 4 or not recent_gross_gap:
        return {'作业量': '标签到盘面差', '有效读数': len(recent_gross_gap), '判断': '参考不足'}
    anchor_gross_gap = median(usual_gross_gap)
    measured_gross_gap = median(recent_gross_gap)
    ordered_gross_gap = sorted(usual_gross_gap)
    low_gross_gap, high_gross_gap = ordered_gross_gap[len(ordered_gross_gap)//10], ordered_gross_gap[(len(ordered_gross_gap)*9)//10]
    change_gross_gap = measured_gross_gap-anchor_gross_gap
    outside_gross_gap = sum(value<low_gross_gap or value>high_gross_gap for value in recent_gross_gap)
    return {'作业量': '标签到盘面差', '训练参考': round(anchor_gross_gap, 4), '现场中位': round(measured_gross_gap, 4),
            '变动': round(change_gross_gap, 4), '越界量': outside_gross_gap, '有效读数': len(recent_gross_gap)}


def current_customer_gap(vector):
    ticket_g = vector.input_values[0]
    actual_g = vector.input_values[1]
    tare_g = vector.input_values[2]
    return_g = vector.input_values[5]
    return float(actual_g-tare_g+return_g-ticket_g)


def compare_customer_gap(training, target):
    usual_customer_gap = take_sample(training, current_customer_gap)
    recent_customer_gap = take_sample(target, current_customer_gap)
    if len(usual_customer_gap) < 4 or not recent_customer_gap:
        return {'作业量': '净重与标签差', '有效读数': len(recent_customer_gap), '判断': '参考不足'}
    anchor_customer_gap = median(usual_customer_gap)
    measured_customer_gap = median(recent_customer_gap)
    ordered_customer_gap = sorted(usual_customer_gap)
    low_customer_gap, high_customer_gap = ordered_customer_gap[len(ordered_customer_gap)//10], ordered_customer_gap[(len(ordered_customer_gap)*9)//10]
    change_customer_gap = measured_customer_gap-anchor_customer_gap
    outside_customer_gap = sum(value<low_customer_gap or value>high_customer_gap for value in recent_customer_gap)
    return {'作业量': '净重与标签差', '训练参考': round(anchor_customer_gap, 4), '现场中位': round(measured_customer_gap, 4),
            '变动': round(change_customer_gap, 4), '越界量': outside_customer_gap, '有效读数': len(recent_customer_gap)}


def current_label_severity(vector):
    ticket_g = vector.input_values[0]
    actual_g = vector.input_values[1]
    tare_g = vector.input_values[2]
    return_g = vector.input_values[5]
    return float(1000*(actual_g-tare_g+return_g-ticket_g)/ticket_g)


def compare_label_severity(training, target):
    usual_label_severity = take_sample(training, current_label_severity)
    recent_label_severity = take_sample(target, current_label_severity)
    if len(usual_label_severity) < 4 or not recent_label_severity:
        return {'作业量': '差额千克比', '有效读数': len(recent_label_severity), '判断': '参考不足'}
    anchor_label_severity = median(usual_label_severity)
    measured_label_severity = median(recent_label_severity)
    ordered_label_severity = sorted(usual_label_severity)
    low_label_severity, high_label_severity = ordered_label_severity[len(ordered_label_severity)//10], ordered_label_severity[(len(ordered_label_severity)*9)//10]
    change_label_severity = measured_label_severity-anchor_label_severity
    outside_label_severity = sum(value<low_label_severity or value>high_label_severity for value in recent_label_severity)
    return {'作业量': '差额千克比', '训练参考': round(anchor_label_severity, 4), '现场中位': round(measured_label_severity, 4),
            '变动': round(change_label_severity, 4), '越界量': outside_label_severity, '有效读数': len(recent_label_severity)}


def current_paper_tare(vector):
    ticket_g = vector.input_values[0]
    tare_g = vector.input_values[2]
    return float(1000*tare_g/ticket_g)


def compare_paper_tare(training, target):
    usual_paper_tare = take_sample(training, current_paper_tare)
    recent_paper_tare = take_sample(target, current_paper_tare)
    if len(usual_paper_tare) < 4 or not recent_paper_tare:
        return {'作业量': '每公斤扣皮量', '有效读数': len(recent_paper_tare), '判断': '参考不足'}
    anchor_paper_tare = median(usual_paper_tare)
    measured_paper_tare = median(recent_paper_tare)
    band_paper_tare = max(1.0, abs(anchor_paper_tare)*.2, median(abs(value-anchor_paper_tare) for value in usual_paper_tare))
    change_paper_tare = (measured_paper_tare-anchor_paper_tare) / band_paper_tare
    outside_paper_tare = sum(abs(value-anchor_paper_tare)>2.5*band_paper_tare for value in recent_paper_tare)
    return {'作业量': '每公斤扣皮量', '训练参考': round(anchor_paper_tare, 4), '现场中位': round(measured_paper_tare, 4),
            '变动': round(change_paper_tare, 4), '越界量': outside_paper_tare, '有效读数': len(recent_paper_tare)}


def current_actual_drift(vector):
    temp_c = vector.input_values[3]
    return float(temp_c-24)


def compare_actual_drift(training, target):
    usual_actual_drift = take_sample(training, current_actual_drift)
    recent_actual_drift = take_sample(target, current_actual_drift)
    if len(usual_actual_drift) < 4 or not recent_actual_drift:
        return {'作业量': '秤台温度与中点差', '有效读数': len(recent_actual_drift), '判断': '参考不足'}
    anchor_actual_drift = median(usual_actual_drift)
    measured_actual_drift = median(recent_actual_drift)
    ordered_actual_drift = sorted(usual_actual_drift)
    low_actual_drift, high_actual_drift = ordered_actual_drift[len(ordered_actual_drift)//10], ordered_actual_drift[(len(ordered_actual_drift)*9)//10]
    change_actual_drift = measured_actual_drift-anchor_actual_drift
    outside_actual_drift = sum(value<low_actual_drift or value>high_actual_drift for value in recent_actual_drift)
    return {'作业量': '秤台温度与中点差', '训练参考': round(anchor_actual_drift, 4), '现场中位': round(measured_actual_drift, 4),
            '变动': round(change_actual_drift, 4), '越界量': outside_actual_drift, '有效读数': len(recent_actual_drift)}


def current_return_units(vector):
    bins = vector.input_values[4]
    return_g = vector.input_values[5]
    return float(return_g/bins)


def compare_return_units(training, target):
    usual_return_units = take_sample(training, current_return_units)
    recent_return_units = take_sample(target, current_return_units)
    if len(usual_return_units) < 4 or not recent_return_units:
        return {'作业量': '每格退秤分摊', '有效读数': len(recent_return_units), '判断': '参考不足'}
    anchor_return_units = median(usual_return_units)
    measured_return_units = median(recent_return_units)
    band_return_units = max(1.0, abs(anchor_return_units)*.2, median(abs(value-anchor_return_units) for value in usual_return_units))
    change_return_units = (measured_return_units-anchor_return_units) / band_return_units
    outside_return_units = sum(abs(value-anchor_return_units)>2.5*band_return_units for value in recent_return_units)
    return {'作业量': '每格退秤分摊', '训练参考': round(anchor_return_units, 4), '现场中位': round(measured_return_units, 4),
            '变动': round(change_return_units, 4), '越界量': outside_return_units, '有效读数': len(recent_return_units)}


def current_low_net(vector):
    actual_g = vector.input_values[1]
    tare_g = vector.input_values[2]
    return float(float(actual_g-tare_g<90))


def compare_low_net(training, target):
    usual_low_net = take_sample(training, current_low_net)
    recent_low_net = take_sample(target, current_low_net)
    if len(usual_low_net) < 4 or not recent_low_net:
        return {'作业量': '净重是否小于最小档', '有效读数': len(recent_low_net), '判断': '参考不足'}
    anchor_low_net = median(usual_low_net)
    measured_low_net = median(recent_low_net)
    ordered_low_net = sorted(usual_low_net)
    low_low_net, high_low_net = ordered_low_net[len(ordered_low_net)//10], ordered_low_net[(len(ordered_low_net)*9)//10]
    change_low_net = measured_low_net-anchor_low_net
    outside_low_net = sum(value<low_low_net or value>high_low_net for value in recent_low_net)
    return {'作业量': '净重是否小于最小档', '训练参考': round(anchor_low_net, 4), '现场中位': round(measured_low_net, 4),
            '变动': round(change_low_net, 4), '越界量': outside_low_net, '有效读数': len(recent_low_net)}


def take_sample(vectors, measure):
    return tuple(measure(record) for record in vectors if not record.missing)


def measure_variance_context_band(history, daybook):
    yield compare_corrected_grams(history, daybook)
    yield compare_gross_gap(history, daybook)
    yield compare_customer_gap(history, daybook)
    yield compare_label_severity(history, daybook)
    yield compare_paper_tare(history, daybook)
    yield compare_actual_drift(history, daybook)
    yield compare_return_units(history, daybook)
    yield compare_low_net(history, daybook)


def evaluate_shift(training, current):
    return list(measure_variance_context_band(training, current))
