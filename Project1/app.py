from typing import Collection
from flask import Flask, redirect, render_template, request, jsonify,url_for,Blueprint
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from bson import ObjectId
from dotenv import load_dotenv
import os
from flask_cors import CORS
from datetime import datetime, timezone
from flask_mail import Mail,Message
from itsdangerous import Serializer, URLSafeTimedSerializer
import math
import json
from datetime import datetime, timedelta
import google.generativeai as genai
from werkzeug.utils import secure_filename
from utils.chat import chat_bp
import re
import random




# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configuration

app.config['SECRET_KEY'] = 'bhup14'
MONGO_URI="mongodb+srv://Admin:bait1783@fitrackdb.o4yvman.mongodb.net/?retryWrites=true&w=majority&appName=fitrackdb"
mongo=MongoClient(MONGO_URI)
db=mongo["myDatabase"]
users=db["users"]
GEMINI_API_KEY = "AIzaSyCojl5hk_fItuAEjPU26E0sJiZ8uAoM2Vs"
GEMINI_API_URL="https://gemini.googleapis.com/v1/models/gemini-2.5-pro:generateContent"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-pro")
app.register_blueprint(chat_bp)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'examplep489@gmail.com'
app.config['MAIL_PASSWORD'] = 'rmyr hwug keok syfv'
mail = Mail(app)

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])



# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Configure Gemini
genai.configure(api_key='AIzaSyCojl5hk_fItuAEjPU26E0sJiZ8uAoM2Vs')

#Database Collections
def get_users_collection():
    return mongo.db.users

def get_records():
    return mongo.db.records

#Chatbot

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


# BMI Classification Data
CHILD_BMI_DATA = {
    "labels": ["< 5th", "5th–85th", "85th–95th", "> 95th"],
    "values": [14, 18, 20, 23],
    "categories": ["Underweight", "Healthy", "At Risk", "Overweight"]
}

ADULT_BMI_DATA = {
    "values": [18.4, 24.9, 29.9, 40],
    "categories": ["Underweight", "Normal", "Overweight", "Obese"]
}

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.email = user_doc['email']
        self.name = user_doc.get('name', '')

@login_manager.user_loader
def load_user(user_id):
    try:
        users_collection=get_users_collection()
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        return User(user) if user else None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

# BMI Classification Functions
def get_child_bmi_category(bmi):
    """Get BMI category for children (under 19)"""
    for i, threshold in enumerate(CHILD_BMI_DATA["values"]):
        if bmi <= threshold:
            return {
                "percentile": CHILD_BMI_DATA["labels"][i],
                "category": CHILD_BMI_DATA["categories"][i]
            }
    return {
        "percentile": "> 95th",
        "category": "Overweight"
    }

def get_adult_bmi_category(bmi):
    """Get BMI category for adults (19+)"""
    for i, threshold in enumerate(ADULT_BMI_DATA["values"]):
        if bmi <= threshold:
            return ADULT_BMI_DATA["categories"][i]
    return "Obese"

def calculate_bmi_value(weight, height, units):
    """Calculate BMI based on weight, height, and units"""
    if units == 'metric':
        # weight in kg, height in cm
        return weight / ((height / 100) ** 2)
    else:
        # weight in lbs, height in inches
        return (703 * weight) / (height ** 2)

# Routes


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/calculate_bmi', methods=['POST'])
def calculate_bmi():
    try:
        data = request.get_json()
        
        # Validate input data
        if not data or not all(k in data for k in ('age', 'weight', 'height', 'units')):
            return jsonify({"error": "Missing required fields"}), 400
        
        age = int(data['age'])
        weight = float(data['weight'])
        height = float(data['height'])
        units = data['units']
        
        # Validate ranges
        if age < 1 or age > 120:
            return jsonify({"error": "Age must be between 1 and 120"}), 400
        if weight <= 0 or height <= 0:
            return jsonify({"error": "Weight and height must be positive"}), 400
        
        # Calculate BMI
        bmi = calculate_bmi_value(weight, height, units)
        bmi = round(bmi, 2)
        
        # Determine category
        if age < 19:
            child_result = get_child_bmi_category(bmi)
            result = {
                "bmi": bmi,
                "category": child_result["category"],
                "percentile": child_result["percentile"],
                "type": "child"
            }
        else:
            result = {
                "bmi": bmi,
                "category": get_adult_bmi_category(bmi),
                "type": "adult"
            }
        
        # Save to database if user is logged in
        if current_user.is_authenticated:
            try:
                bmi_records_collection=get_records()
                bmi_records_collection.insert_one({
                    'user_id': ObjectId(current_user.id),
                    'age': age,
                    'weight': weight,
                    'height': height,
                    'bmi': bmi,
                    'type': result['type'],
                    'category': result['category'],
                    'units': units,
                    'timestamp': datetime.now(timezone.utc)
                })
            except Exception as e:
                print(f"Error saving BMI record: {e}")
                # Don't fail the request if saving fails
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": "Invalid input data"}), 400
    except Exception as e:
        print(f"Error calculating BMI: {e}")
        return jsonify({"error": "Internal server error"}), 500
    



