from flask import Flask, request, render_template_string, send_file
import math, io, os
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

app = Flask(__name__)

PIECE_HEIGHT = 0.2
CORNER_RETURN = 0.1
INSTALL_BODY_RATE = 120
INSTALL_CORNER_RATE = 120
GST_RATE = 0.10

PRODUCTS = {
    "RB": {"name": "Royal Blue", "body_code": "CLD005", "corner_code": "CLD006", "body_price": 75, "corner_price": 25},
    "IWQ": {"name": "Ivory White Quartz", "body_code": "CLD007", "corner_code": "CLD008", "body_price": 75, "corner_price": 25},
    "AWQ": {"name": "Artic White Quartz", "body_code": "CLD009", "corner_code": "CLD010", "body_price": 75, "corner_price": 25},
    "CC": {"name": "Country Cross", "body_code": "CLD011", "corner_code": "CLD012", "body_price": 75, "corner_price": 25}
}

def money(v):
    return "{:.2f}".format(float(v))

# =========================
# HTML
# =========================
HTML = """<!DOCTYPE html>
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

 document.getElementById("wallSection").style.display =
    (t=="wall" || t=="floor") ? "block" : "none";

 document.getElementById("pillarSection").style.display =
    (t=="pillar") ? "block" : "none";
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

<div id="wallSection" style="display:none;">
<div class="row">
<input name="length" placeholder="Length (m)">
<input name="height" placeholder="Height / Width (m)">
</div>
<input name="corner_lm" placeholder="Corner Length (LM)">
</div>

<div id="pillarSection" style="display:none;">
<div class="row">
<input name="pillar_height" placeholder="Pillar Height (m)">
<input name="front" placeholder="Front Width (m)">
</div>
<input name="depth" placeholder="Return Depth (m)">
<select name="sides">
<option value="3">3 sides</option>
<option value="4">4 sides</option>
</select>
</div>

<select name="product">
{% for k,p in products.items() %}
<option value="{{k}}">
{{p.name}} ({{p.body_code}} / {{p.corner_code}})
</option>
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
<p>Total Area: {{result.total_area}}</p>
<p>Total: ${{result.total}}</p>

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
            "product":p["name"],
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
            "total_area":total_area
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

    story.append(Paragraph("<b>PPM STONE QUOTE</b>", styles['Title']))

    table = [
        ["Subtotal", "$"+money(request.form.get("subtotal"))],
        ["GST", "$"+money(request.form.get("gst"))],
        ["Total", "$"+money(request.form.get("total"))]
    ]

    story.append(Table(table))

    # ✅ FIXED NOTES SECTION (NOW INSIDE FUNCTION)
    story.append(Spacer(1,20))
    story.append(Paragraph("Notes:", styles['Heading3']))
    story.append(Paragraph(
        "This is an estimate of cost, the final figures may vary after the final site inspection.",
        styles['Normal']
    ))

    story.append(Spacer(1,10))
    story.append(Paragraph("Disclaimer:", styles['Heading3']))
    story.append(Paragraph(
        "Please note that our bluestones and stone claddings are natural, so variations in colour, texture, and veining may occur. These differences from samples or images are natural and enhance the stone's unique character.", styles['Normal'].",
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
