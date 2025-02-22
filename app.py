import qrcode, socket
import sqlite3
import uuid
from flask import Flask, request, jsonify, send_file,redirect
from io import BytesIO
from flask import render_template

# Initialize Flask app
app = Flask(__name__)

# Database setup
DB_FILE = "qrcodes.db"

@app.route('/')
def home():
    return render_template('index.html')

def getLocatIp():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    localIp=s.getsockname()[0]
    s.close
    return localIp
def init_db():
    """Create database table if not exists."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qr_codes (
            id TEXT PRIMARY KEY,
            link TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()  # Ensure DB is initialized

def save_qr_code(qr_id, link):
    """Save a new QR code and link to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO qr_codes (id, link) VALUES (?, ?)", (qr_id, link))
    conn.commit()
    conn.close()

def update_qr_code(qr_id, new_link):
    """Update the link for an existing QR code."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE qr_codes SET link = ? WHERE id = ?", (new_link, qr_id))
    conn.commit()
    conn.close()

def get_qr_code_link(qr_id):
    """Retrieve the link associated with a QR code."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT link FROM qr_codes WHERE id = ?", (qr_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
HostIp=getLocatIp()
def generate_qr(qr_id):
    """Generate a QR code image based on the stored ID."""
    qr = qrcode.make(f"http://{HostIp}:5000/redirect/{qr_id}")
    img_io = BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

@app.route('/create_qr', methods=['POST'])
def create_qr():
    """Create a new QR code with a given link."""
    data = request.json
    link = data.get('link')
    if not link:
        return jsonify({"error": "No link provided"}), 400

    qr_id = str(uuid.uuid4())[:8]  # Generate a short unique ID
    save_qr_code(qr_id, link)
    return jsonify({"qr_id": qr_id, "qr_code_url": f"http://127.0.0.1:5000/qr/{qr_id}"})

@app.route('/qr/<qr_id>', methods=['GET'])
def get_qr(qr_id):
    """Return the QR code image."""
    if get_qr_code_link(qr_id):
        return send_file(generate_qr(qr_id), mimetype='image/png')
    return jsonify({"error": "QR Code not found"}), 404

@app.route('/update_qr/<qr_id>', methods=['PUT'])
def update_qr(qr_id):
    """Update the link for an existing QR code."""
    data = request.json
    new_link = data.get('link')
    if not new_link:
        return jsonify({"error": "No new link provided"}), 400

    if get_qr_code_link(qr_id):
        update_qr_code(qr_id, new_link)
        return jsonify({"message": "QR code updated successfully"})
    return jsonify({"error": "QR Code not found"}), 404

@app.route('/redirect/<qr_id>', methods=['GET'])
def redirect_qr(qr_id):
    """Redirect to the latest stored link for the QR code."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT link FROM qr_codes WHERE id = ?", (qr_id,))
    result = cursor.fetchone()
    
    if  result:
        return redirect(result[0],code=302)
    else:
        return jsonify({"error": "QR Code not found"}), 404
    

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=5000,debug=True)