@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        if not all([name, email, password]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        users_collection = get_users_collection()
        if users_collection.find_one({"email": email}):
            return jsonify({"success": False, "message": "Email already registered"}), 409

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # 🔐 Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

        # ⏳ Store user with OTP (and is_verified = False)
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "otp": otp,
            "otp_expiry": expiry,
            "is_verified": False,
            "created_at": datetime.now(timezone.utc)
        })

        # 📩 Send Email
        msg = Message("Your OTP for FitTrack Signup",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[email])
        msg.body = f"Hello {name},\n\nYour OTP is: {otp}\nThis OTP will expire in 10 minutes."
        mail.send(msg)

        return jsonify({"success": True, "message": "OTP sent to your email. Please verify."}), 200

    except Exception as e:
        print("Signup Error:", str(e))
        return jsonify({"success": False, "message": "Signup failed."}), 500

@app.route('/bodyfat')
def bodyfat():
    return render_template('bodyfat.html')

@app.route("/api/calculate_bodyfat", methods=["POST"])
@login_required
def calculate_bodyfat():
    try:
        data = request.get_json()
        print("Incoming Body Fat Data:", data)  

        gender = data.get("gender")
        height = float(data.get("height"))
        neck = float(data.get("neck"))
        waist = float(data.get("waist"))
        hip = float(data.get("hip", 0))

        if gender == "male":
            if waist <= neck:
                raise ValueError("Waist must be greater than neck")
            body_fat = 86.010 * math.log10(waist - neck) - 70.041 * math.log10(height) + 36.76
        else:
            if waist + hip <= neck:
                raise ValueError("Waist + Hip must be greater than neck")
            body_fat = 163.205 * math.log10(waist + hip - neck) - 97.684 * math.log10(height) - 78.387


        body_fat = round(body_fat, 2)
        category = categorize_bodyfat(gender, body_fat)

        
        print(f"Calculated BF%: {body_fat}, Category: {category}")

        get_records().insert_one({
            "user_id": ObjectId(current_user.id),
            "type": "body_fat",
            "gender": gender,
            "height": height,
            "neck": neck,
            "waist": waist,
            "hip": hip,
            "body_fat": body_fat,
            "category": category,
            "timestamp": datetime.now(timezone.utc)
        })

        return jsonify({"success": True, "body_fat": body_fat, "category": category})

    except Exception as e:
        print("Error in /api/calculate_bodyfat:", str(e))  
        return jsonify({"success": False, "error": str(e)})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        otp_entered = data.get('otp')

        if not all([email, otp_entered]):
            return jsonify({"success": False, "message": "Email and OTP are required"}), 400

        user = get_users_collection().find_one({"email": email})
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        if user.get("is_verified"):
            return jsonify({"success": True, "message": "Account already verified."}), 200

        if datetime.now(timezone.utc) > user.get("otp_expiry"):
            return jsonify({"success": False, "message": "OTP expired"}), 400

        if user.get("otp") != otp_entered:
            return jsonify({"success": False, "message": "Invalid OTP"}), 400

        # ✅ Mark user as verified
        get_users_collection().update_one({"email": email}, {
            "$set": {"is_verified": True},
            "$unset": {"otp": "", "otp_expiry": ""}
        })

        return jsonify({"success": True, "message": "Account verified successfully!"})

    except Exception as e:
        print("OTP Verification Error:", str(e))
        return jsonify({"success": False, "message": "Verification failed"}), 500



def categorize_bodyfat(gender, value):
    zones = {
        "male": [(5, "Essential"), (13, "Athletes"), (17, "Fitness"), (24, "Average"), (40, "Obese")],
        "female": [(13, "Essential"), (20, "Athletes"), (24, "Fitness"), (31, "Average"), (45, "Obese")]
    }
    for limit, label in zones[gender]:
        if value <= limit:
            return label
    return "Extremely High"

