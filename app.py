from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os, json, uuid
from twilio.rest import Client
import requests

app = Flask(__name__)
VCARD_FOLDER = "vcards"
DATA_FILE = "contacts.json"

TWILIO_SID = "AC3da2934b4ac8d9078cf1d9d0e206af6e"
TWILIO_TOKEN = "81ed71aff32eceabd9a6858fde0da7f1"
TWILIO_NUMBER = "whatsapp:+14155238886"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.form.to_dict()
        contact_id = str(uuid.uuid4())
        data["id"] = contact_id

        with open(DATA_FILE, "r") as f:
            contacts = json.load(f)
        contacts[contact_id] = data

        with open(DATA_FILE, "w") as f:
            json.dump(contacts, f)

        vcf_content = f"""BEGIN:VCARD
VERSION:3.0
FN:{data['name']}
TEL;TYPE=CELL:{data['phone']}
EMAIL:{data['email']}
END:VCARD"""
        vcf_path = os.path.join(VCARD_FOLDER, f"{contact_id}.vcf")
        with open(vcf_path, "w") as f:
            f.write(vcf_content)

        return redirect(url_for("view_card", card_id=contact_id))
    return render_template("index.html")

@app.route("/card/<card_id>")
def view_card(card_id):
    with open(DATA_FILE, "r") as f:
        contacts = json.load(f)
    contact = contacts.get(card_id)
    if not contact:
        return "Contact not found", 404
    return render_template("view_card.html", contact=contact)

@app.route("/vcards/<filename>")
def serve_vcf(filename):
    return send_from_directory(VCARD_FOLDER, filename, mimetype="text/vcard")

@app.route("/exchange/<card_id>", methods=["GET", "POST"])
def exchange(card_id):
    with open(DATA_FILE, "r") as f:
        contacts = json.load(f)
    original_contact = contacts.get(card_id)
    if not original_contact:
        return "Original contact not found", 404

    if request.method == "POST":
        user_data = request.form.to_dict()
        user_vcf = f"""BEGIN:VCARD
VERSION:3.0
FN:{user_data['name']}
TEL;TYPE=CELL:{user_data['phone']}
EMAIL:{user_data['email']}
END:VCARD"""
        user_vcf_name = f"{uuid.uuid4()}.vcf"
        user_vcf_path = os.path.join(VCARD_FOLDER, user_vcf_name)
        with open(user_vcf_path, "w") as f:
            f.write(user_vcf)

        # Upload to Render API
        upload_url = "https://vcf-api.onrender.com/upload"
        with open(user_vcf_path, "rb") as f:
            response = requests.post(upload_url, files={"file": f})

        if response.status_code != 200:
            return f"❌ Upload failed: {response.text}", 500

        vcf_file_url = response.json()["url"]

        # Send via Twilio
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            from_=TWILIO_NUMBER,
            to="whatsapp:" + original_contact["phone"],
            body=f"📇 {user_data['name']} just exchanged contact with you!",
            media_url=[vcf_file_url]
        )
        return "✅ Contact exchanged and sent via WhatsApp!"

    return render_template("exchange.html", card_id=card_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
