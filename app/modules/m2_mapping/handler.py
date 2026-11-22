from flask import Blueprint
from app.web import api,page
bp=Blueprint('m2_mapping',__name__)
@bp.get('/m2_mapping')
def screen():return page(2,'m2_mapping.html')
@bp.route('/api/m2_mapping',methods=['GET','POST'])
def preview():return api(2)
