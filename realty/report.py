from django.conf import settings
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Table, Image
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

def set_qrcode(canvas, obj):
    qr_image = obj.get_last_image_by_code('qrcode')
    if not qr_image or not qr_image.img:
        qr = qrcode.make(obj.get_absolute_url())
        qr_image = obj.add_image(qr, 'qrcode')
    
    img = Image(qr_image.img.path, 122, 112)
    img.drawOn(canvas, 442, 208)

def set_text(canvas, text, x, y, size):
    canvas.setFontSize(size)
    canvas.drawString(x, y, text)

def set_bold_text(canvas, text, x, y, size):
    canvas.setFont('Helvetica-Bold', size)
    canvas.drawString(x, y, text)

def get_pdf(obj):    
    #Document settings
    buff = BytesIO()
    canvas = Canvas(buff,pagesize=A4)
    set_template_page(canvas)
    set_bold_text(canvas, str(obj.price), 360, 693, 16)
    set_bold_text(canvas, str(obj.get_purpose().activity), 455, 693, 16)
    set_qrcode(canvas, obj)
    canvas.save()
        
    return buff.getvalue()