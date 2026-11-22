from flask import Blueprint
from app.web import api,page
bp=Blueprint('m3_versions',__name__)
@bp.get('/m3_versions')
def screen():return page(3,'m3_versions.html')
@bp.route('/api/m3_versions',methods=['GET','POST'])
def preview():return api(3)
