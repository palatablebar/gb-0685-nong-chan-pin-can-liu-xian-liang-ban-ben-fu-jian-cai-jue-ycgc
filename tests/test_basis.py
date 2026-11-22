import json
import pytest
from app import store
from app.errors import DomainError
from app.workflow import load, run
from app.modules.m7_archive.export_out import bundle, conclusion


def curve_state():
    return run(load('curve_change.csv'), {})


def test_conflicting_basis_is_not_spliced():
    s = curve_state()
    b = next(x for x in s['basis'] if x['sample_id'] == 'S501')
    assert b['reason'] == 'BASIS_CONFLICT' and b['decision'] == 'UNCERTAIN'
    # Both original signals survive with the dilution each was actually run at.
    assert {q['report_id']: q['dilution'] for q in b['quantifications']} == {'00501': '10', '00502': '1'}
    # Both curve versions survive; the SAME current curve re-quantifies both.
    assert {q['source_curve'] for q in b['quantifications']} == {'P01-2026A', 'P01-2026B'}
    assert {q['current_curve'] for q in b['quantifications']} == {'P01-2026B'}
    # The adopted interval is the envelope of both valid measurements, not one
    # report's range glued onto the other report's dilution.
    assert b['lower'] != b['upper']


def test_sample_verdict_matches_interval_rule():
    s = curve_state()
    c = next(x for x in s['calculations'] if x['sample_id'] == 'S501')
    assert c['code'] == 'UNCERTAIN' and c['basis'] == 'BASIS_CONFLICT'
    assert c['lower'] == '0.00419048' and c['upper'] == '0.0051' and c['limit'] == '0.005'


def test_initial_signal_requantified_on_current_curve_not_copied():
    s = curve_state()
    b = next(x for x in s['basis'] if x['sample_id'] == 'S501')
    initial = next(q for q in b['quantifications'] if q['report_id'] == '00501')
    # 0.45 signal on curve B: (0.45-0.01)/1050 = 0.0004190476 mg/kg in vial,
    # multiplied by the report's own 10x dilution -- not the retest's 1x.
    assert initial['source_original'] == '0.0045'
    assert initial['current_original'] == '0.00419047619047619047619047619'
    assert initial['current_code'] == 'PASS'


def test_stable_sample_uses_current_curve():
    s = curve_state()
    for sid in ('S502', 'S503'):
        c = next(x for x in s['calculations'] if x['sample_id'] == sid)
        assert c['basis'] == 'SINGLE_VALID' and c['code'] == 'PASS' and c['curve'] == 'P01-2026B'


def test_batch_risk_and_seal_follow_the_same_basis():
    s = curve_state()
    grades = {g['batch']: g for g in s['reconcile']['grades']}
    assert grades['B501']['code'] == 'UNCERTAIN' and grades['B501']['conflict'] == 1
    assert grades['B502']['code'] == 'PASS'
    seal = {x['batch']: x for x in s['reconcile']['seal_scope']}
    assert seal['B501']['sealed'] is True and seal['B501']['samples'] == ['S501', 'S502']
    assert seal['B501']['driver_samples'] == ['S501']
    assert seal['B502']['sealed'] is False
    # The sealed batch contains every sample in it; the driving risky sample is
    # recorded separately so the seal can be traced back to the basis conflict.
    drivers = {r['sample_id'] for r in s['calculations'] if r['batch'] == 'B501' and r['code'] != 'PASS'}
    assert set(seal['B501']['driver_samples']) == drivers


def test_basis_derived_from_one_calculation_table():
    s = curve_state()
    # Every calculation row is the sample/analyte decision derived from the basis.
    for c in s['calculations']:
        b = next(x for x in s['basis'] if (x['batch'], x['sample_id'], x['analyte']) == (c['batch'], c['sample_id'], c['analyte']))
        assert c['code'] == b['decision'] and (c['lower'], c['upper']) == (b['lower'], b['upper'])


def test_evidence_keeps_signals_dilutions_and_both_curves():
    s = curve_state()
    text = bundle(s)
    for token in ('0.45', '5.365', '10', 'P01-2026A', 'P01-2026B', '依据', '封存范围'):
        assert token in text
    body = conclusion(s)
    assert body['seal_scope'] and body['decisions']
    assert body['curve_registry_sha256'] == s['manifest']['curve_registry_sha256']


