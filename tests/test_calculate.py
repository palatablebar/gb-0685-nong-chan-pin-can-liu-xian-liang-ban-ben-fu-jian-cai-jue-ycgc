from copy import deepcopy
from app.workflow import run
from app.modules.m5_calculate.rules import select_reports,apply

def test_real_retest_replaces_initial(raw):
    s=run(raw,{});assert len(s['calculations'])==24 and s['calculations'][0]['id']=='00002' and s['calculations'][0]['replaces']=='00001'
def test_real_other_analyte_not_erased(raw):
    s=run(raw,{});assert s['business']=={'total':24,'pass':12,'fail':12,'uncertain':0,'unit':'检测项目'}
def test_wrong_sample_reference_rejected(raw):
    s=run(raw,{},4);s['measurements'][1]['sample_id']='OTHER';chosen,bad=select_reports(s['measurements']);assert bad['00002']=='REFERENCE' and any(r['id']=='00001' for r in chosen)
def test_wrong_method_reference_rejected(raw):
    s=run(raw,{},4);s['measurements'][1]['method']='GC-MS';_,bad=select_reports(s['measurements']);assert bad['00002']=='REFERENCE'
def test_future_reference_rejected(raw):
    s=run(raw,{},4);s['measurements'][1]['reported']='2026-08-01';_,bad=select_reports(s['measurements']);assert bad['00002']=='REFERENCE'
def test_cycle_rejected(raw):
    # TRAP-20
    s=run(raw,{},4);s['measurements'][0]['relation']='00002';_,bad=select_reports(s['measurements']);assert '00001' in bad and '00002' in bad
def test_input_order_cannot_change_verdict(raw):
    a=run(raw,{},4);b=deepcopy(a);b['measurements'].reverse();ca,ba=select_reports(a['measurements']);cb,bb=select_reports(b['measurements']);assert sorted(r['id'] for r in ca)==sorted(r['id'] for r in cb) and ba==bb


def test_same_report_id_latest_revision_is_authoritative(raw):
    s=run(raw,{},4);new=dict(s['measurements'][1],version='3',lower='0.006',upper='0.006',code='FAIL');s['measurements'].append(new);chosen,bad=select_reports(s['measurements'])
    assert next(r for r in chosen if r['id']=='00002')['code']=='FAIL' and '00002' not in bad
