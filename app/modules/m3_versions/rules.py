from app.modules.m3_versions.standards import standards,choose
from app.errors import DomainError
from decimal import Decimal

def apply(state):
    limits=standards();reports=[];bad=[]
    for r in state['rows']:
        try:
            if r['reported']<r['sampled'] or Decimal(str(r['lod']))<=0:raise DomainError('RANGE','报告日期或检出限无效')
            report=dict(r);report.update(choose(r,limits));reports.append(report)
        except DomainError as e:bad.append((r,e.code))
    lines={r['_line'] for r,_ in bad};state['rows']=[r for r in state['rows'] if r['_line'] not in lines]
    for r,c in bad:state['quarantine'].append({'line':r['_line'],'id':r['id'],'code':c,'raw':r['_raw']})
    state['reports']=reports;return state
