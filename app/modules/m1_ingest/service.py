from app.modules.m1_ingest.reader import read

def execute(content, parameters=None):
    state=read(content);state['parameters']=parameters or {};return state
