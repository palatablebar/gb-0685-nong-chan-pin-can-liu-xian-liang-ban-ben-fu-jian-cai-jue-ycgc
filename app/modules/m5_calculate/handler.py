from flask import Blueprint
from app.web import api,page
bp=Blueprint('m5_calculate',__name__)
@bp.get('/m5_calculate')
def screen():return page(5,'m5_calculate.html')
@bp.route('/api/m5_calculate',methods=['GET','POST'])
def preview():return api(5)
