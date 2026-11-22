import os
from pathlib import Path
import pytest
from app.workflow import load,run
@pytest.fixture
def raw():return load('dirty.csv')
@pytest.fixture
def state(raw):return run(raw,{})
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('DB_PATH',str(tmp_path/'test.db'))
    from app.main import create_app
    app=create_app();app.config['TESTING']=True
    return app.test_client()
