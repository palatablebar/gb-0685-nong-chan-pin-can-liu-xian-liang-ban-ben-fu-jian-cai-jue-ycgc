from collections import defaultdict
from decimal import Decimal
from app.errors import DomainError

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
    calculations=[{'id':r['id'],'line':r['_line'],'sample_id':r['sample_id'],'batch':r['batch'],'analyte':r['analyte'],'method':r['method'],'standard':r['standard_id'],'lower':r['lower'],'upper':r['upper'],'upper_exclusive':r['upper_exclusive'],'limit':r['limit'],'code':r['code'],'replaces':r['relation']} for r in chosen if r['id'] not in bad]
    state['calculations']=calculations;state['business']={'total':len(calculations),'pass':sum(r['code']=='PASS' for r in calculations),'fail':sum(r['code']=='FAIL' for r in calculations),'uncertain':sum(r['code']=='UNCERTAIN' for r in calculations),'unit':'检测项目'};return state
