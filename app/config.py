TITLE='农产品残留限量版本与复检裁决'
SHORT='residuelimit'
RULE_VERSION='2026.11.17-v1'
MODULES=[('m1_ingest', '报告采信'), ('m2_mapping', '项目映射'), ('m3_versions', '限量选版'), ('m4_segments', '检出量换算'), ('m5_calculate', '复检裁决'), ('m6_reconcile', '批次判级'), ('m7_archive', '报告归档')]
REQUIRED=['id', 'sample_id', 'batch', 'product', 'analyte', 'method', 'version', 'sampled', 'reported', 'result', 'unit', 'lod']
NUMERIC=['version', 'lod']
DATES=['sampled', 'reported']
TIMES=[]
