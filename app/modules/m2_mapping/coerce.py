import unicodedata
from decimal import Decimal,InvalidOperation
from datetime import datetime,date,timezone
from app.errors import DomainError
SENTINELS={'','-','N/A','NULL','未知'}

def number(value):
    text=unicodedata.normalize('NFKC',str(value)).strip().replace(',','')
    if text.upper() in SENTINELS:raise DomainError('MISSING','数值缺失')
    try:
        result=Decimal(text)
        if not result.is_finite():raise InvalidOperation
        return result
    except InvalidOperation:raise DomainError('NUMBER','数值无效')

def day(value):
    try:return date.fromisoformat(value.strip()).isoformat()
    except (ValueError,AttributeError):raise DomainError('DATE','日期无效')

def instant(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        if d.tzinfo is None:raise ValueError()
        return d.astimezone(timezone.utc).isoformat()
    except (ValueError,AttributeError):raise DomainError('DATE','时间必须包含时区')
