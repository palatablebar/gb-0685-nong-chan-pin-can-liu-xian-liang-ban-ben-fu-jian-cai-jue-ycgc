from collections import defaultdict
from datetime import date
from decimal import Decimal
from app.errors import DomainError
from app.modules.m4_segments import curves

GROUP = ('sample_id', 'batch', 'product', 'analyte')


def _display(value):
    return curves._display(value)


def _verdict(value, limit):
    return 'PASS' if value <= limit else 'FAIL'


def _order(row):
    return (row['reported'], Decimal(str(row['version'])), row['id'])


def resolve_group(rows, on_date):
    """Establish one quantitative basis for a sample/project group.

    Every preserved raw signal is re-quantified on the currently approved
    curve, each with the dilution recorded on its own report.  The dilution is
    a physical property of that measurement and is never borrowed from the
    later report; the curve is always the current calibration.  A single value
    is adopted only when the resulting verdicts agree.  When valid signals on
    the same current curve fall on opposite sides of the limit the sample has
    no single basis and is reported indeterminate -- the two measurements are
    never spliced together and neither report is silently preferred.
    """
    rows = sorted(rows, key=_order)
    method = rows[0]['method']
    limit = Decimal(str(rows[0]['limit']))
    current = curves.current_for(rows[0]['analyte'], method, on_date)
    quantifications = []
    for r in rows:
        entry = {'report_id': r['id'], 'reported': r['reported'], 'version': str(r['version']),
                 'source_curve': r.get('curve_id'), 'source_curve_version': r.get('curve_version'),
                 'signal': r.get('signal'), 'dilution': str(r.get('dilution')) if r.get('dilution') not in (None, '') else None,
                 'source_original': r.get('original'), 'source_code': r.get('code'),
                 'current_curve': current['curve_id'] if current else None,
                 'current_original': None, 'current_code': None, 'valid': False, 'error': None}
        if r.get('quantified_by') != 'curve':
            entry['error'] = 'NO_SIGNAL'
        elif current is None:
            entry['error'] = 'CURVE'
        else:
            try:
                q = curves.quantify(r['signal'], r['dilution'], current)
            except DomainError as error:
                entry['error'] = error.code
            else:
                value = Decimal(q['original'])
                entry.update(valid=True, current_original=q['original'], current_original_display=q['original_display'],
                             current_code=_verdict(value, limit), in_solution=q['in_solution'])
        quantifications.append(entry)
    valid = [q for q in quantifications if q['valid']]
    missing = [q for q in quantifications if q['error'] == 'NO_SIGNAL']
    if missing and valid:
        # One group mixing curve-quantified and legacy rows cannot be settled on
        # a single basis: the legacy row has no raw signal to re-quantify.
        decision, reason, chosen = 'UNCERTAIN', 'MIXED_BASIS', None
        lower = upper = None
    elif not valid:
        decision, reason, chosen = 'UNCERTAIN', 'NO_VALID_BASIS', None
        lower = upper = None
    elif len(valid) == 1:
        chosen = valid[0]
        decision, reason = chosen['current_code'], 'SINGLE_VALID'
        lower = upper = chosen['current_original_display']
    else:
        codes = {q['current_code'] for q in valid}
        chosen = valid[-1]
        values = sorted(Decimal(q['current_original']) for q in valid)
        # The surviving valid measurements bracket the sample value.  Their
        # envelope is the honest interval while the two disagree; it is not a
        # splice of one report's range with another report's dilution.
        lower, upper = _display(values[0]), _display(values[-1])
        if len(codes) == 1:
            decision, reason = chosen['current_code'], 'AGREE'
        else:
            decision, reason = 'UNCERTAIN', 'BASIS_CONFLICT'
    adopted = chosen['report_id'] if chosen and decision != 'UNCERTAIN' else ('+'.join(q['report_id'] for q in (valid or quantifications)) or rows[-1]['id'])
    record = {'sample_id': rows[0]['sample_id'], 'batch': rows[0]['batch'],
              'product': rows[0]['product'], 'analyte': rows[0]['analyte'], 'method': method,
              'adjudication_date': on_date, 'limit': str(limit),
              'current_curve': current, 'quantifications': quantifications,
              'decision': decision, 'reason': reason, 'lower': lower, 'upper': upper,
              'chosen_report': chosen['report_id'] if chosen and decision != 'UNCERTAIN' else None,
              'adopted_id': adopted,
              'report_ids': [q['report_id'] for q in quantifications]}
    return record


def group_measurements(measurements, bad):
    grouped = defaultdict(list)
    for m in measurements:
        if m['id'] in bad:
            continue
        grouped[(m['sample_id'], m['batch'], m['product'], m['analyte'])].append(m)
    return grouped


def adjudication_date(parameters, measurements):
    """The date on which the "current" curve is fixed.

    It can be pinned by the caller; otherwise the latest report date in the
    batch stands in for the issuance point.  Deriving it from the source rather
    than the wall clock keeps the run id stable, so re-running the same bytes
    cannot silently move a sample onto a different calibration.
    """
    supplied = (parameters or {}).get('adjudication_date')
    if supplied is not None:
        try:
            parsed = date.fromisoformat(str(supplied))
        except ValueError:
            raise DomainError('PARAMETERS', 'adjudication_date 必须是 ISO 日期')
        return parsed.isoformat()
    if not measurements:
        return None
    return max(m['reported'] for m in measurements)


def adjudicate(measurements, chosen, bad, parameters):
    """Split groups into basis-driven and plain reports, keeping both in the tally."""
    grouped = group_measurements(measurements, bad)
    plain = {}
    for r in chosen:
        plain[(r['sample_id'], r['batch'], r['product'], r['analyte'])] = r
    on_date = adjudication_date(parameters, measurements)
    basis = []
    resolved = {}
    for key, rows in grouped.items():
        if any(r.get('quantified_by') == 'curve' for r in rows):
            resolved[key] = resolve_group(rows, on_date)
            basis.append(resolved[key])
    basis.sort(key=lambda b: (b['batch'], b['sample_id'], b['analyte']))
    return basis, resolved, plain, on_date
