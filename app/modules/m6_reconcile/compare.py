from collections import defaultdict
RANK={'PASS':0,'UNCERTAIN':1,'FAIL':2}

def balance(state):
    accepted=len(state['rows']);isolated=len(state['quarantine']);accounted=accepted+isolated+state['blank_count']+state['header_count']+state['duplicate_count']
    batches=defaultdict(list)
    for r in state['calculations']:batches[r['batch']].append(r)
    grades=[{'batch':b,'code':max((r['code'] for r in rows),key=lambda c:RANK[c]),'projects':len(rows),'samples':len({r['sample_id'] for r in rows})} for b,rows in sorted(batches.items())]
    return {'input':state['input_count'],'accepted':accepted,'isolated':isolated,'blank':state['blank_count'],'headers':state['header_count'],'duplicates':state['duplicate_count'],'accounted':accounted,'balanced':accounted==state['input_count'],'business':state['business'],'grades':grades}
