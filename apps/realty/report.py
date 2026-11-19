import os

from django.conf import settings
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Table, Image
#Libs for map
import requests
from PIL import Image as PilImage
#Qrcode
from io import BytesIO
import qrcode

def get_template_page(canvas, doc):    
        canvas.saveState()        
		# styles = getSampleStyleSheet()
        base_path = settings.BASE_DIR + '/static/images/print/'
        #print(base_path)
		
        template = Image(base_path + 'print_template.png', A4[0], A4[1])
        
        canvas.setFillColorRGB(47/255, 59/255, 89/255)
        canvas.rect(0, A4[1] - 2*cm, A4[0], 2*cm, stroke=False,fill=True)
        template.drawOn(canvas, 0, 0)

        canvas.rect(0, 0, A4[0], 0.75*cm, stroke=False,fill=True)
		#footer_caption = Image(base_path + 'footer-caption.png', width=6.5*cm,height=1.5*cm)
		#footer_image = Image(base_path + 'footer-image.png', width=3*cm,height=1.5*cm)		

        # Release the canvas
        canvas.restoreState()

def set_template_page(canvas):            
        base_path = settings.BASE_DIR + '/static/images/print/'        
        template = Image(base_path + 'print_template.png', A4[0], A4[1])
        template.drawOn(canvas, 0, 0)

def _file_exists(path):
    return bool(path) and os.path.isfile(path)

def set_cover(canvas, obj):
    cover_path = obj.get_cover_path()
    if not _file_exists(cover_path):
        return
    img = Image(cover_path, 549.5, 350)
    img.drawOn(canvas, 23, 352)

def set_qrcode(canvas, obj, base_url):
    # El QR se genera en memoria con la URL actual del sitio (los QR guardados apuntaban al dominio anterior).
    url = '%s%s' % (base_url, obj.get_absolute_url())
    buffer = BytesIO()
    qrcode.make(url).save(buffer, 'PNG')
    buffer.seek(0)
    img = Image(buffer, 120, 110)
    img.drawOn(canvas, 449, 160)
    set_text(canvas, 'Ver más', 480, 280, 14)

    canvas.setFontSize(12)
    txt_obj = canvas.beginText()
    txt_obj.setTextOrigin(450, 150)
    for char in url:
        txt_obj.textOut(char)
        x = txt_obj.getX()
        if x > 563:
            txt_obj.moveCursor(0, 15)
    canvas.drawText(txt_obj)

def set_map(canvas, obj):
    if not obj.category.require_location or not obj.geopoint:
        return
    map_image = obj.get_last_image_by_code('map')
    if not map_image or not map_image.img or not _file_exists(map_image.img.path):
        key = settings.GOOGLE_MAPS_API_KEY
        if not key:
            return
        center = '%s,%s' % (obj.geopoint.y, obj.geopoint.x)
        params = {
            'center': center, 'zoom': 17, 'size': '274x203',
            'maptype': 'hybrid', 'markers': center, 'key': key,
        }
        try:
            result = requests.get(
                'https://maps.googleapis.com/maps/api/staticmap',
                params=params, timeout=settings.EXTERNAL_HTTP_TIMEOUT,
            )
            result.raise_for_status()
            image = PilImage.open(BytesIO(result.content))
        except (requests.RequestException, OSError):
            return
        map_image = obj.add_image(image, 'map')
    img = Image(map_image.img.path, 274, 203)
    img.drawOn(canvas, 23, 78)

def set_avatar(canvas, obj):
    avatar = obj.user.profile.get_avatar_path()
    if not _file_exists(avatar):
        return
    img = Image(avatar, 75, 75)
    img.drawOn(canvas, 334.5, 217.5)

def set_user(canvas, user):
    canvas.setFillColorRGB(0,0,0)
    name = user.get_full_name() or user.username
    width = 122
    name_width = stringWidth(name, 'Helvetica-Bold', 12)
    canvas.setFontSize(12)
    center = (width - name_width)/2
    set_bold_text(canvas, name, center + 310, 195, 12)
    base_path = settings.BASE_DIR + '/static/images/print/'
    cell = Image(base_path + 'cell.png', 10, 10)
    cell.drawOn(canvas, 315, 175)
    set_text(canvas, user.profile.phone, 330, 175, 10)

def set_socialnetworks(canvas, obj):
    base_path = settings.BASE_DIR + '/static/images/print/'
    y = 160
    count=5
    mail = Image(base_path + 'envelope.png', 10, 10)
    mail.drawOn(canvas, 315, 160)

    canvas.setFontSize(10)
    txt_obj = canvas.beginText()
    txt_obj.setTextOrigin(330, y)
    y -= 15
    for char in obj.user.email:
        txt_obj.textOut(char)
        x = txt_obj.getX()
        if x > 425:
            txt_obj.moveCursor(0, 15)
            y -= 15
            count -= 1
    canvas.drawText(txt_obj)
    
    networks = obj.user.profile.socialnetworkprofile_set.all()[:count]
    for network in networks:
        icon = network.social_network.get_last_image_by_code('print')
        if icon and icon.img:
            img = Image(icon.img.path, 10, 10)
            img.drawOn(canvas, 315, y)
        set_text(canvas, network.username, 330, y, 10)
        y -= 15

def set_text(canvas, text, x, y, size):
    text = text or ''
    canvas.setFontSize(size)
    canvas.drawString(x, y, text)

def set_bold_text(canvas, text, x, y, size):
    canvas.setFont('Helvetica-Bold', size)
    canvas.drawString(x, y, text)

def set_points_grid(canvas):
    canvas.setFontSize(5)
    for x in range(0, int(A4[0]), 10):
        for y in range(0, int(A4[1]), 5):
            text = str(y) if x == 0 else str(x) if y == 0 else '.' 
            canvas.drawString(x, y, text)

def get_pdf(obj, base_url=''):
    #Document settings
    buff = BytesIO()
    canvas = Canvas(buff,pagesize=A4)
    set_template_page(canvas)
    canvas.setFillColorRGB(1,1,1)

    set_bold_text(canvas, str(obj.category.singular_name), 310, 790, 16)
    set_bold_text(canvas, str(obj.get_purpose().activity), 450, 790, 16)
    set_bold_text(canvas, 'Precio', 310, 750, 16)
    set_bold_text(canvas, '$ ' + str(obj.get_price_area()), 450, 750, 16)
    set_cover(canvas, obj)
    set_map(canvas, obj)
    set_avatar(canvas, obj)
    set_user(canvas, obj.user)
    set_socialnetworks(canvas, obj)
    set_qrcode(canvas, obj, base_url or settings.SITE_URL)
    #set_points_grid(canvas)
    canvas.save()
        
    return buff.getvalue()