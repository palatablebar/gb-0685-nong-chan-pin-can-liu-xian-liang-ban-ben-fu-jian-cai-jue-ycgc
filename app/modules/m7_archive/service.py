from app.modules.m7_archive.export_out import checksum

def execute(state):
    state['archive']={'sha256':checksum(state),'evidence_count':len(state.get('calculations',[]))+len(state['quarantine'])+len(state.get('basis',[])),
        'basis_groups':len(state.get('basis',[])),'sealed_batches':sum(1 for s in state.get('reconcile',{}).get('seal_scope',[]) if s['sealed']),
        'ready':state.get('reconcile',{}).get('balanced',False)}
    return state
