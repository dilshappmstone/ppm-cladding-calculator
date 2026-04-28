from flask import Flask, request, render_template_string, send_file, redirect
import math, io, os
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ================= CONFIG =================
app.config['SECRET_KEY'] = 'ppm_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ================= INIT =================
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ================= MODEL =================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    customer = db.Column(db.String(100))
    project = db.Column(db.String(100))
    total = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= CREATE DB =================
with app.app_context():
    db.create_all()

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

<style>
body {
    font-family: Arial;
    background:#f4f6f8;
    margin:0;
}
.container {
    max-width:950px;
    margin:30px auto;
    background:white;
    padding:30px;
    border-radius:10px;
    box-shadow:0 6px 20px rgba(0,0,0,0.08);
}
.section { margin-bottom:25px; }

label {
    font-weight:600;
    display:block;
    margin-top:10px;
}

input, select, textarea {
    width:100%;
    padding:10px;
    border:1px solid #ccc;
    border-radius:6px;
    margin-top:5px;
}

button {
    margin-top:15px;
    padding:12px;
    background:black;
    color:white;
    border:none;
    border-radius:6px;
    font-size:15px;
    cursor:pointer;
}

.add-btn {
    background:#2d7ef7;
}

.remove-btn {
    background:#d9534f;
    margin-top:10px;
}

.area-box {
    border:1px solid #ddd;
    padding:15px;
    margin-top:15px;
    border-radius:8px;
    background:#fafafa;
}