@app.route('/idealweight')
@login_required
def idealweight():
    return render_template('idealweight.html')

@app.route('/api/calculate_idealweight', methods=['POST'])
@login_required
def calculate_idealweight():
    try:
        data = request.get_json()

        gender = data.get('gender')
        age = int(data.get('age'))
        height = float(data.get('height'))
        units = data.get('units', 'metric')

        if gender not in ['male', 'female']:
            return jsonify({"success": False, "error": "Invalid gender"}), 400

        if age < 1 or height <= 0:
            return jsonify({"success": False, "error": "Invalid age or height"}), 400

        # Convert height to cm if in imperial
        if units == 'imperial':
            height *= 2.54  # inches to cm

        # Ideal Weight Calculation using Devine Formula:
        # Base = 50kg (male) or 45.5kg (female) + 0.9kg per cm over 152.4
        base_height = 152.4
        if gender == 'male':
            base_weight = 50 + 0.9 * max(0, height - base_height)
        else:
            base_weight = 45.5 + 0.9 * max(0, height - base_height)

        ideal_weight = round(base_weight, 2)

        # Save to DB
        mongo.db.records.insert_one({
            'user_id': ObjectId(current_user.id),
            'type': 'ideal_weight',
            'gender': gender,
            'age': age,
            'height_cm': height,
            'ideal_weight_kg': ideal_weight,
            'units': units,
            'timestamp': datetime.now(timezone.utc)
        })

        return jsonify({
            "success": True,
            "ideal_weight": ideal_weight,
            "units": "kg" if units == 'metric' else "converted from imperial",
        })

    except Exception as e:
        print("Ideal weight error:", str(e))
        return jsonify({"success": False, "error": "Failed to calculate ideal weight"}), 500


@app.route('/bmi-predict')
@login_required
def bmi_predict_page():
    return render_template('bmi_predict.html')


@app.route('/api/predict_bmi', methods=['POST'])
@login_required
def predict_bmi():
    try:
        data = request.get_json()
        age = int(data['age'])
        current_bmi = float(data['bmi'])

        # Example logic: Slight monthly increase
        predicted_bmi = round(current_bmi + (age * 0.05), 2)

        # Suggestion logic (you can enhance this)
        if predicted_bmi < 18.5:
            suggestion = "Increase calorie intake and build muscle."
        elif predicted_bmi < 24.9:
            suggestion = "Maintain regular exercise and healthy eating."
        elif predicted_bmi < 29.9:
            suggestion = "Incorporate more cardio and reduce sugar intake."
        else:
            suggestion = "Consult a health professional for a guided weight loss plan."

        # Simulate 6-month timeline
        months = ["July", "August", "September", "October", "November", "December"]
        prediction_timeline = [
            {"date": month, "bmi": round(current_bmi + (i * 0.1), 2)}
            for i, month in enumerate(months)
        ]

        # Save to DB
        mongo.db.records.insert_one({
            'user_id': ObjectId(current_user.id),
            'type': 'bmi_prediction',
            'age': age,
            'current_bmi': current_bmi,
            'predicted_bmi': predicted_bmi,
            'timestamp': datetime.now(timezone.utc)
        })

        return jsonify({
            "success": True,
            "current_bmi": current_bmi,
            "predicted_bmi": predicted_bmi,
            "suggestions": suggestion,
            "prediction_timeline": prediction_timeline
        })

    except Exception as e:
        print("BMI Prediction Error:", str(e))
        return jsonify({"success": False, "error": "Failed to predict BMI"}), 500




@app.route('/calorie')
@login_required
def calorie():
    return render_template('calorie.html')

@app.route('/api/calculate_calories', methods=['POST'])
@login_required
def calculate_calories():
    try:
        data = request.get_json()

        age = int(data.get('age'))
        gender = data.get('gender')
        weight = float(data.get('weight'))
        height = float(data.get('height'))
        activity = data.get('activity_level')  # sedentary, moderate, active
        units = data.get('units', 'metric')

        if units == 'imperial':
            weight *= 0.453592
            height *= 2.54

        if gender == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        activity_multiplier = {
            "sedentary": 1.2,
            "moderate": 1.55,
            "active": 1.9
        }.get(activity, 1.2)

        daily_calories = round(bmr * activity_multiplier)

        mongo.db.records.insert_one({
            'user_id': ObjectId(current_user.id),
            'type': 'calorie',
            'age': age,
            'gender': gender,
            'weight': weight,
            'height': height,
            'activity': activity,
            'daily_calories': daily_calories,
            'timestamp': datetime.now(timezone.utc)
        })

        return jsonify({
            "success": True,
            "daily_calories": daily_calories
        })

    except Exception as e:
        print("Error calculating calories:", str(e))
        return jsonify({"success": False, "error": "Failed to calculate calories"}), 500




