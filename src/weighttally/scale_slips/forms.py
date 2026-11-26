from collections.abc import Mapping
from decimal import Decimal

from .contracts import MeasureIssue


from dataclasses import dataclass


def form_number(form, sheet, name, minimum, maximum):
    from .service import number

    table = form.get(sheet)
    if not isinstance(table, Mapping):
        raise MeasureIssue(sheet, 'FORM_SECTION_REQUIRED')
    return Decimal(str(number(table.get(name), name, minimum, maximum)))


@dataclass(frozen=True, slots=True)
class ScaleSlipsSheet:
    label_mg: Decimal
    scale_mg: Decimal
    tare_mg: Decimal
    probe_deci_c: Decimal
    scale_bins: Decimal
    void_mg: Decimal

    def fields(self):
        return {
            'ticket_g': float(self.label_mg) / 1000,
            'actual_g': float(self.scale_mg) / 1000,
            'tare_g': float(self.tare_mg) / 1000,
            'temp_c': float(self.probe_deci_c) / 10,
            'bins': float(self.scale_bins),
            'return_g': float(self.void_mg) / 1000,
        }

    def validation(self):
        fields = self.fields()
        ticket_g = fields['ticket_g']
        actual_g = fields['actual_g']
        tare_g = fields['tare_g']
        temp_c = fields['temp_c']
        bins = fields['bins']
        return_g = fields['return_g']
        physical_net = actual_g-tare_g
        receipt_difference = physical_net+return_g-ticket_g
        return_fraction = return_g/max(1,actual_g)
        thermal_span = abs(temp_c-24)
        alerts = []
        if physical_net<0:
            alerts.append(('tare_mg', 'TARE_EXCEEDS_GROSS'))
        if return_fraction>1:
            alerts.append(('void_mg', 'RETURN_EXCEEDS_GROSS'))
        if thermal_span>12 and abs(receipt_difference)>1500:
            alerts.append(('probe_deci_c', 'CHECK_SCALE_REFERENCE_BAND'))
        return tuple(alerts)


def read_scale_slips(form):
    return ScaleSlipsSheet(
        label_mg=form_number(form, '散称签面', 'label_mg', 120000, 3300000),
        scale_mg=form_number(form, '散称签面', 'scale_mg', 90000, 3300000),
        tare_mg=form_number(form, '抽秤净毛', 'tare_mg', 6000, 120000),
        probe_deci_c=form_number(form, '抽秤净毛', 'probe_deci_c', 120, 370),
        scale_bins=form_number(form, '退秤补签', 'scale_bins', 2, 21),
        void_mg=form_number(form, '退秤补签', 'void_mg', 0, 155000),
    )


def explicit_rows(form):
    if not isinstance(form, Mapping):
        raise MeasureIssue('form', 'FORM_OBJECT_REQUIRED')
    note = read_scale_slips(form)
    return note.fields(), note.validation()


def check_native_history(source):
    if not isinstance(source, Mapping) or 'form' not in source:
        return source
    if any(key in source for key in ('ticket_g', 'actual_g', 'tare_g', 'temp_c', 'bins', 'return_g')):
        raise MeasureIssue('form','MIXED_FORM_AND_FLAT_READING')
    converted, flags = explicit_rows(source['form'])
    if flags:
        raise MeasureIssue(*flags[0])
    return {**source, **converted}
