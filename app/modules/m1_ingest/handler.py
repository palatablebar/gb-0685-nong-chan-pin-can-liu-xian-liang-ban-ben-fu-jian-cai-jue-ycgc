from flask import Blueprint
from app.web import api,page
bp=Blueprint('m1_ingest',__name__)
@bp.get('/m1_ingest')
def screen():return page(1,'m1_ingest.html')
@bp.route('/api/m1_ingest',methods=['GET','POST'])
def preview():return api(1)