@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ('email', 'password')):
            return jsonify({"success": False, "message": "Missing email or password"}), 400
        
        users_collection=get_users_collection()
        user = users_collection.find_one({'email': data['email']})
        

        if not user.get("is_verified"):
            return jsonify({"success": False, "error": "Please verify your email first."})


        
        if user and bcrypt.check_password_hash(user['password'], data['password']):
            login_user(User(user))
            return jsonify({"success": True, "message": "Login successful"})
        
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
        
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({"success": False, "message": "Login failed"}), 500



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/resend_verification', methods=['POST'])
def resend_verification():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"success": False, "error": "Email is required."}), 400

    user = mongo.db.users.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    if user.get("is_verified"):
        return jsonify({"success": False, "message": "Account already verified."}), 200

    # Generate token
    token = s.dumps(data['email'], salt='email-confirm')
    link = url_for('verify_email', token=token, _external=True)

# Send verification email
    msg = Message("Email Verification - FitTrack",
              sender="examplep489@gmail.com",
              recipients=[data['email']])
    msg.body = f"Click the link to verify your account: {link}"
    mail.send(msg)

    return jsonify({"success": True, "message": "Verification email sent."}), 200



@app.route('/dashboard')
@login_required
def dashboard():
    try:
        def format_records(records, key):
            for r in records:
                r['_id'] = str(r['_id'])
                r['user_id'] = str(r['user_id'])
                if isinstance(r['timestamp'], datetime):
                    r['timestamp'] = r['timestamp'].strftime('%Y-%m-%d')
                elif isinstance(r['timestamp'], str):
                    pass
                else:
                    r['timestamp'] = str(r['timestamp'])
                r[key] = float(r[key])
            return records

        def compute_stats(records, key):
            if not records:
                return None
            values = [r[key] for r in records]
            return {
                'latest': values[-1],
                'average': round(sum(values) / len(values), 2),
                'min': min(values),
                'max': max(values),
                'total': len(values),
                'latest_date': records[-1]['timestamp']
            }

        user_id = ObjectId(current_user.id)
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # ✅ BMI should come from db.records, not db.bmi_records
        bmi_records = list(mongo.db.records.find({
            'user_id': user_id,
            'type': 'adult',  # or 'child' depending on your BMI logic
            'timestamp': {'$gte': week_ago}
        }).sort('timestamp', 1))

        bodyfat_records = list(mongo.db.records.find({
            'user_id': user_id,
            'type': 'body_fat',
            'timestamp': {'$gte': week_ago}
        }).sort('timestamp', 1))

        idealweight_records = list(mongo.db.records.find({
            'user_id': user_id,
            'type': 'ideal_weight',
            'timestamp': {'$gte': week_ago}
        }).sort('timestamp', 1))

        calorie_records = list(mongo.db.records.find({
            'user_id': user_id,
            'type': 'calorie',
            'timestamp': {'$gte': week_ago}
        }).sort('timestamp', 1))
        prediction_records = list(mongo.db.records.find({
            'user_id': user_id,
            'type': 'bmi_prediction',
            'timestamp': {'$gte': week_ago}
        }).sort('timestamp', 1))




        return render_template("dashboard.html",
                               user=current_user,
                               bmi_records=format_records(bmi_records, 'bmi'),
                               bodyfat_records=format_records(bodyfat_records, 'body_fat'),
                               idealweight_records=format_records(idealweight_records, 'ideal_weight_kg'),
                               bmi_stats=compute_stats(bmi_records, 'bmi'),
                               bf_stats=compute_stats(bodyfat_records, 'body_fat'),
                               iw_stats=compute_stats(idealweight_records, 'ideal_weight_kg'),
                               calorie_stats = compute_stats(calorie_records, 'daily_calories'),
                               calorie_records = format_records(calorie_records, 'daily_calories'),
                                prediction_records=format_records(prediction_records, 'predicted_bmi'))

    except Exception as e:
        print("Dashboard error:", e)
        return render_template("dashboard.html",
                               user=current_user,
                               bmi_records=[], bodyfat_records=[], idealweight_records=[],
                               bmi_stats=None, bf_stats=None, iw_stats=None,
                               error="Dashboard loading failed.")



# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)