from collections import defaultdict
RANK={'PASS':0,'UNCERTAIN':1,'FAIL':2}

def balance(state):
    accepted=len(state['rows']);isolated=len(state['quarantine']);accounted=accepted+isolated+state['blank_count']+state['header_count']+state['duplicate_count']
    batches=defaultdict(list)
    for r in state['calculations']:batches[r['batch']].append(r)
    grades=[{'batch':b,'code':max((r['code'] for r in rows),key=lambda c:RANK[c]),'projects':len(rows),
             'samples':len({r['sample_id'] for r in rows}),
             'uncertain':sum(r['code']=='UNCERTAIN' for r in rows),
             'fail':sum(r['code']=='FAIL' for r in rows),
             'conflict':sum(r.get('basis')=='BASIS_CONFLICT' for r in rows)} for b,rows in sorted(batches.items())]
    # The seal scope follows directly from the same concentration basis that
    # produced the sample verdict.  The batch is the unit of release, so a batch
    # whose highest risk level is not PASS is sealed as a whole; the risky
    # projects that drove the grade are recorded so the seal can be re-checked.
    scope=[]
    for g in grades:
        rows=batches[g['batch']]
        all_samples=sorted({r['sample_id'] for r in rows})
        risky=sorted({r['sample_id'] for r in rows if r['code']!='PASS'})
        uncertain=sorted({r['sample_id'] for r in rows if r['code']=='UNCERTAIN'})
        scope.append({'batch':g['batch'],'code':g['code'],'sealed':g['code']!='PASS',
                      'samples':all_samples,'driver_samples':risky,'uncertain_samples':uncertain})
    return {'input':state['input_count'],'accepted':accepted,'isolated':isolated,'blank':state['blank_count'],'headers':state['header_count'],'duplicates':state['duplicate_count'],'accounted':accounted,'balanced':accounted==state['input_count'],'business':state['business'],'grades':grades,'seal_scope':sorted(scope,key=lambda s:s['batch'])}
