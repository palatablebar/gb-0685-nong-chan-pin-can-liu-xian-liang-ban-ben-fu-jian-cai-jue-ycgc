from collections import defaultdict
from decimal import Decimal
from app.errors import DomainError
from app.modules.m5_calculate import basis

def select_reports(reports):
    versions={}
    for r in reports:
        if r['id'] not in versions or Decimal(str(r['version']))>Decimal(str(versions[r['id']]['version'])):versions[r['id']]=r
    reports=list(versions.values());lookup={r['id']:r for r in reports};bad={};valid=[]
    # A relation is a replacement chain; detect cycles before following any edge.
    for r in reports:
        chain=[];current=r
        while current.get('relation'):
            if current['id'] in chain:
                for rid in chain:bad[rid]='REFERENCE'
                break
            chain.append(current['id']);parent=lookup.get(current['relation'])
            if parent is None:bad[r['id']]='REFERENCE';break
            shared=('sample_id','batch','product','analyte','method','sampled')
            if any(current[k]!=parent[k] for k in shared) or current['reported']<=parent['reported']:
                bad[r['id']]='REFERENCE';break
            current=parent
        if current['id'] in bad:bad[r['id']]='REFERENCE'
    grouped=defaultdict(list)
    for r in reports:
        if r['id'] not in bad:grouped[(r['sample_id'],r['batch'],r['product'],r['analyte'])].append(r)
    for key,rows in grouped.items():
        roots=[r for r in rows if not r['relation']]
        if len(roots)!=1:
            for r in rows:bad[r['id']]='CONFLICT'
            continue
        # Only reports connected to the single primary sample result may supersede it.
        candidates=[r for r in rows if r['id'] not in bad]
        rank=max((r['reported'],Decimal(str(r['version']))) for r in candidates)
        newest=[r for r in candidates if (r['reported'],Decimal(str(r['version'])))==rank]
        if len({(r['lower'],r['upper']) for r in newest})>1:
            for r in rows:bad[r['id']]='CONFLICT'
            continue
        chosen=sorted(newest,key=lambda x:x['id'])[0];valid.append(chosen)
    return valid,bad

def apply(state):
    chosen,bad=select_reports(state['measurements']);lines=set()
    for r in state['measurements']:
        if r['id'] in bad:
            lines.add(r['_line']);state['quarantine'].append({'line':r['_line'],'id':r['id'],'code':bad[r['id']],'raw':r['_raw']})
    state['rows']=[r for r in state['rows'] if r['_line'] not in lines]
    basis_rows,resolved,plain,on_date=basis.adjudicate(state['measurements'],chosen,bad,state.get('parameters',{}))
    calculations=[]
    for key,r in sorted(plain.items(),key=lambda kv:(kv[1]['batch'],kv[1]['sample_id'],kv[1]['analyte'])):
        if key in resolved:
            b=resolved[key]
            calculations.append({'id':b['adopted_id'],'line':r['_line'],'sample_id':r['sample_id'],'batch':r['batch'],'analyte':r['analyte'],
                'method':r['method'],'standard':r['standard_id'],'lower':b['lower'] if b['lower'] is not None else '—',
                'upper':b['upper'] if b['upper'] is not None else '—','upper_exclusive':False,
                'limit':r['limit'],'code':b['decision'],'replaces':r['relation'],'basis':b['reason'],
                'curve':b['current_curve']['curve_id'] if b['current_curve'] else None})
        else:
            calculations.append({'id':r['id'],'line':r['_line'],'sample_id':r['sample_id'],'batch':r['batch'],'analyte':r['analyte'],'method':r['method'],
                'standard':r['standard_id'],'lower':r['lower'],'upper':r['upper'],'upper_exclusive':r['upper_exclusive'],'limit':r['limit'],
                'code':r['code'],'replaces':r['relation'],'basis':'REPORTED','curve':None})
    calculations.sort(key=lambda c:(c['batch'],c['sample_id'],c['analyte']))
    state['basis']=basis_rows;state['adjudication_date']=on_date
    state['calculations']=calculations
    state['business']={'total':len(calculations),'pass':sum(r['code']=='PASS' for r in calculations),'fail':sum(r['code']=='FAIL' for r in calculations),
        'uncertain':sum(r['code']=='UNCERTAIN' for r in calculations),'unit':'检测项目'}
    state['basis_summary']={'groups':len(basis_rows),
        'conflict':sum(b['reason']=='BASIS_CONFLICT' for b in basis_rows),
        'single':sum(b['reason']=='SINGLE_VALID' for b in basis_rows),
        'agree':sum(b['reason']=='AGREE' for b in basis_rows),
        'mixed':sum(b['reason']=='MIXED_BASIS' for b in basis_rows),
        'no_basis':sum(b['reason']=='NO_VALID_BASIS' for b in basis_rows),
        'adjudication_date':on_date}
    return state