.area-title {
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.result {
    margin-top:30px;
    padding:20px;
    background:#f9fafb;
    border-radius:8px;
    border:1px solid #ddd;
}
</style>

<script>
let areaCount = 0;

function addArea() {
    areaCount++;

    let html = `
    <div class="area-box" id="area_${areaCount}">

        <div class="area-title">
            <b>Area ${areaCount}</b>
            <button type="button" class="remove-btn" onclick="removeArea(${areaCount})">Remove</button>
        </div>

        <label>Type</label>
        <select name="type_${areaCount}" onchange="toggleArea(${areaCount}, this.value)">
            <option value="">Select Type</option>
            <option value="wall">Wall</option>
            <option value="floor">Floor</option>
            <option value="pillar">Pillar</option>
            <option value="curve">Curve Wall</option>
        </select>

        <!-- WALL -->
        <div id="wall_${areaCount}" style="display:none;">
            <h4>Wall / Floor</h4>

            <label>Length (m)</label>
            <input name="length_${areaCount}">

            <label>Height (m)</label>
            <input name="height_${areaCount}">

            <label>Corner LM</label>
            <input name="corner_${areaCount}">
        </div>

        <!-- PILLAR -->
        <div id="pillar_${areaCount}" style="display:none;">
            <h4>Pillar</h4>

            <label>Pillar Height</label>
            <input name="pillar_height_${areaCount}">

            <label>Front Width</label>
            <input name="front_${areaCount}">

            <label>Depth</label>
            <input name="depth_${areaCount}">

            <label>Sides</label>
            <select name="sides_${areaCount}">
                <option value="3">3</option>
                <option value="4">4</option>
            </select>
        </div>

        <!-- CURVE -->
        <div id="curve_${areaCount}" style="display:none;">
            <h4>Curve Wall</h4>

            <label>Value</label>
            <input name="curve_value_${areaCount}">

            <label>Mode</label>
            <select name="curve_mode_${areaCount}">
                <option value="radius">Radius</option>
                <option value="diameter">Diameter</option>
            </select>

            <label>Curve Type</label>
            <select name="curve_type_${areaCount}">
                <option value="half">Half</option>
                <option value="quarter">Quarter</option>
            </select>

            <label>Height</label>
            <input name="height_${areaCount}">
        </div>

    </div>
    `;

    document.getElementById("areas").insertAdjacentHTML("beforeend", html);
}

function removeArea(id){
    document.getElementById("area_" + id).remove();
}

function toggleArea(id, type) {
    document.getElementById("wall_" + id).style.display = "none";
    document.getElementById("pillar_" + id).style.display = "none";
    document.getElementById("curve_" + id).style.display = "none";

    if (type === "wall" || type === "floor") {
        document.getElementById("wall_" + id).style.display = "block";
    }
    else if (type === "pillar") {
        document.getElementById("pillar_" + id).style.display = "block";
    }
    else if (type === "curve") {
        document.getElementById("curve_" + id).style.display = "block";
    }
}

window.onload = function() {
    addArea();
};
</script>

</head>

<body>

<div class="container">

<div style="margin-bottom:20px;">
<a href="/">Home</a> |
<a href="/quote">Quote</a> |
<a href="/history">History</a> |
<a href="/logout">Logout</a>
</div>

<h1>PPM Cladding Calculator</h1>
<p>Estimate quantities & generate professional quotes</p>

<form method="post">

<div class="section">
<label>Project Areas</label>
<button type="button" class="add-btn" onclick="addArea()">+ Add Area</button>
<div id="areas"></div>
</div>

<div class="section">
<label>Product</label>
<select name="product">
{% for k,p in products.items() %}
<option value="{{k}}">
{{p.name}} ({{p.body_code}} / {{p.corner_code}})
</option>
{% endfor %}
</select>
</div>

<div class="section">
<label>Include Installation</label>
<input type="checkbox" name="install">
</div>

<div class="section">
<label>Customer Name</label>
<input name="customer">

<label>Project</label>
<input name="project">

<label>Address</label>
<textarea name="address"></textarea>
</div>

<button>Generate Quote</button>

</form>

{% if result %}
<div class="result">

<h3>Project Summary</h3>

<p><b>Customer:</b> {{result.customer}}</p>
<p><b>Project:</b> {{result.project}}</p>

<hr>

<h3>Areas</h3>

{% for a in result.areas %}
<div style="border:1px solid #ddd; padding:10px; margin-bottom:10px; border-radius:6px;">
    
    <b>Type:</b> {{a.type}}<br>

    {% if a.type == "wall" or a.type == "floor" %}
    Length: {{a.length}} m<br>
    Height: {{a.height}} m<br>
    Corner: {{a.corner}}<br>
    {% endif %}

    {% if a.type == "pillar" %}
    Pillar Height: {{a.pillar_height}} m<br>
    Front: {{a.front}} m<br>
    Depth: {{a.depth}} m<br>
    {% endif %}

    <b>Area:</b> {{a.area}} m²

</div>
{% endfor %}

<hr>

<hr>

<h3>Calculation Summary</h3>

<p><b>Total Area:</b> {{result.total_area}} m²</p>
<p><b>Corner Deduction:</b> {{result.corner_area}} m²</p>
<p><b>Net Area:</b> {{result.net_area}} m²</p>
<p><b>Area with Wastage (10%):</b> {{result.area_waste}} m²</p>

<hr>

<h3>Cost Breakdown</h3>

<p>
Body: {{result.area_waste}} × ${{result.body_rate}}  
= <b>${{result.body_total}}</b>
</p>

<p>
Corner: {{result.corner_pcs}} pcs × ${{result.corner_rate}}  
= <b>${{result.corner_total}}</b>
</p>

{% if result.install %}
<p>Installation Body: <b>${{result.install_body}}</b></p>
<p>Installation Corner: <b>${{result.install_corner}}</b></p>
{% endif %}

<hr>

<h3>Totals</h3>

<p>Subtotal: ${{result.subtotal}}</p>
<p>GST (10%): ${{result.gst}}</p>

<h2>Total (Inc GST): ${{result.total}}</h2>

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
# AUTH
# =========================
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            return "Missing email or password"

        if User.query.filter_by(email=email).first():
            return "User already exists"

        user = User(
            email=email,
            password=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return """
    <h2>Register</h2>
    <form method="post">
    <input name="email"><br><br>
    <input name="password" type="password"><br><br>
    <button>Register</button>
    </form>
    """


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect("/")

        return "Invalid login"

    return """
    <h2>Login</h2>
    <form method="post">
    <input name="email"><br><br>
    <input name="password" type="password"><br><br>
    <button>Login</button>
    </form>
    <a href="/register">Register</a>
    """


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# =========================
# HOME (NEW)
# =========================
@app.route("/")
@login_required
def home():
    return """
    <h2>PPM Dashboard</h2>
    <p>Welcome! Use navigation:</p>
    <a href="/quote">Go to Calculator</a><br><br>
    <a href="/history">View Quote History</a>
    """


# =========================
# QUOTE (YOUR CALCULATOR MOVED HERE)
# =========================
@app.route("/quote", methods=["GET","POST"])
@login_required
def quote():

    if request.method=="POST":

        p = PRODUCTS.get(request.form.get("product"))

        total_area = 0
        total_corner_lm = 0

        # ================= MULTI AREA =================
        i = 1
        found_multi = False
        area_list = []

        while True:
            if f"type_{i}" not in request.form:
                break

            found_multi = True

            typ = request.form.get(f"type_{i}")

            length = float(request.form.get(f"length_{i}") or 0)
            height = float(request.form.get(f"height_{i}") or 0)
            corner = float(request.form.get(f"corner_{i}") or 0)

            ph = float(request.form.get(f"pillar_height_{i}") or 0)
            front = float(request.form.get(f"front_{i}") or 0)
            depth = float(request.form.get(f"depth_{i}") or 0)
            sides = int(request.form.get(f"sides_{i}") or 3)

            # ===== TYPE LOGIC =====
            if typ in ["wall","floor"]:
                area = length * height

            elif typ == "pillar":
                if sides == 4:
                    area = ph * (2*front + 2*depth)
                    corner = ph * 4
                else:
                    area = ph * (front + 2*depth)
                    corner = ph * 2

            elif typ == "curve":
                value = float(request.form.get(f"curve_value_{i}") or 0)
                mode = request.form.get(f"curve_mode_{i}")
                curve_type = request.form.get(f"curve_type_{i}")

                r = value / 2 if mode == "diameter" else value
                arc = math.pi * r if curve_type == "half" else (math.pi * r)/2

                area = arc * height

            else:
                area = 0

            total_area += area
            total_corner_lm += corner

            area_list.append({
                "type": typ,
                "length": length,
                "height": height,
                "corner": corner,
                "pillar_height": ph,
                "front": front,
                "depth": depth,
                "sides": sides,
                "area": round(area, 2)
            })

            i += 1


        # ================= SINGLE AREA (fallback) =================
        if not found_multi:

            typ = request.form.get("type")

            length=float(request.form.get("length") or 0)
            height=float(request.form.get("height") or 0)
            corner_lm=float(request.form.get("corner_lm") or 0)

            ph=float(request.form.get("pillar_height") or 0)
            front=float(request.form.get("front") or 0)
            depth=float(request.form.get("depth") or 0)
            sides=int(request.form.get("sides") or 3)

            if typ in ["wall","floor"]:
                total_area = length * height
                total_corner_lm = corner_lm
            else:
                if sides == 4:
                    total_area = ph*(2*front + 2*depth)
                    total_corner_lm = ph*4
                else:
                    total_area = ph*(front + 2*depth)
                    total_corner_lm = ph*2


        # ================= CALCULATION =================
        corner_area = total_corner_lm*(2*CORNER_RETURN)
        net_area = max(total_area-corner_area,0)
        area_waste = net_area*1.1

        corner_pcs = math.ceil(total_corner_lm/PIECE_HEIGHT)

        body_total = area_waste*p["body_price"]
        corner_total = corner_pcs*p["corner_price"]

        install_body = install_corner = 0
        if request.form.get("install"):
            install_body = area_waste*INSTALL_BODY_RATE
            install_corner = total_corner_lm*INSTALL_CORNER_RATE

        subtotal = body_total+corner_total+install_body+install_corner
        gst = subtotal*GST_RATE
        total = subtotal+gst


        # ================= RESULT =================
        result = {
            "product_name": p["name"],
            "size": p["size"],
            "body_code": p["body_code"],
            "corner_code": p["corner_code"],
            "areas": area_list,

            "area_waste": round(area_waste, 2),
            "corner_pcs": corner_pcs,

            "body_rate": p["body_price"],
            "corner_rate": p["corner_price"],

            "body_total": round(body_total, 2),
            "corner_total": round(corner_total, 2),

            "install": request.form.get("install"),
            "install_body": round(install_body, 2),
            "install_corner": round(install_corner, 2),

            "subtotal": round(subtotal, 2),
            "gst": round(gst, 2),
            "total": round(total, 2),

            "customer": request.form.get("customer") or "",
            "project": request.form.get("project") or "",
            "address": request.form.get("address") or "",

            "total_area": round(total_area, 2),
            "corner_area": round(corner_area, 2),
            "net_area": round(net_area, 2)
        }


        # ================= SAVE =================
        db.session.add(Quote(
            user_id=current_user.id,
            customer=result["customer"],
            project=result["project"],
            total=result["total"]
        ))
        db.session.commit()

        return render_template_string(HTML, result=result, products=PRODUCTS)

    return render_template_string(HTML, result=None, products=PRODUCTS)


# =========================
# HISTORY (DASHBOARD)
# =========================
@app.route("/history")
@login_required
def history():

    quotes = Quote.query.filter_by(user_id=current_user.id).all()

    rows = ""
    for q in quotes:
        rows += f"""
        <tr>
            <td>{q.customer}</td>
            <td>{q.project}</td>
            <td>${q.total}</td>
        </tr>
        """

    return f"""
    <h2>Quote History</h2>

    <table border="1" cellpadding="10">
        <tr>
            <th>Customer</th>
            <th>Project</th>
            <th>Total</th>
        </tr>
        {rows}
    </table>

    <br><a href="/quote">Back to Calculator</a>
    """

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
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
