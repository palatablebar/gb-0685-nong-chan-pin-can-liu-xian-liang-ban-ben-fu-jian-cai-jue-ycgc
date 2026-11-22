import sqlite3,json,os,hashlib
from pathlib import Path
from app.errors import DomainError

def connection():
    path=Path(os.environ.get('DB_PATH','data/records.db'));path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10);db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, body TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, decision TEXT NOT NULL DEFAULT "待复核", digest TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    columns={r['name'] for r in db.execute('PRAGMA table_info(runs)').fetchall()}
    if 'digest' not in columns:db.execute('ALTER TABLE runs ADD COLUMN digest TEXT')
    return db

def _digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def save(run_id, body):
    # Serialize completely before touching the store.  An interrupted or partial
    # serialization never reaches the database, so the previous version survives.
    try:
        text=json.dumps(body,ensure_ascii=False,sort_keys=True)
    except (TypeError,ValueError):
        raise DomainError('PERSIST','证据序列化失败，已保留旧版',500)
    digest=_digest(text)
    with connection() as db:
        existing=db.execute('SELECT body FROM runs WHERE id=?',(run_id,)).fetchone()
        if existing is None:
            try:
                db.execute('INSERT INTO runs(id,body,digest) VALUES (?,?,?)',(run_id,text,digest))
                stored=db.execute('SELECT body FROM runs WHERE id=?',(run_id,)).fetchone()
                if stored is None or _digest(stored['body'])!=digest:
                    raise DomainError('PERSIST','证据写入校验失败，已回退旧版',500)
            except Exception:
                db.rollback()
                raise
        # Same input bytes + parameters + rule version + curve registry hash
        # produce the same run id.  Re-running the same source is a no-op: the
        # first stored evidence is returned unchanged, so no second sample
        # result is created and the archived version is never overwritten.
        db.execute("INSERT INTO meta(key,value) VALUES ('latest',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(run_id,))
    return get(run_id)

def get(run_id):
    with connection() as db:r=db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
    if not r:raise DomainError('NOT_FOUND','批次不存在',404)
    body=json.loads(r['body']);body.update(run_id=r['id'],review_version=r['version'],decision=r['decision']);return body

def history():
    with connection() as db:rows=db.execute("SELECT id,version,decision FROM runs ORDER BY CASE WHEN id=(SELECT value FROM meta WHERE key='latest') THEN 0 ELSE 1 END,rowid DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]

def review(run_id, version, decision):
    if decision not in ('通过','退回'):raise DomainError('DECISION','复核状态无效')
    with connection() as db:
        cur=db.execute('UPDATE runs SET version=version+1,decision=? WHERE id=? AND version=?',(decision,run_id,version))
        if cur.rowcount!=1:
            if not db.execute('SELECT 1 FROM runs WHERE id=?',(run_id,)).fetchone():raise DomainError('NOT_FOUND','批次不存在',404)
            raise DomainError('STALE','复核版本已更新，请刷新',409)
    return get(run_id)
