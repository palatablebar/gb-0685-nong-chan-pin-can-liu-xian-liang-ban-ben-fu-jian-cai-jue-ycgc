from copy import deepcopy
from app.modules.m6_reconcile.compare import balance
from app.workflow import run,load

def test_count_conservation(state):
    assert state['reconcile']['balanced'] is True
def test_input_total(state):
    r=state['reconcile'];assert r['input']==r['accepted']+r['isolated']+r['blank']+r['headers']+r['duplicates']
def test_quarantine_visible(state):
    assert state['reconcile']['isolated']>=4
def test_broken_count_detected(state):
    s=deepcopy(state);s['input_count']+=1;assert balance(s)['balanced'] is False
def test_clean_count():
    s=run(load('clean.csv'),{});assert s['reconcile']['balanced'] and s['reconcile']['isolated']==0
def test_business_has_totals(state):
    assert state['reconcile']['business'] and 'total' in state['reconcile']['business']
def test_no_evidence_lost(state):
    assert all(r['line']>=2 and r['code'] for r in state['quarantine'])
