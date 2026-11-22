from flask import Blueprint
from app.web import api,page
bp=Blueprint('m7_archive',__name__)
@bp.get('/m7_archive')
def screen():return page(7,'m7_archive.html')
@bp.route('/api/m7_archive',methods=['GET','POST'])
def preview():return api(7)
