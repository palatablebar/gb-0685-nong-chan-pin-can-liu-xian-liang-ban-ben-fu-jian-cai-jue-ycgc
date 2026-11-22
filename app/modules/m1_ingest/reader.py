import csv,io
from app.errors import DomainError
from app.config import REQUIRED
from app.modules.m1_ingest.decode import decode

def read(raw):
    text,encoding=decode(raw)
    if not text:raise DomainError('EMPTY_FILE','文件为空')
    if not text.strip():raise DomainError('BLANK_FILE','文件仅含空行')
    reader=csv.reader(io.StringIO(text,newline=''))
    try:header=[s.strip().lstrip('\ufeff') for s in next(reader)]
    except (StopIteration,csv.Error):raise DomainError('HEADER','无法读取表头')
    if len(set(header))!=len(header) or not set(REQUIRED)<=set(header):raise DomainError('HEADER','表头缺失或重复')
    out={'rows':[],'quarantine':[],'input_count':0,'blank_count':0,'header_count':0,'duplicate_count':0,'encoding':encoding}
    try:
        for row in reader:
            out['input_count']+=1;line=reader.line_num
            if not row or not any(s.strip() for s in row):out['blank_count']+=1;continue
            if row==header:out['header_count']+=1;continue
            if len(row)!=len(header):out['quarantine'].append({'line':line,'id':'','code':'WIDTH','raw':row});continue
            item=dict(zip(header,row));item['_line']=line;item['_raw']=dict(item);out['rows'].append(item)
    except csv.Error as exc:raise DomainError('CSV',str(exc))
    if out['input_count']==0:raise DomainError('HEADER_ONLY','文件仅含表头')
    return out
