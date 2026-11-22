from app.modules.m6_reconcile.compare import balance

def execute(state):
    state['reconcile']=balance(state);return state
