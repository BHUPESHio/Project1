import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gemini API key from .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model with instructions
model = genai.GenerativeModel(
    "gemini-1.5-flash",
    system_instruction=(
        "You are a helpful fitness and health assistant. "
        "You ONLY respond to questions related to fitness, exercise, diet, nutrition, gym, physical growth, "
        "calories, food content, protein, weight loss, muscle building, health improvement, and related topics. "
        "If something is outside this scope, politely refuse."
    )
)

def generate_reply(prompt, file_data=None):
    try:
        if file_data:
            # Optional: Add logic for image or PDF processing later
            response = model.generate_content([prompt, file_data])
        else:
            response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"An error occurred while processing your request: {str(e)}"
