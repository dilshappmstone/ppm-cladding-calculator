# =========================
# IMPORTS
# =========================
from flask import Flask, request, render_template_string, send_file
import math
from datetime import datetime
import io
import os

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

def money(val):
    return "{:.2f}".format(float(val))

# =========================
# HTML
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>PPM Cladding Calculator</title>

<style>
body {
    font-family: Arial, sans-serif;
    background:#f4f6f8;
    margin:0;
}

.container {
    max-width:950px;
    margin:40px auto;
    background:#ffffff;
    padding:30px 40px;
    border-radius:10px;
    box-shadow:0 6px 25px rgba(0,0,0,0.08);
}

/* HEADER */
.header {
    display:flex;
    align-items:center;
    gap:15px;
    margin-bottom:25px;
}

.header img {
    height:55px;
}

.header h1 {
    margin:0;
}

.subtitle {
    color:#666;
    margin-bottom:25px;
}

.section {
    margin-bottom:25px;
}

label {
    font-weight:600;
    display:block;
    margin-top:12px;
}

small {
    color:#777;
    margin-bottom:8px;
    display:block;
}

input, select, textarea {
    width:100%;
    padding:12px;
    border:1px solid #ccc;
    border-radius:6px;
}

input:focus, select:focus, textarea:focus {
    border-color:#000;
    outline:none;
}

.row {
    display:flex;
    gap:15px;
}

.row > div {
    flex:1;
}

/* TOGGLE SWITCH */
.toggle-container {
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-top:15px;
}

.switch {
    position: relative;
    width:50px;
    height:26px;
}

.switch input {display:none;}

.slider {
    position:absolute;
    cursor:pointer;
    top:0;
    left:0;
    right:0;
    bottom:0;
    background:#ccc;
    border-radius:26px;
    transition:.3s;
}

.slider:before {
    position:absolute;
    content:"";
    height:20px;
    width:20px;
    left:3px;
    bottom:3px;
    background:white;
    border-radius:50%;
    transition:.3s;
}

input:checked + .slider {
    background:#000;
}

input:checked + .slider:before {
    transform:translateX(24px);
}

/* BUTTON */
button {
    margin-top:25px;
    width:100%;
    padding:14px;
    background:#000;
    color:#fff;
    border:none;
    border-radius:6px;
    font-size:16px;
    cursor:pointer;
}

button:hover {
    background:#333;
}

/* RESULT */
.result {
    margin-top:30px;
    padding:25px;
    background:#f9fafb;
    border-radius:6px;
    border:1px solid #ddd;
}

.divider {
    margin:15px 0;
    border-top:1px solid #ddd;
}

/* PRODUCT IMAGE */
.product-preview img {
    width:100%;
    max-height:250px;
    object-fit:cover;
    border-radius:6px;
    margin-top:10px;
}
</style>

<script>
function toggleFields(){
    let t=document.getElementById("type").value;
    document.getElementById("wall").style.display=(t=="wall"||t=="floor")?"block":"none";
    document.getElementById("pillar").style.display=(t=="pillar")?"block":"none";
}

const images = {
    "RB": "royal-blue.jpg",
    "IWQ": "ivory-white.jpg",
    "AWQ": "artic-white.jpg",
    "CC": "country-cross.jpg"
};

function updateImage(){
    let product = document.querySelector('[name="product"]').value;
    document.getElementById("productImage").src = images[product];
}

window.onload = function(){
    toggleFields();
    updateImage();
};
</script>

</head>

<body>

<div class="container">

<!-- HEADER -->
<div class="header">
    <img src="ppm-stone-logo.png">
    <div>
        <h1>PPM Stone</h1>
        <small>Cladding Calculator</small>
    </div>
</div>

<p class="subtitle">Estimate material quantities and generate a professional quote</p>

<form method="post" action="/">

<div class="section">
<label>Application Type</label>
<select name="type" id="type" onchange="toggleFields()">
<option value="wall">Wall</option>
<option value="floor">Floor</option>
<option value="pillar">Pillar</option>
</select>
</div>

