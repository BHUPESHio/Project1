from typing import Collection
from flask import Flask, redirect, render_template, request, jsonify,url_for
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

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#Database Collections
def get_users_collection():
    return mongo.db.users

def get_records():
    return mongo.db.records

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
        
        # Validate input
        if not data or not all(k in data for k in ('name', 'email', 'password')):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        # Check if user already exists
        users_collection=get_users_collection()
        existing_user = users_collection.find_one({'email': data['email']})
        if existing_user:
            return jsonify({"success": False, "message": "Email already registered"}), 409
        
        # Hash password and create user
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        user_id = mongo.db.users.insert_one({
            'name': data['name'],
            'email': data['email'],
            'password': hashed_password,
            'created_at': datetime.now(timezone.utc)
        }).inserted_id

        return jsonify({"success":True,"message":"Account created ! "})
        
    except Exception as e:
        print(f"Error during signup: {e}")
        return jsonify({"success": False, "message": "Registration failed"}), 500

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

from datetime import datetime, timedelta

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


        return render_template("dashboard.html",
                               user=current_user,
                               bmi_records=format_records(bmi_records, 'bmi'),
                               bodyfat_records=format_records(bodyfat_records, 'body_fat'),
                               idealweight_records=format_records(idealweight_records, 'ideal_weight_kg'),
                               bmi_stats=compute_stats(bmi_records, 'bmi'),
                               bf_stats=compute_stats(bodyfat_records, 'body_fat'),
                               iw_stats=compute_stats(idealweight_records, 'ideal_weight_kg'),
                               calorie_records = format_records(calorie_records, 'daily_calories'))
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