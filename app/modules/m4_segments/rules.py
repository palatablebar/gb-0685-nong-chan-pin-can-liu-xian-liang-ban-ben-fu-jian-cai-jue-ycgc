from decimal import Decimal,InvalidOperation
import unicodedata
from app.errors import DomainError

def concentration(result,unit,lod,limit):
    factors={'mg/kg':Decimal(1),'ppm':Decimal(1),'ug/kg':Decimal('.001'),'ppb':Decimal('.001')}
    if unit not in factors:raise DomainError('UNIT','检出量单位无效')
    factor=factors[unit];detection=Decimal(str(lod))*factor;threshold=Decimal(str(limit))
    text=unicodedata.normalize('NFKC',str(result)).strip().upper()
    try:
        if text=='ND':lower,upper,exclusive=Decimal(0),detection,True
        elif text.startswith('<'):
            value=Decimal(text[1:])*factor
            if not value.is_finite() or value<=0 or value!=detection:raise DomainError('RANGE','低于检出限报告与LOD不一致')
            lower,upper,exclusive=Decimal(0),value,True
        else:
            value=Decimal(text.replace(',',''))*factor
            if not value.is_finite() or value<0 or value<detection:raise DomainError('RANGE','定量值低于检出限')
            lower,upper,exclusive=value,value,False
    except InvalidOperation:raise DomainError('NUMBER','检出量无法解析')
    code='PASS' if upper<=threshold else 'FAIL' if lower>threshold else 'UNCERTAIN'
    return {'lower':str(lower),'upper':str(upper),'upper_exclusive':exclusive,'limit':str(threshold),'code':code,'unit':'mg/kg'}

def apply(state):
    measurements=[];bad=[]
    for r in state['reports']:
        try:
            m=dict(r);m.update(concentration(r['result'],r['unit'],r['lod'],r['limit']));measurements.append(m)
        except DomainError as e:bad.append((r,e.code))
    lines={r['_line'] for r,_ in bad};state['rows']=[r for r in state['rows'] if r['_line'] not in lines]
    for r,c in bad:state['quarantine'].append({'line':r['_line'],'id':r['id'],'code':c,'raw':r['_raw']})
    state['measurements']=measurements;return state
