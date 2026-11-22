from flask import Blueprint
from app.web import api,page
bp=Blueprint('m4_segments',__name__)
@bp.get('/m4_segments')
def screen():return page(4,'m4_segments.html')
@bp.route('/api/m4_segments',methods=['GET','POST'])
def preview():return api(4)
