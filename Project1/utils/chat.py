from flask import Blueprint, request, jsonify, render_template, send_file
from flask_login import current_user, login_required
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.utils import secure_filename
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import base64
import re
import google.generativeai as genai

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://Admin:bait1783@fitrackdb.o4yvman.mongodb.net/?retryWrites=true&w=majority&appName=fitrackdb"
mongo = MongoClient(MONGO_URI)
db = mongo["myDatabase"]
chats = db["chat_history"]
memory = db["user_memory"]

# Blueprint
chat_bp = Blueprint("chat", __name__)

# Memory Functions
def get_user_memory(user_id):
    result = memory.find_one({"user_id": user_id}) or {}
    print(f"[MEMORY LOAD] Retrieved from user_memory: {result}")
    return result

def update_user_memory(user_id, updates: dict):
    print(f"[MEMORY SET] Saving to user_memory for {user_id}: {updates}")
    memory.update_one({"user_id": user_id}, {"$set": updates}, upsert=True)

# Main Chat Route
@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def chat():
    user_input = request.form.get("message")
    file = request.files.get("file")
    user_id = str(current_user.get_id())

    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    # Prepare file (if any)
    file_data = None
    filename = None
    if file:
        filename = secure_filename(file.filename)
        file_content = file.read()
        file_data = {
            "mime_type": file.mimetype,
            "data": base64.b64encode(file_content).decode("utf-8")
        }

    # Detect name in message
    name_match = re.match(r"(my name is|i am|i'm)\s+(\w+)", user_input.lower())
    if name_match:
        name = name_match.group(2).capitalize()
        update_user_memory(user_id, {"name": name})

    # Load memory and prepare context
    user_memory = get_user_memory(user_id)
    memory_summary = ""
    if "name" in user_memory:
        memory_summary += f"User's name is {user_memory['name']}. "
    memory_summary += (
    "You are FitBot, a professional fitness coach and assistant. You only answer health-related questions like:\n"
    "- Gym, workouts, yoga\n"
    "- Muscle building, weight loss\n"
    "- Food, calorie intake, protein tracking\n"
    "- Supplements and body recovery\n"
    "- Remedies for muscle injury or soreness\n\n"

    "You must remember personal info shared by the user (e.g. their name, protein goal, injury) and refer to it when needed.\n\n"

    "🧠 FORMAT RULES:\n"
    "1. Start with a short, direct summary in **bold**.\n"
    "2. Use clear section titles with emojis like:\n"
    "   '💪 Workout Plan', '🥗 Diet Plan', '📊 Summary', '📅 Weekly Plan'\n"
    "3. Space out each section clearly (no long paragraphs).\n"
    "4. Use bullet points for lists, but use **Markdown tables** when sharing plans, meals, or comparisons.\n"
    "5. Add 1 line gap between major sections. Keep it visually clean.\n"
    "6. Bold keywords (e.g. Meal, Protein) and use **|tables|** for summaries like this:\n\n"
    "| Meal      | Dish               | Protein |\n"
    "|-----------|--------------------|---------|\n"
    "| Breakfast | 2 Eggs             | 12g     |\n"
    "| Lunch     | Soya Chunks Curry  | 25g     |\n"
    "| Dinner    | Toor Dal Soup      | 15g     |\n\n"

    "7. End with a reminder, encouragement, or friendly sign-off like 'You're doing great, Bhupesh! 💪'\n\n"

    "❌ Do not answer non-fitness topics.\n"
    "❌ Never write long unbroken paragraphs or markdown-like clutter (like *, #).\n"
    "✅ Always format like a clean, visually readable chart or guide.\n\n"

    "Now respond like a premium ChatGPT health coach."
        )
    print("[PROMPT CONTEXT] memory_summary:", memory_summary)

    # Load chat history (last 5)
    history = list(chats.find({"user_id": user_id}).sort("_id", -1).limit(5))
    history.reverse()

    context = []
    for h in history:
        context.append({"role": "user", "parts": [{"text": h["question"]}]})
        context.append({"role": "model", "parts": [{"text": h["reply"]}]})
    context.append({"role": "user", "parts": [{"text": user_input}]})

    # Generate Gemini reply
    model = genai.GenerativeModel(
        "gemini-2.5-pro",
        system_instruction=memory_summary
    )

    try:
        response = model.generate_content(contents=context)
        reply = response.text
    except Exception as e:
        reply = f"An error occurred while generating a reply: {str(e)}"

    # Save to chat history
    chats.insert_one({
        "user_id": user_id,
        "question": user_input,
        "reply": reply,
        "file_used": filename if file else None
    })

    return jsonify({"reply": reply})

# Get chat history (20 latest)
@chat_bp.route("/api/chat/history", methods=["GET"])
@login_required
def get_chat_history():
    user_id = str(current_user.get_id())
    history = list(chats.find({"user_id": user_id}).sort("_id", -1).limit(20))
    for chat in history:
        chat["_id"] = str(chat["_id"])
    return jsonify(history)

# Get specific chat
@chat_bp.route("/api/chat/history/<chat_id>", methods=["GET"])
@login_required
def get_chat_by_id(chat_id):
    chat = chats.find_one({"_id": ObjectId(chat_id)})
    if not chat or str(chat["user_id"]) != str(current_user.get_id()):
        return jsonify({"error": "Chat not found"}), 404
    return jsonify({
        "question": chat["question"],
        "reply": chat["reply"]
    })

# Download chat as PDF
@chat_bp.route("/api/chat/pdf/<chat_id>", methods=["GET"])
@login_required
def download_chat_pdf(chat_id):
    chat = chats.find_one({"_id": ObjectId(chat_id)})
    if not chat or str(chat["user_id"]) != str(current_user.get_id()):
        return jsonify({"error": "Chat not found"}), 404

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica", 12)
    textobject = c.beginText(50, height - 50)
    textobject.textLine("Question:")
    textobject.textLines(chat["question"])
    textobject.textLine("")
    textobject.textLine("Response:")
    textobject.textLines(chat["reply"])
    c.drawText(textobject)
    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="chat_response.pdf", mimetype='application/pdf')

# Delete chat
@chat_bp.route("/api/chat/delete/<chat_id>", methods=["DELETE"])
@login_required
def delete_chat(chat_id):
    result = chats.delete_one({"_id": ObjectId(chat_id), "user_id": current_user.get_id()})
    return jsonify({"success": result.deleted_count > 0})

# Chat frontend
@chat_bp.route("/chat")
@login_required
def chat_page():
    return render_template("chat.html", user=current_user)