def test_same_source_rerun_adds_no_sample_result(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'r.db'))
    s1 = run(load('curve_change.csv'), {})
    s2 = run(load('curve_change.csv'), {})
    assert s1['run_id'] == s2['run_id']
    first = store.save(s1['run_id'], s1)
    second = store.save(s2['run_id'], s2)
    assert first['run_id'] == second['run_id']
    assert len(store.history()) == 1
    assert len(store.get(s1['run_id'])['calculations']) == len(s1['calculations'])
    # The archived evidence is the first write and is not rewritten by the rerun.
    assert store.get(s1['run_id'])['archive']['sha256'] == s1['archive']['sha256']


def test_interrupted_write_keeps_previous_version(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'r.db'))
    s = curve_state()
    store.save(s['run_id'], s)
    original = store.get(s['run_id'])['archive']['sha256']

    def explode(*args, **kwargs):
        raise TypeError('interrupted')

    with monkeypatch.context() as patch:
        patch.setattr(store.json, 'dumps', explode)
        with pytest.raises(DomainError):
            store.save(s['run_id'], dict(s, tampered=True))
    after = store.get(s['run_id'])
    assert after['archive']['sha256'] == original and 'tampered' not in after


def test_curve_scope_quarantines_foreign_curve():
    raw = ('id,sample_id,batch,product,analyte,method,version,sampled,reported,result,unit,lod,relation,note,curve_id,curve_version,signal,dilution\n'
           '00901,S901,B901,苹果,P01,LC-MS/MS,1,2026-08-01,2026-08-04,0.002,mg/kg,0.0005,,,P01-2026A,1,2.11,1\n').encode()
    s = run(raw, {})
    assert any(q['code'] == 'CURVE' for q in s['quarantine'])
    assert s['calculations'] == []


def test_adjudication_date_parameter_selects_curve():
    raw = load('curve_change.csv')
    s = run(raw, {'adjudication_date': '2026-08-02'})
    assert s['adjudication_date'] == '2026-08-02'
    # On 2026-08-02 the current approved curve is the older A release.
    b = next(x for x in s['basis'] if x['sample_id'] == 'S502')
    assert b['current_curve']['curve_id'] == 'P01-2026A'


def test_no_current_curve_yields_no_basis_not_old_curve():
    s = run(load('curve_change.csv'), {'adjudication_date': '2027-06-01'})
    assert s['basis_summary']['no_basis'] == 3
    assert all(b['decision'] == 'UNCERTAIN' and b['current_curve'] is None for b in s['basis'])
    # Every original signal and dilution is still preserved for review.
    assert all(q['signal'] and q['dilution'] for b in s['basis'] for q in b['quantifications'])


def test_invalid_adjudication_date_rejected():
    raw = load('curve_change.csv')
    with pytest.raises(DomainError) as e:
        run(raw, {'adjudication_date': 'not-a-date'})
    assert e.value.code == 'PARAMETERS'


def test_mixed_curve_and_legacy_rows_have_no_common_basis():
    raw = ('id,sample_id,batch,product,analyte,method,version,sampled,reported,result,unit,lod,relation,note,curve_id,curve_version,signal,dilution\n'
           '0001,S9,B9,苹果,P01,LC-MS/MS,1,2026-08-01,2026-08-04,0.003,mg/kg,0.0005,,,P01-2026B,2,3.16,1\n'
           '0002,S9,B9,苹果,P01,LC-MS/MS,2,2026-08-01,2026-08-05,0.004,mg/kg,0.001,0001,,,,,\n').encode()
    s = run(raw, {})
    b = s['basis'][0]
    assert b['reason'] == 'MIXED_BASIS' and b['decision'] == 'UNCERTAIN'
    # Both reports stay in the evidence; the legacy row is flagged as lacking a signal.
    assert {q['report_id']: q['error'] for q in b['quantifications']} == {'0001': None, '0002': 'NO_SIGNAL'}


def test_conclusion_download_matches_archive(client):
    s = client.post('/api/runs', json={'sample': 'curve_change.csv'}).get_json()
    r = client.get('/api/archive/' + s['run_id'] + '/conclusion.json')
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body['seal_scope'] == s['reconcile']['seal_scope']
    assert body['curve_registry_sha256'] == s['manifest']['curve_registry_sha256']
    assert r.headers['X-Evidence-SHA256'] == s['archive']['sha256']
    csv = client.get('/api/archive/' + s['run_id'] + '/export.csv')
    assert csv.status_code == 200 and 'P01-2026A' in csv.data.decode('utf-8-sig')


def test_curve_change_pages_render(client):
    client.post('/api/runs', json={'sample': 'curve_change.csv'})
    for mod in ('m4_segments', 'm5_calculate', 'm6_reconcile', 'm7_archive'):
        r = client.get('/' + mod + '?sample=curve_change.csv')
        assert r.status_code == 200
