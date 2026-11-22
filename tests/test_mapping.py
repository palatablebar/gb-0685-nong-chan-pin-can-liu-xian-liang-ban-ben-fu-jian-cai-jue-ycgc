from decimal import Decimal
import pytest
from app.workflow import run
from app.modules.m2_mapping.coerce import number
from app.errors import DomainError

def test_thousands():
    # TRAP-06
    assert number('１,２３４.５')==Decimal('1234.5')
def test_missing_numeric():
    # TRAP-07
    with pytest.raises(DomainError) as e:number('N/A')
    assert e.value.code=='MISSING'
def test_identifier_zeroes(raw):
    # TRAP-08
    assert run(raw,{},2)['rows'][0]['id'].startswith('00')
def test_real_missing_quarantine(raw):
    s=run(raw,{},2);assert any(r['code']=='MISSING' for r in s['quarantine'])
def test_real_conflict_quarantine(raw):
    # TRAP-14
    s=run(raw,{},2);assert sum(r['code']=='CONFLICT' for r in s['quarantine'])==2
def test_real_deduplication(raw):
    s=run(raw,{},2);assert s['duplicate_count']==1
def test_decimal_precision():
    # TRAP-10
    assert sum([number('0.1')]*1000)==Decimal('100.0')
