import hashlib,json,time
from datetime import datetime,timezone
from pathlib import Path
from app.config import RULE_VERSION

CURVES=Path(__file__).resolve().parents[1]/'sample_data'/'curves.csv'

def curve_registry():
    """Exact bytes and digest of the calibration registry used for this run."""
    raw=CURVES.read_bytes()
    return raw,hashlib.sha256(raw).hexdigest()

def identity(content, parameters):
    _,digest=curve_registry()
    raw = content + json.dumps(parameters,sort_keys=True,ensure_ascii=False).encode() + RULE_VERSION.encode() + digest.encode()
    return hashlib.sha256(raw).hexdigest()[:20]

def manifest(content, parameters, elapsed):
    raw,digest=curve_registry()
    return {'sha256':hashlib.sha256(content).hexdigest(),'rule_version':RULE_VERSION,
        'parameters':parameters,'elapsed_ms':round(elapsed*1000),
        'curve_registry_sha256':digest,'curve_registry':raw.decode('utf-8-sig'),
        'generated_at':datetime.now(timezone.utc).isoformat(),'timezone':'Asia/Shanghai'}