<div id="wall" class="section">
<div class="row">
<div>
<label>Length (m)</label>
<input name="length" placeholder="e.g. 5.5">
<small>Total horizontal length</small>
</div>

<div>
<label>Height / Width (m)</label>
<input name="height" placeholder="e.g. 2.4">
<small>Wall height or floor width</small>
</div>
</div>

<label>Corner Length (LM)</label>
<input name="corner_lm" placeholder="e.g. 10">
<small>Total vertical edges in meters</small>
</div>

<div id="pillar" class="section">
<div class="row">
<div>
<label>Pillar Height (m)</label>
<input name="pillar_height" placeholder="e.g. 3">
</div>

<div>
<label>Front Width (m)</label>
<input name="front" placeholder="e.g. 1.2">
</div>
</div>

<label>Return Depth (m)</label>
<input name="depth" placeholder="e.g. 0.6">

<label>Sides Covered</label>
<select name="sides">
<option value="3">3 sides</option>
<option value="4">4 sides</option>
</select>
</div>

<div class="section">
<label>Product</label>
<select name="product" onchange="updateImage()">
{% for k,p in products.items() %}
<option value="{{k}}">{{p.name}}</option>
{% endfor %}
</select>

<div class="product-preview">
<img id="productImage">
</div>

<div class="toggle-container">
<span>Include Installation</span>
<label class="switch">
<input type="checkbox" name="install">
<span class="slider"></span>
</label>
</div>

</div>

<div class="section">
<label>Customer Name</label>
<input name="customer">

<label>Project Reference</label>
<input name="project">

<label>Site Address</label>
<textarea name="address"></textarea>
</div>

<button type="submit">Calculate & Generate Quote</button>

</form>

{% if result %}
<div class="result">

<h3>Calculation Summary</h3>

<p><b>Total Area:</b> {{result.total_area}} m²</p>
<p><b>Corner Deduction:</b> {{result.corner_area}} m²</p>
<p><b>Net Area:</b> {{result.net_area}} m²</p>
<p><b>Area with Wastage:</b> {{result.area_waste}} m²</p>

<div class="divider"></div>

<h3>Cost Breakdown</h3>

<p>Body: {{result.area_waste}} × {{result.body_rate}} = <b>${{result.body_total}}</b></p>
<p>Corner: {{result.corner_pcs}} pcs × {{result.corner_rate}} = <b>${{result.corner_total}}</b></p>

{% if result.install %}
<p>Installation Body: <b>${{result.install_body}}</b></p>
<p>Installation Corner: <b>${{result.install_corner}}</b></p>
{% endif %}

<div class="divider"></div>

<h2>Total (Inc GST): ${{result.total}}</h2>

