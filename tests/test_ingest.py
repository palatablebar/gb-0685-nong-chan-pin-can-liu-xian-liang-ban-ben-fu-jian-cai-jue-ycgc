import pytest
from app.workflow import load
from app.modules.m1_ingest.reader import read
from app.errors import DomainError

def test_bom(raw):
    # TRAP-02
    assert 'id' in read(raw)['rows'][0]
def test_legacy_encoding():
    # TRAP-01
    assert read(load('legacy.csv'))['encoding']=='gb18030'
def test_width_isolation(raw):
    # TRAP-05
    assert any(r['code']=='WIDTH' for r in read(raw)['quarantine'])
def test_logical_rows(raw):
    # TRAP-03
    result=read(raw);assert result['input_count']>=35 and result['rows'][0]['_line']>=2
def test_empty_three_states():
    # TRAP-18
    for data,code in [(b'','EMPTY_FILE'),(b'\n \n','BLANK_FILE')]:
        with pytest.raises(DomainError) as e:read(data)
        assert e.value.code==code
    from app.config import REQUIRED
    with pytest.raises(DomainError) as e:read((','.join(REQUIRED)+'\n').encode())
    assert e.value.code=='HEADER_ONLY'
def test_missing_header():
    with pytest.raises(DomainError) as e:read(b'wrong\n1\n')
    assert e.value.code=='HEADER'
def test_preserves_multiline_note(raw):
    result=read(raw);assert any('\n' in r.get('note','') for r in result['rows'])
