from decimal import Decimal,InvalidOperation
import unicodedata
from app.errors import DomainError
from app.modules.m4_segments import curves

FACTORS={'mg/kg':Decimal(1),'ppm':Decimal(1),'ug/kg':Decimal('.001'),'ppb':Decimal('.001')}

def concentration(result,unit,lod,limit):
    if unit not in FACTORS:raise DomainError('UNIT','检出量单位无效')
    factor=FACTORS[unit];detection=Decimal(str(lod))*factor;threshold=Decimal(str(limit))
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

def by_curve(r,limit):
    """Check out the quantity recorded on the report's own curve and dilution."""
    if r.get('signal') in (None,''):raise DomainError('SIGNAL','校准曲线报告缺少原始信号')
    if r.get('dilution') in (None,''):raise DomainError('SIGNAL','校准曲线报告缺少稀释记录')
    if not r.get('curve_id'):raise DomainError('CURVE','校准曲线报告缺少曲线编号')
    curve=curves.get(r['curve_id'])
    if curve['curve_version']!=str(r.get('curve_version','')):raise DomainError('CURVE','曲线版本与曲线编号不符')
    curves.applicable(curve,r['analyte'],r['method'],r['reported'])
    q=curves.quantify(r['signal'],r['dilution'],curve)
    threshold=Decimal(str(limit));value=Decimal(q['original'])
    if r.get('result') not in (None,''):verify_reported(r['result'],r['unit'],value)
    return {'lower':q['original'],'upper':q['original'],'upper_exclusive':False,'limit':str(threshold),
            'code':'PASS' if value<=threshold else 'FAIL','unit':'mg/kg','quantified_by':'curve',
            'curve_id':q['curve_id'],'curve_version':q['curve_version'],'signal':q['signal'],
            'dilution':q['dilution'],'in_solution':q['in_solution'],'original':q['original'],
            'curve_lod':q['lod_mgkg'],'curve_range':[q['range_low'],q['range_high']]}

def verify_reported(text,unit,value):
    if unit not in FACTORS:raise DomainError('UNIT','检出量单位无效')
    raw=unicodedata.normalize('NFKC',str(text)).strip()
    if raw.upper()=='ND' or raw.startswith('<'):raise DomainError('CONSTRAINT','曲线报告的结果必须为定量值')
    try:reported=Decimal(raw.replace(',',''))*FACTORS[unit]
    except InvalidOperation:raise DomainError('NUMBER','检出量无法解析')
    if not reported.is_finite() or reported!=value:raise DomainError('CONSTRAINT','报告结果与原始信号按本曲线复算不一致')

def apply(state):
    measurements=[];bad=[]
    for r in state['reports']:
        try:
            m=dict(r)
            if r.get('curve_id') or r.get('signal') not in (None,''):m.update(by_curve(r,r['limit']))
            else:m.update(concentration(r['result'],r['unit'],r['lod'],r['limit']))
            measurements.append(m)
        except DomainError as e:bad.append((r,e.code))
    lines={r['_line'] for r,_ in bad};state['rows']=[r for r in state['rows'] if r['_line'] not in lines]
    for r,c in bad:state['quarantine'].append({'line':r['_line'],'id':r['id'],'code':c,'raw':r['_raw']})
    state['measurements']=measurements;return state
