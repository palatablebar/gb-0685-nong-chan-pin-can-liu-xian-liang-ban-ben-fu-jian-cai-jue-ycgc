import csv
from pathlib import Path
from decimal import Decimal, InvalidOperation
from app.errors import DomainError

PATH = Path(__file__).resolve().parents[3] / 'sample_data' / 'curves.csv'


def registry():
    """Read the calibration registry as strings so the snapshot is loss-free."""
    with PATH.open(encoding='utf-8-sig', newline='') as f:
        return [dict(row) for row in csv.DictReader(f)]


def get(curve_id, rows=None):
    rows = registry() if rows is None else rows
    found = [c for c in rows if c['curve_id'] == curve_id]
    if len(found) != 1:
        raise DomainError('CURVE', '校准曲线缺失或重复')
    return found[0]


def applicable(curve, analyte, method, reported):
    """A curve may quantify a report only inside its own analyte/method/date scope."""
    if curve['analyte'] != analyte or curve['method'] != method:
        raise DomainError('CURVE', '校准曲线与残留项目或方法不匹配')
    if curve.get('status') != 'approved':
        raise DomainError('CURVE', '校准曲线未批准')
    if not (curve['effective_from'] <= reported < curve['effective_to']):
        raise DomainError('CURVE', '报告日期不在校准曲线有效期内')
    return curve


def current_for(analyte, method, on_date, rows=None):
    """Exactly one approved curve effective on the adjudication date, else None."""
    rows = registry() if rows is None else rows
    hits = [c for c in rows if c['analyte'] == analyte and c['method'] == method
            and c.get('status') == 'approved'
            and c['effective_from'] <= on_date < c['effective_to']]
    if len(hits) == 1:
        return hits[0]
    return None


def _dec(value, code='CURVE'):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise DomainError(code, '校准曲线数值无效')
    if not result.is_finite():
        raise DomainError(code, '校准曲线数值无效')
    return result


def dstr(value):
    text = format(value.normalize(), 'f')
    return '0' if text in ('-0', '') else text


def quantify(signal, dilution, curve):
    """Re-quantify a preserved raw signal on a named curve.

    concentration in the injected solution = (signal - intercept) / slope;
    concentration in the original sample = that x recorded dilution factor.
    The recorded dilution is a physical fact of that report, never borrowed
    from another report.
    """
    signal = _dec(signal, 'SIGNAL')
    dilution = _dec(dilution, 'SIGNAL')
    slope = _dec(curve['slope'])
    intercept = _dec(curve['intercept'])
    low = _dec(curve['range_low'])
    high = _dec(curve['range_high'])
    max_dilution = _dec(curve['max_dilution'])
    if signal < 0 or dilution <= 0:
        raise DomainError('SIGNAL', '原始信号或稀释倍数无效')
    if dilution > max_dilution:
        raise DomainError('RANGE', '稀释倍数超出校准曲线允许范围')
    if slope == 0:
        raise DomainError('CURVE', '校准曲线斜率无效')
    in_solution = (signal - intercept) / slope
    if in_solution < low or in_solution > high:
        raise DomainError('RANGE', '原始信号超出校准曲线量程')
    if in_solution < _dec(curve['lod_mgkg']):
        raise DomainError('RANGE', '原始信号低于校准曲线检出限')
    original = in_solution * dilution
    return {'curve_id': curve['curve_id'], 'curve_version': curve['curve_version'],
            'signal': dstr(signal), 'dilution': dstr(dilution),
            'in_solution': dstr(in_solution), 'original': dstr(original),
            'in_solution_display': _display(in_solution), 'original_display': _display(original),
            'range_low': curve['range_low'], 'range_high': curve['range_high'],
            'lod_mgkg': curve['lod_mgkg'], 'max_dilution': curve['max_dilution']}


def _display(value):
    """Six significant figures for the worksheet; the exact value decides."""
    quantized = Decimal(str(value)).normalize()
    if quantized == 0:
        return '0'
    exponent = quantized.adjusted()
    places = max(0, 5 - exponent)
    return dstr(quantized.quantize(Decimal(1).scaleb(-places)))
