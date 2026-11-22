import csv
from pathlib import Path
from decimal import Decimal
from app.errors import DomainError

def standards():
    path=Path(__file__).resolve().parents[3]/'sample_data'/'limits.csv'
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def choose(row, limits):
    candidates=[l for l in limits if l['product']==row['product'] and l['analyte']==row['analyte'] and l['start']<=row['sampled']<l['end']]
    if len(candidates)!=1:raise DomainError('VERSION','采样日期的限量版本缺失或重叠')
    limit=candidates[0]
    if row['method'] not in limit['methods'].split('|'):raise DomainError('METHOD','检测方法不在标准适用范围')
    return {'standard_id':limit['id'],'limit':str(Decimal(limit['limit_mgkg'])),'methods':limit['methods'],'standard_start':limit['start'],'standard_end':limit['end']}
