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
# PRODUCTS (WITH SIZE)
# =========================
PRODUCTS = {
    "RB": {"name": "Royal Blue", "size": "20–40mm", "body_code": "CLD005", "corner_code": "CLD006", "body_price": 75, "corner_price": 25},
    "IWQ": {"name": "Ivory White Quartz", "size": "15–30mm", "body_code": "CLD007", "corner_code": "CLD008", "body_price": 75, "corner_price": 25},
    "AWQ": {"name": "Artic White Quartz", "size": "25–50mm", "body_code": "CLD009", "corner_code": "CLD010", "body_price": 75, "corner_price": 25},
    "CC": {"name": "Country Cross", "size": "30–60mm", "body_code": "CLD011", "corner_code": "CLD012", "body_price": 75, "corner_price": 25}
}

def money(v):
    return "{:.2f}".format(float(v))

# =========================
# HTML
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
input, select, textarea {width:100%;padding:12px;margin-top:8px;}
button {width:100%;padding:14px;margin-top:20px;background:black;color:white;}
.result {background:#f9fafb;padding:15px;margin-top:20px;border-radius:8px;}
.row {display:flex; gap:10px;}
@media(max-width:768px){ .row{flex-direction:column;} }
</style>

<script>
function toggleFields(){
 let t=document.getElementById("type").value;
 document.getElementById("wall").style.display=(t=="wall"||t=="floor")?"block":"none";
 document.getElementById("pillar").style.display=(t=="pillar")?"block":"none";
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
<option value="floor">Floor</option>
<option value="pillar">Pillar</option>
</select>

<div id="wall" style="display:none;">
<div class="row">
<input name="length" placeholder="Length (m)">
<input name="height" placeholder="Height / Width (m)">
</div>
<input name="corner_lm" placeholder="Corner Length (LM)">
</div>

<div id="pillar" style="display:none;">
<div class="row">
<input name="pillar_height" placeholder="Pillar Height">
<input name="front" placeholder="Front Width">
</div>
<input name="depth" placeholder="Depth">
<select name="sides">
<option value="3">3 sides</option>
<option value="4">4 sides</option>
</select>
</div>

<select name="product">
{% for k,p in products.items() %}
<option value="{{k}}">{{p.name}} ({{p.body_code}} / {{p.corner_code}})</option>
{% endfor %}
</select>

<label><input type="checkbox" name="install"> Include Installation</label>

<h3>Customer Details</h3>
<input name="customer">
<input name="project">
<textarea name="address"></textarea>

<button>Generate Quote</button>
</form>

{% if result %}
<div class="result">

<h3>Calculation</h3>
<p>Total Area: {{result.total_area}} m²</p>
<p>Corner Deduction: {{result.corner_area}} m²</p>
<p>Net Area: {{result.net_area}} m²</p>
<p>With Wastage: {{result.area_waste}} m²</p>

<h3>Breakdown</h3>
<p>Body = {{result.area_waste}} × {{result.body_rate}} = ${{result.body_total}}</p>
<p>Corner = {{result.corner_pcs}} × {{result.corner_rate}} = ${{result.corner_total}}</p>

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

        typ = request.form.get("type")
        p = PRODUCTS.get(request.form.get("product"))

        length=float(request.form.get("length") or 0)
        height=float(request.form.get("height") or 0)
        corner_lm=float(request.form.get("corner_lm") or 0)

        ph=float(request.form.get("pillar_height") or 0)
        front=float(request.form.get("front") or 0)
        depth=float(request.form.get("depth") or 0)
        sides=int(request.form.get("sides") or 3)

        if typ in ["wall","floor"]:
            total_area = length * height
        else:
            if sides == 4:
                total_area = ph*(2*front + 2*depth)
                corner_lm = ph*4
            else:
                total_area = ph*(front + 2*depth)
                corner_lm = ph*2

        corner_area = corner_lm*(2*CORNER_RETURN)
        net_area = max(total_area-corner_area,0)
        area_waste = net_area*1.1

        corner_pcs = math.ceil(corner_lm/PIECE_HEIGHT)

        body_total = area_waste*p["body_price"]
        corner_total = corner_pcs*p["corner_price"]

        install_body = install_corner = 0
        if request.form.get("install"):
            install_body = area_waste*INSTALL_BODY_RATE
            install_corner = corner_lm*INSTALL_CORNER_RATE

        subtotal = body_total+corner_total+install_body+install_corner
        gst = subtotal*GST_RATE
        total = subtotal+gst

        result={
            "product_name":p["name"],
            "size":p["size"],
            "body_code":p["body_code"],
            "corner_code":p["corner_code"],
            "area_waste":area_waste,
            "corner_pcs":corner_pcs,
            "corner_lm":corner_lm,
            "body_rate":p["body_price"],
            "corner_rate":p["corner_price"],
            "body_total":body_total,
            "corner_total":corner_total,
            "install":request.form.get("install"),
            "install_body":install_body,
            "install_corner":install_corner,
            "subtotal":subtotal,
            "gst":gst,
            "total":total,
            "customer":request.form.get("customer"),
            "project":request.form.get("project"),
            "address":request.form.get("address"),
            "total_area":total_area,
            "corner_area":corner_area,
            "net_area":net_area
        }

        return render_template_string(HTML,result=result,products=PRODUCTS)

    return render_template_string(HTML,result=None,products=PRODUCTS)

# =========================
# PDF
# =========================
@app.route("/pdf", methods=["POST"])
def pdf():

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    center = ParagraphStyle(name='c', alignment=TA_CENTER)

    story = []

    try:
        story.append(Image("static/ppm-stone-logo.png", width=140, height=60))
    except:
        pass

    story.append(Paragraph("<b>PPM Stone</b>", styles['Title']))
    story.append(Paragraph("PPM Enterprises Pty Ltd", styles['Normal']))
    story.append(Paragraph("Factory 2, 64-70 Edison Road Dandenong South VIC 3175", styles['Normal']))
    story.append(Paragraph("Tel: 1300 278 355", styles['Normal']))
    story.append(Paragraph("Email: admin@ppmstone.com.au", styles['Normal']))
    story.append(Paragraph("ABN: 79 116 045 553", styles['Normal']))

    story.append(Spacer(1,10))
    story.append(Paragraph("<b>QUOTE</b>", center))

    now = datetime.now()
    story.append(Paragraph(now.strftime("Quote No: QU-%y%m%d01"), styles['Normal']))
    story.append(Paragraph(now.strftime("Date: %d/%m/%Y"), styles['Normal']))

    story.append(Spacer(1,10))

    story.append(Paragraph("<b>Customer Details</b>", styles['Heading3']))
    story.append(Paragraph(f"Customer Name: {request.form.get('customer')}", styles['Normal']))
    story.append(Paragraph(f"Project Reference: {request.form.get('project')}", styles['Normal']))
    story.append(Paragraph(f"Site Address: {request.form.get('address')}", styles['Normal']))

    story.append(Spacer(1,15))

    data = [
        ["Code","Description","Qty","Unit","Rate","Amount"],
        [request.form.get("body_code"),
         f"PPM Cladding | Body | {request.form.get('product_name')} | {request.form.get('size')}",
         request.form.get("area_waste"),"m²",
         "$"+money(request.form.get("body_rate")),
         "$"+money(request.form.get("body_total"))],

        [request.form.get("corner_code"),
         f"PPM Cladding | Corner | {request.form.get('product_name')} | {request.form.get('size')}",
         request.form.get("corner_pcs"),"pcs",
         "$"+money(request.form.get("corner_rate")),
         "$"+money(request.form.get("corner_total"))]
    ]

    if request.form.get("install") == "on":
        data.append([request.form.get("body_code")+"-I","Installation Body",
                     request.form.get("area_waste"),"m²","$120",
                     "$"+money(request.form.get("install_body"))])

        data.append([request.form.get("corner_code")+"-I","Installation Corner",
                     request.form.get("corner_lm"),"LM","$120",
                     "$"+money(request.form.get("install_corner"))])

    table = Table(data)
    table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.8,colors.black),
        ('BACKGROUND',(0,0),(-1,0),colors.black),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(2,1),(-1,-1),'RIGHT')
    ]))

    story.append(table)

    totals = [
        ["Subtotal (Ex GST)", "$"+money(request.form.get("subtotal"))],
        ["GST (10%)", "$"+money(request.form.get("gst"))],
        ["TOTAL (INC GST)", "$"+money(request.form.get("total"))]
    ]

    t2 = Table(totals, colWidths=[300,120])
    t2.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.8,colors.black),
        ('ALIGN',(1,0),(1,-1),'RIGHT'),
        ('FONTNAME',(0,2),(-1,2),'Helvetica-Bold'),
        ('BACKGROUND',(0,2),(-1,2),colors.lightgrey)
    ]))

    story.append(Spacer(1,15))
    story.append(t2)

    story.append(Spacer(1,20))
    story.append(Paragraph("Notes:", styles['Heading3']))
    story.append(Paragraph("This is an estimate of cost, the final figures may vary after the final site inspection.", styles['Normal']))

    story.append(Spacer(1,10))
    story.append(Paragraph("Disclaimer:", styles['Heading3']))
    story.append(Paragraph(
        "Please note that our bluestones and stone claddings are natural, so variations in colour, texture, and veining may occur. "
        "These differences from samples or images are natural and enhance the stone's unique character.",
        styles['Normal']
    ))

    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="QUOTE.pdf")

# =========================
# RUN
# =========================
if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
