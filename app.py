# =========================
# IMPORTS
# =========================
from flask import Flask, request, render_template_string, send_file
import math, io, os
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

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

<style>
body {font-family: Arial; background:#f4f6f8;}
.container {max-width:900px;margin:auto;background:white;padding:30px;border-radius:10px;}

.section {margin-top:20px;}
input, select, textarea {
    width:100%; padding:10px; margin-top:8px;
    border:1px solid #ccc; border-radius:6px;
}

.row {display:flex; gap:10px;}
.row input {flex:1;}

button {
    width:100%; padding:14px; margin-top:20px;
    background:black; color:white; border:none;
}

.hidden {display:none;}

.switch {position:relative;width:50px;height:25px;}
.switch input {display:none;}
.slider {
    position:absolute;top:0;left:0;right:0;bottom:0;
    background:#ccc;border-radius:25px;
}
.slider:before {
    content:""; position:absolute;
    width:20px;height:20px;left:3px;bottom:3px;
    background:white;border-radius:50%;
}
input:checked + .slider {background:black;}
input:checked + .slider:before {transform:translateX(24px);}
</style>

<script>
function toggleFields(){
    let type = document.getElementById("type").value;

    document.getElementById("wallSection").style.display =
        (type === "wall" || type === "floor") ? "block" : "none";

    document.getElementById("pillarSection").style.display =
        (type === "pillar") ? "block" : "none";
}
</script>

</head>

<body>

<div class="container">

<h2>PPM Cladding Calculator</h2>

<form method="post">

<div class="section">
<label>Application Type</label>
<select name="type" id="type" onchange="toggleFields()" required>
<option value="">-- Select --</option>
<option value="wall">Wall</option>
<option value="floor">Floor</option>
<option value="pillar">Pillar</option>
</select>
</div>

<div id="wallSection" class="section hidden">
<h3>Wall / Floor Inputs</h3>

<div class="row">
<input name="length" placeholder="Length (m)">
<input name="height" placeholder="Height / Width (m)">
</div>

<input name="corner_lm" placeholder="Corner Length (LM)">
</div>

<div id="pillarSection" class="section hidden">
<h3>Pillar Inputs</h3>

<div class="row">
<input name="pillar_height" placeholder="Pillar Height (m)">
<input name="front" placeholder="Front Width (m)">
</div>

<input name="depth" placeholder="Return Depth (m)">

<select name="sides">
<option value="3">3 Sides</option>
<option value="4">4 Sides</option>
</select>
</div>

<div class="section">
<label>Product</label>
<select name="product">
{% for k,p in products.items() %}
<option value="{{k}}">{{p.name}} ({{p.body_code}})</option>
{% endfor %}
</select>
</div>

<div class="section" style="display:flex;justify-content:space-between;align-items:center;">
<span>Include Installation</span>
<label class="switch">
<input type="checkbox" name="install">
<span class="slider"></span>
</label>
</div>

<div class="section">
<input name="customer" placeholder="Customer Name">
<input name="project" placeholder="Project Reference">
<textarea name="address" placeholder="Site Address"></textarea>
</div>

<button type="submit">Calculate</button>

</form>

{% if result %}
<hr>

<h3>Calculation</h3>

<p>Total Area: {{result.total_area}} m²</p>
<p>Corner Area: {{result.corner_area}} m²</p>
<p>Net Area: {{result.net_area}} m²</p>
<p>With Wastage: {{result.area_waste}} m²</p>

<h3>Costs</h3>

<p>Body: ${{result.body_total}}</p>
<p>Corner: ${{result.corner_total}}</p>

{% if result.install %}
<p>Installation Body: ${{result.install_body}}</p>
<p>Installation Corner: ${{result.install_corner}}</p>
{% endif %}

<h2>Total (Inc GST): ${{result.total}}</h2>

<form method="post" action="/pdf">
{% for k,v in result.items() %}
<input type="hidden" name="{{k}}" value="{{v}}">
{% endfor %}
<button>Download PDF</button>
</form>

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

    if request.method == "POST":

        typ = request.form.get("type")
        p = PRODUCTS.get(request.form.get("product"))

        length = float(request.form.get("length") or 0)
        height = float(request.form.get("height") or 0)
        corner_lm = float(request.form.get("corner_lm") or 0)

        ph = float(request.form.get("pillar_height") or 0)
        front = float(request.form.get("front") or 0)
        depth = float(request.form.get("depth") or 0)
        sides = int(request.form.get("sides") or 3)

        if typ in ["wall","floor"]:
            area = length * height
        else:
            if sides == 4:
                area = ph * (2*front + 2*depth)
                corner_lm = ph * 4
            else:
                area = ph * (front + 2*depth)
                corner_lm = ph * 2

        total_area = area
        corner_area = corner_lm * (2 * CORNER_RETURN)
        net_area = max(total_area - corner_area, 0)
        area_waste = net_area * 1.1

        corner_pcs = math.ceil(corner_lm / PIECE_HEIGHT)

        body_total = area_waste * p["body_price"]
        corner_total = corner_pcs * p["corner_price"]

        install_body = install_corner = 0
        if request.form.get("install"):
            install_body = area_waste * INSTALL_BODY_RATE
            install_corner = corner_lm * INSTALL_CORNER_RATE

        subtotal = body_total + corner_total + install_body + install_corner
        gst = subtotal * GST_RATE
        total = subtotal + gst

        result = {
            "total_area": round(total_area,2),
            "corner_area": round(corner_area,2),
            "net_area": round(net_area,2),
            "area_waste": round(area_waste,2),
            "body_total": round(body_total,2),
            "corner_total": round(corner_total,2),
            "install": request.form.get("install"),
            "install_body": round(install_body,2),
            "install_corner": round(install_corner,2),
            "total": round(total,2)
        }

        return render_template_string(HTML, result=result, products=PRODUCTS)

    return render_template_string(HTML, result=None, products=PRODUCTS)

# =========================
# PDF
# =========================
@app.route("/pdf", methods=["POST"])
def pdf():

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("PPM QUOTE", styles['Title']))
    story.append(Spacer(1,10))

    story.append(Paragraph("Total: $" + request.form.get("total"), styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="QUOTE.pdf")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
