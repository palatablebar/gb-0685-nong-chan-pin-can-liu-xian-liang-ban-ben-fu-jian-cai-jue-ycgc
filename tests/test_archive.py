import csv,io
from app import store
from app.modules.m7_archive.export_out import bundle,checksum
from app.workflow import load,run
from app.errors import DomainError
import pytest

def test_export_rows(state):
    rows=list(csv.reader(io.StringIO(bundle(state).lstrip('\ufeff'))));assert rows[0][0]=='记录类型' and rows[1][0]=='运行清单'
def test_export_quarantine(state):
    assert bundle(state).count('隔离')==len(state['quarantine'])
def test_checksum_stable(state):
    assert checksum(state)==state['archive']['sha256'] and len(checksum(state))==64
def test_archive_ready(state):
    assert state['archive']['ready'] is True
def test_idempotent_store(state,tmp_path,monkeypatch):
    monkeypatch.setenv('DB_PATH',str(tmp_path/'r.db'))
    a=store.save(state['run_id'],state);b=store.save(state['run_id'],state)
    assert a['run_id']==b['run_id'] and len(store.history())==1
def test_stale_review(state,tmp_path,monkeypatch):
    # TRAP-26
    monkeypatch.setenv('DB_PATH',str(tmp_path/'r.db'));store.save(state['run_id'],state)
    assert store.review(state['run_id'],1,'通过')['review_version']==2
    with pytest.raises(DomainError) as e:store.review(state['run_id'],1,'退回')
    assert e.value.status==409
def test_persistent_new_connection(state,tmp_path,monkeypatch):
    monkeypatch.setenv('DB_PATH',str(tmp_path/'r.db'));store.save(state['run_id'],state)
    assert store.get(state['run_id'])['calculations']==state['calculations']