<form method="post" action="/pdf">
{% for k,v in result.items() %}
<input type="hidden" name="{{k}}" value="{{v}}">
{% endfor %}
<button type="submit">Download Quote (PDF)</button>
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

        typ=request.form.get("type")
        p=PRODUCTS.get(request.form.get("product"))

        length=float(request.form.get("length") or 0)
        height=float(request.form.get("height") or 0)
        corner_lm=float(request.form.get("corner_lm") or 0)

        ph=float(request.form.get("pillar_height") or 0)
        front=float(request.form.get("front") or 0)
        depth=float(request.form.get("depth") or 0)
        sides=int(request.form.get("sides") or 3)

        if typ in ["wall","floor"]:
            area=length*height
        else:
            if sides==4:
                area=ph*(2*front+2*depth)
                corner_lm=ph*4
            else:
                area=ph*(front+2*depth)
                corner_lm=ph*2

        total_area=area
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
            "corner_lm":round(corner_lm,2),
            "corner_pcs":corner_pcs,
            "body_rate":p["body_price"],
            "corner_rate":p["corner_price"],
            "body_total":round(body_total,2),
            "corner_total":round(corner_total,2),
            "install":request.form.get("install"),
            "install_body":round(install_body,2),
            "install_corner":round(install_corner,2),
            "subtotal":round(subtotal,2),
            "gst":round(gst,2),
            "total":round(total,2),
            "customer":request.form.get("customer"),
            "project":request.form.get("project"),
            "address":request.form.get("address")
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
    right = ParagraphStyle(name='r', alignment=TA_RIGHT)

    story = []

    try:
        story.append(Image("ppm-stone-logo.png", width=150, height=70))
    except:
        pass

    story.append(Paragraph("<b>PPM Stone</b>", styles['Title']))
    story.append(Paragraph("PPM Enterprises Pty Ltd", styles['Normal']))
    story.append(Paragraph("Factory 2, 64-70 Edison Road Dandenong South VIC 3175", styles['Normal']))
    story.append(Paragraph("Tel: 1300 278 355", styles['Normal']))
    story.append(Paragraph("E-mail: admin@ppmstone.com.au", styles['Normal']))
    story.append(Paragraph("ABN: 79 116 045 553", styles['Normal']))

    story.append(Spacer(1,10))
    story.append(Paragraph("<b>QUOTE</b>", center))
    story.append(Spacer(1,10))

    now=datetime.now()
    story.append(Paragraph(now.strftime("Quote No: QU-%y%m%d01"), styles['Normal']))
    story.append(Paragraph(now.strftime("Date: %d/%m/%Y"), styles['Normal']))

    story.append(Spacer(1,10))

    story.append(Paragraph("<b>Customer Details</b>", styles['Heading3']))
    story.append(Paragraph(f"Customer Name: {request.form.get('customer')}", styles['Normal']))
    story.append(Paragraph(f"Project Reference: {request.form.get('project')}", styles['Normal']))
    story.append(Paragraph(f"Site Address: {request.form.get('address')}", styles['Normal']))

    story.append(Spacer(1,15))

    product=request.form.get("product")

    table=[
        ["Code","Qty","Unit","Description","Unit Price","Amount"],
        [request.form.get("body_code"),request.form.get("area_waste"),"m²",
         Paragraph(f"PPM Cladding | Body | {product} | Irregular 20–40mm", styles['Normal']),
         "$"+money(request.form.get("body_rate")),
         "$"+money(request.form.get("body_total"))],

        [request.form.get("corner_code"),request.form.get("corner_pcs"),"pcs",
         Paragraph(f"PPM Cladding | Corner | {product} | Irregular 20–40mm", styles['Normal']),
         "$"+money(request.form.get("corner_rate")),
         "$"+money(request.form.get("corner_total"))],
    ]

    if request.form.get("install")=="on":
        table.append([request.form.get("body_code")+"-I",request.form.get("area_waste"),"m²","Installation Body","$120","$"+money(request.form.get("install_body"))])
        table.append([request.form.get("corner_code")+"-I",request.form.get("corner_lm"),"LM","Installation Corner","$120","$"+money(request.form.get("install_corner"))])

    t2=Table(table, colWidths=[60,50,40,200,80,80])
    t2.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('ALIGN',(-1,1),(-1,-1),'RIGHT'),
        ('ALIGN',(-2,1),(-2,-1),'RIGHT')
    ]))

    story.append(t2)

    totals = [
        ["Subtotal (Ex GST)", "$"+money(request.form.get("subtotal"))],
        ["GST (10%)", "$"+money(request.form.get("gst"))],
        ["Total (Inc GST)", "$"+money(request.form.get("total"))]
    ]

    t3 = Table(totals, colWidths=[300,100])
    t3.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('ALIGN',(1,0),(1,-1),'RIGHT'),
        ('BACKGROUND',(0,2),(-1,2),colors.lightgrey),
        ('FONTNAME',(0,2),(-1,2),'Helvetica-Bold')
    ]))

    story.append(Spacer(1,15))
    story.append(t3)

    story.append(Spacer(1,15))

    story.append(Paragraph("<b>Notes:</b> This is an estimate of cost, final figures may vary after site inspection.", styles['Normal']))
    story.append(Paragraph("<b>Disclaimer:</b> Please note that our bluestones and stone claddings are natural, so variations in colour, texture, and veining may occur. These differences from samples or images are natural and enhance the stone's unique character.", styles['Normal']))

    doc.build(story)

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="QUOTE.pdf")


# =========================
# RUN (DEPLOY READY)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
