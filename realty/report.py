from django.conf import settings
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Table, Image
from io import BytesIO

def get_template_page(canvas, doc):    
        canvas.saveState()        
		# styles = getSampleStyleSheet()
        base_path = settings.BASE_DIR + '/static/images/'
        #print(base_path)
		
        logo = Image(base_path + 'logo.png', width=5*cm, height=1.28*cm)
        
        canvas.setFillColorRGB(47/255, 59/255, 89/255)
        canvas.rect(0, A4[1] - 2*cm, A4[0], 2*cm, stroke=False,fill=True)
        logo.drawOn(canvas, 25, A4[1] - logo._height - 10)

        canvas.rect(0, 0, A4[0], 0.75*cm, stroke=False,fill=True)
		#footer_caption = Image(base_path + 'footer-caption.png', width=6.5*cm,height=1.5*cm)
		#footer_image = Image(base_path + 'footer-image.png', width=3*cm,height=1.5*cm)		

        # Release the canvas
        canvas.restoreState()


def get_pdf():
    pass
    #Document settings
    buff = BytesIO()
    doc = SimpleDocTemplate(buff,pagesize=A4)

    #Styles settings
    styles = getSampleStyleSheet()
    report = [
        Paragraph('HOLA', styles['Title']),
    ]

    doc.build(report, onFirstPage=get_template_page,onLaterPages=get_template_page)
    return buff.getvalue()