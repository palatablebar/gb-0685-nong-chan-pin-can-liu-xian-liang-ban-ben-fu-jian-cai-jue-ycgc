from app.errors import DomainError

def decode(raw):
    for encoding in ('utf-8-sig','gb18030'):
        try:return raw.decode(encoding),encoding
        except UnicodeDecodeError:continue
    raise DomainError('ENCODING','文件编码无法识别')
