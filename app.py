from flask import Flask, request, render_template_string, send_file
import math, io, os
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

app = Flask(__name__)

# =========================
# CONSTANTS
# =========================
PIECE_HEIGHT = 0.2
CORNER_RETURN = 0.1
INSTALL_BODY_RATE = 120
INSTALL_CORNER_RATE = 120
GST_RATE = 0.10

# =========================
# PRODUCTS
# =========================
PRODUCTS = {
    "RB": {"name": "Royal Blue", "body_code": "CLD005", "corner_code": "CLD006", "body_price": 75, "corner_price": 25},
    "IWQ": {"name": "Ivory White Quartz", "body_code": "CLD007", "corner_code": "CLD008", "body_price": 75, "corner_price": 25},
    "AWQ": {"name": "Artic White Quartz", "body_code": "CLD009", "corner_code": "CLD010", "body_price": 75, "corner_price": 25},
    "CC": {"name": "Country Cross", "body_code": "CLD011", "corner_code": "CLD012", "body_price": 75, "corner_price": 25}
}

def money(v): return "{:.2f}".format(float(v))

# =========================
# HTML (DETAILED OUTPUT)
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>PPM Cladding Calculator</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/static/favicon.ico">

<style>
body {font-family: Arial; background:#f4f6f8;}
.container {max-width:900px;margin:auto;background:white;padding:20px;border-radius:10px;}
input, select {width:100%;padding:12px;margin-top:8px;}
button {width:100%;padding:14px;margin-top:20px;background:black;color:white;}
.result {background:#f9fafb;padding:15px;margin-top:20px;border-radius:8px;}
</style>

<script>
function toggleFields(){
 let t=document.getElementById("type").value;
 document.getElementById("wall").style.display=(t=="wall")?"block":"none";
}
</script>

</head>

<body>
<div class="container">

<h2>PPM Cladding Calculator</h2>

<form method="post">

<select name="type" id="type" onchange="toggleFields()" required>
<option value="">Select Type</option>
<option value="wall">Wall</option>
</select>

<div id="wall" style="display:none;">
<input name="length" placeholder="Length (m)">
<input name="height" placeholder="Height (m)">
<input name="corner_lm" placeholder="Corner LM">
</div>

<select name="product">
{% for k,p in products.items() %}
<option value="{{k}}">
{{p.name}} ({{p.body_code}} / {{p.corner_code}})
</option>
{% endfor %}
</select>

<label>
<input type="checkbox" name="install"> Include Installation
</label>

<button>Generate Quote</button>

</form>

{% if result %}
<div class="result">

<h3>Detailed Calculation</h3>

<p>Total Area: {{result.total_area}} m²</p>
<p>Corner Deduction: {{result.corner_area}} m²</p>
<p>Net Area: {{result.net_area}} m²</p>
<p>With Wastage: {{result.area_waste}} m²</p>

<h3>Breakdown</h3>

<p>Body: {{result.area_waste}} × {{result.body_rate}} = ${{result.body_total}}</p>
<p>Corner: {{result.corner_pcs}} pcs × {{result.corner_rate}} = ${{result.corner_total}}</p>

{% if result.install %}
<p>Installation Body = ${{result.install_body}}</p>
<p>Installation Corner = ${{result.install_corner}}</p>
{% endif %}

<h3>Totals</h3>
<p>Subtotal: ${{result.subtotal}}</p>
<p>GST: ${{result.gst}}</p>
<h2>Total: ${{result.total}}</h2>

<form method="post" action="/pdf">
{% for k,v in result.items() %}
<input type="hidden" name="{{k}}" value="{{v}}">
{% endfor %}
<button>Download PDF</button>
</form>

</div>
{% endif %}

</div>
</body>
</html>
"""

# =========================
# MAIN
# =========================
@app.route("/", methods=["GET","POST"])
def home():

    if request.method=="POST":

        p=PRODUCTS[request.form.get("product")]

        length=float(request.form.get("length") or 0)
        height=float(request.form.get("height") or 0)
        corner_lm=float(request.form.get("corner_lm") or 0)

        total_area=length*height
        corner_area=corner_lm*(2*CORNER_RETURN)
        net_area=max(total_area-corner_area,0)
        area_waste=net_area*1.1

        corner_pcs=math.ceil(corner_lm/PIECE_HEIGHT)

        body_total=area_waste*p["body_price"]
        corner_total=corner_pcs*p["corner_price"]

        install_body=install_corner=0
        if request.form.get("install"):
            install_body=area_waste*INSTALL_BODY_RATE
            install_corner=corner_lm*INSTALL_CORNER_RATE

        subtotal=body_total+corner_total+install_body+install_corner
        gst=subtotal*GST_RATE
        total=subtotal+gst

        result={
            "product":p["name"],
            "body_code":p["body_code"],
            "corner_code":p["corner_code"],
            "total_area":round(total_area,2),
            "corner_area":round(corner_area,2),
            "net_area":round(net_area,2),
            "area_waste":round(area_waste,2),
            "corner_pcs":corner_pcs,
            "corner_lm":corner_lm,
            "body_rate":p["body_price"],
            "corner_rate":p["corner_price"],
            "body_total":round(body_total,2),
            "corner_total":round(corner_total,2),
            "install":request.form.get("install"),
            "install_body":round(install_body,2),
            "install_corner":round(install_corner,2),
            "subtotal":round(subtotal,2),
            "gst":round(gst,2),
            "total":round(total,2)
        }

        return render_template_string(HTML,result=result,products=PRODUCTS)

    return render_template_string(HTML,result=None,products=PRODUCTS)

# =========================
# PDF (FULL PREMIUM)
# =========================
@app.route("/pdf", methods=["POST"])
def pdf():

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    center = ParagraphStyle(name='center', alignment=TA_CENTER)
    right = ParagraphStyle(name='right', alignment=TA_RIGHT)

    story = []

    # =========================
    # LOGO
    # =========================
    try:
        story.append(Image("static/ppm-stone-logo.png", width=150, height=60))
    except:
        pass

    # =========================
    # COMPANY HEADER
    # =========================
    story.append(Paragraph("<b>PPM Stone</b>", styles['Title']))
    story.append(Paragraph("PPM Enterprises Pty Ltd", styles['Normal']))
    story.append(Paragraph("Factory 2, 64-70 Edison Road Dandenong South VIC 3175", styles['Normal']))
    story.append(Paragraph("Tel: 1300 278 355", styles['Normal']))
    story.append(Paragraph("Email: admin@ppmstone.com.au", styles['Normal']))
    story.append(Paragraph("ABN: 79 116 045 553", styles['Normal']))

    story.append(Spacer(1,10))
    story.append(Paragraph("<b>QUOTE</b>", center))
    story.append(Spacer(1,10))

    # =========================
    # QUOTE INFO
    # =========================
    now = datetime.now()
    story.append(Paragraph(now.strftime("Quote No: QU-%y%m%d01"), styles['Normal']))
    story.append(Paragraph(now.strftime("Date: %d/%m/%Y"), styles['Normal']))

    story.append(Spacer(1,10))

    # =========================
    # CUSTOMER DETAILS
    # =========================
    story.append(Paragraph("<b>Customer Details</b>", styles['Heading3']))
    story.append(Paragraph(f"Customer Name: {request.form.get('customer')}", styles['Normal']))
    story.append(Paragraph(f"Project Reference: {request.form.get('project')}", styles['Normal']))
    story.append(Paragraph(f"Site Address: {request.form.get('address')}", styles['Normal']))

    story.append(Spacer(1,15))

    # =========================
    # PRODUCT TABLE
    # =========================
    table_data = [
        ["Code", "Description", "Qty", "Unit", "Unit Price", "Amount"],

        [
            request.form.get("body_code"),
            f"PPM Cladding | Body | {request.form.get('product')} | 20–40mm",
            request.form.get("area_waste"),
            "m²",
            "$"+money(request.form.get("body_rate")),
            "$"+money(request.form.get("body_total"))
        ],

        [
            request.form.get("corner_code"),
            f"PPM Cladding | Corner | {request.form.get('product')} | 20–40mm",
            request.form.get("corner_pcs"),
            "pcs",
            "$"+money(request.form.get("corner_rate")),
            "$"+money(request.form.get("corner_total"))
        ]
    ]

    # INSTALLATION
    if request.form.get("install") == "on":
        table_data.append([
            request.form.get("body_code")+"-I",
            "Installation - Body",
            request.form.get("area_waste"),
            "m²",
            "$120",
            "$"+money(request.form.get("install_body"))
        ])

        table_data.append([
            request.form.get("corner_code")+"-I",
            "Installation - Corner",
            request.form.get("corner_lm"),
            "LM",
            "$120",
            "$"+money(request.form.get("install_corner"))
        ])

    table = Table(table_data, colWidths=[70,200,60,50,80,80])

    table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.8,colors.black),
        ('BACKGROUND',(0,0),(-1,0),colors.black),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(2,1),(-1,-1),'RIGHT')
    ]))

    story.append(table)

    # =========================
    # TOTALS TABLE
    # =========================
    totals = [
        ["Subtotal (Ex GST)", "$"+money(request.form.get("subtotal"))],
        ["GST (10%)", "$"+money(request.form.get("gst"))],
        ["TOTAL (INC GST)", "$"+money(request.form.get("total"))]
    ]

    totals_table = Table(totals, colWidths=[300,120])

    totals_table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.8,colors.black),
        ('ALIGN',(1,0),(1,-1),'RIGHT'),
        ('FONTNAME',(0,2),(-1,2),'Helvetica-Bold'),
        ('BACKGROUND',(0,2),(-1,2),colors.lightgrey)
    ]))

    story.append(Spacer(1,15))
    story.append(totals_table)

    # =========================
    # NOTES & DISCLAIMER
    # =========================
    story.append(Spacer(1,20))

    story.append(Paragraph(
        "<b>Notes:</b> This is an estimate of cost, the final figures may vary after the final site inspection.",
        styles['Normal']
    ))

    story.append(Spacer(1,8))

    story.append(Paragraph(
        "<b>Disclaimer:</b> Please note that our bluestones and stone claddings are natural, so variations in colour, texture, and veining may occur. These differences from samples or images are natural and enhance the stone's unique character.",
        styles['Normal']
    ))

    # =========================
    # BUILD PDF
    # =========================
    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="QUOTE.pdf")

# =========================
# RUN
# =========================
if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
