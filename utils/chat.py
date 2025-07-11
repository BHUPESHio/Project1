from flask import Blueprint, request, jsonify, render_template
from utils.gemini_bot import generate_reply
from werkzeug.utils import secure_filename
import base64
from flask_login import current_user
from pymongo import MongoClient

# MongoDB connection
MONGO_URI = "mongodb+srv://Admin:bait1783@fitrackdb.o4yvman.mongodb.net/?retryWrites=true&w=majority&appName=fitrackdb"
mongo = MongoClient(MONGO_URI)
db = mongo["myDatabase"]
chats = db["chat_history"]

# Blueprint
chat_bp = Blueprint("chat", __name__)

# Route: Health Chat API
@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    user_input = request.form.get("message")
    file = request.files.get("file")

    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    # Prepare file data (future: vision API)
    file_data = None
    filename = None
    if file:
        filename = secure_filename(file.filename)
        file_content = file.read()
        file_data = {
            "mime_type": file.mimetype,
            "data": base64.b64encode(file_content).decode("utf-8")
        }

    try:
        reply = generate_reply(user_input, file_data=file_data)
    except Exception as e:
        reply = "An error occurred while processing your request."

    # Store chat in MongoDB
    chats.insert_one({
        "user_id": str(current_user.get_id()),
        "question": user_input,
        "reply": reply,
        "file_used": filename if file else None
    })

    return jsonify({"reply": reply})

# Chat page route
@chat_bp.route("/chat")
def chat_page():
    return render_template("chat.html")
