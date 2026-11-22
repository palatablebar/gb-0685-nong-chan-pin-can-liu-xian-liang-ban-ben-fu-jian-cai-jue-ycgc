import io,csv,json,hashlib

def _dumps(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)

def referenced_curves(state):
    ids=set()
    for b in state.get('basis',[]):
        if b.get('current_curve'):ids.add(b['current_curve']['curve_id'])
        for q in b.get('quantifications',[]):
            if q.get('source_curve'):ids.add(q['source_curve'])
    for r in state.get('measurements',[]):
        if r.get('curve_id'):ids.add(r['curve_id'])
    from app.modules.m4_segments.curves import registry
    return [c for c in registry() if c['curve_id'] in ids]

def bundle(state):
    out=io.StringIO(newline='');writer=csv.writer(out)
    writer.writerow(['记录类型','批次','来源行','业务ID','原因码','内容'])
    rid=state.get('run_id','preview')
    writer.writerow(['运行清单',rid,'','','',_dumps(state.get('manifest',{}))])
    writer.writerow(['对账',rid,'','','',_dumps(state.get('reconcile',{}))])
    writer.writerow(['封存范围',rid,'','','',_dumps(state.get('reconcile',{}).get('seal_scope',[]))])
    writer.writerow(['定量依据',rid,'','','',_dumps({'adjudication_date':state.get('adjudication_date'),'summary':state.get('basis_summary',{})})])
    for c in referenced_curves(state):writer.writerow(['曲线',rid,'',c['curve_id'],c.get('status',''),_dumps(c)])
    for row in state.get('basis',[]):
        writer.writerow(['依据',rid,'','%s/%s/%s'%(row['batch'],row['sample_id'],row['analyte']),row['decision'],_dumps(row)])
    for row in state.get('calculations',[]):writer.writerow(['计算',rid,row.get('line',''),row.get('id',''),row.get('code',''),_dumps(row)])
    for row in state['quarantine']:writer.writerow(['隔离',rid,row['line'],row.get('id',''),row['code'],_dumps(row.get('raw',{}))])
    return '﻿'+out.getvalue()

def checksum(state):
    return hashlib.sha256(bundle(state).encode('utf-8')).hexdigest()

def conclusion(state):
    """Machine-checkable adjudication conclusion derived from one basis."""
    return {'run_id':state.get('run_id'),'rule_version':state.get('manifest',{}).get('rule_version'),
        'source_sha256':state.get('manifest',{}).get('sha256'),
        'curve_registry_sha256':state.get('manifest',{}).get('curve_registry_sha256'),
        'adjudication_date':state.get('adjudication_date'),
        'basis_summary':state.get('basis_summary',{}),
        'business':state.get('business',{}),
        'batches':state.get('reconcile',{}).get('grades',[]),
        'seal_scope':state.get('reconcile',{}).get('seal_scope',[]),
        'decisions':[{'batch':r['batch'],'sample_id':r['sample_id'],'analyte':r['analyte'],'report_id':r['id'],
                      'basis':r['basis'],'curve':r.get('curve'),'lower':r['lower'],'upper':r['upper'],
                      'limit':r['limit'],'code':r['code']} for r in state.get('calculations',[])],
        'basis':state.get('basis',[]),
        'quarantine':[{'line':q['line'],'id':q.get('id',''),'code':q['code']} for q in state.get('quarantine',[])],
        'evidence_sha256':state.get('archive',{}).get('sha256')}
