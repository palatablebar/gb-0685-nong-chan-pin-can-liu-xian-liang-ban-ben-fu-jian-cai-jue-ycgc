from app.workflow import run
from app.modules.m3_versions.standards import choose,standards
from app.errors import DomainError
import pytest

def test_real_standard_count(raw):assert len(run(raw,{},3)['reports'])==36
def test_sample_time_selects_new_limit(raw):
    r=run(raw,{},3)['reports'][0];assert r['standard_id']=='APL-P01-V2' and r['limit']=='0.005'
def test_old_sample_uses_old_limit(raw):
    r=run(raw,{},2)['rows'][0];r['sampled']='2026-06-30';assert choose(r,standards())['limit']=='0.01'
def test_halfopen_effective(raw):
    # TRAP-25
    r=run(raw,{},2)['rows'][0];r['sampled']='2026-07-01';assert choose(r,standards())['standard_id']=='APL-P01-V2'
def test_overlap_rejected(raw):
    r=run(raw,{},2)['rows'][0];limits=standards();limits.append(dict(limits[1],id='overlap'))
    with pytest.raises(DomainError) as e:choose(r,limits)
    assert e.value.code=='VERSION'
def test_method_must_be_applicable(raw):
    r=run(raw,{},2)['rows'][0];r['method']='GC-MS'
    with pytest.raises(DomainError) as e:choose(r,standards())
    assert e.value.code=='METHOD'
def test_real_all_reported_after_sampling(raw):assert all(r['reported']>=r['sampled'] for r in run(raw,{},3)['reports'])
