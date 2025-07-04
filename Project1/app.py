from typing import Collection
from flask import Flask, redirect, render_template, request, jsonify,url_for
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
from flask_cors import CORS
from datetime import datetime, timezone
from flask_mail import Mail,Message
from itsdangerous import Serializer, URLSafeTimedSerializer

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configuration
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']=587
app.config['MAIL_USE_TLS']=True
app.config['MAIL_USERNAME']='examplep489@gmail.com'
app.config['MAIL_PASSWORD']='bull buhk ntmh djrw'
app.config['MAIL_DEFAULT_USERNAME']='examplep489@gmail.com'
app.config['SECRET_KEY'] = 'bhup14'
MONGO_URI="mongodb+srv://Admin:bait1783@fitrackdb.o4yvman.mongodb.net/?retryWrites=true&w=majority&appName=fitrackdb"
mongo=MongoClient(MONGO_URI)
db=mongo["myDatabase"]
users=db["users"]
mail=Mail(app)

#Email Token Serializer
serializer=URLSafeTimedSerializer(app.config['SECRET_KEY'])
def send_verification_email(email):
    token=serializer.dumps(email,salt='email-confirm')
    confirm_url=url_for('verify_email',token=token,_external=True)
    html=f'''
    <p>Hi! Please verify your email address by clicking the link below : </p>
    <a href="{confirm_url}">Verify your email </a>
    '''
    msg=Message('Email Verification',recipients=[email],html=html)
    mail.send(msg)


# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#Database Collections
def get_users_collection():
    return mongo.db.users

def get_bmi_records_collection():
    return mongo.db.bmi_records


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
                bmi_records_collection=get_bmi_records_collection()
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
    
@app.route('/verify/<token>')
def verify_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except:
        return render_template("verified.html", success=False, message="The verification link is invalid or has expired.")

    users_collection = get_users_collection()
    user = users_collection.find_one({'email': email})

    if user:
        if not user.get('is_verified', False):
            users_collection.update_one({'email': email}, {'$set': {'is_verified': True}})
            return render_template("verified.html", success=True, message="Your email has been successfully verified. You will be redirected shortly.")
        else:
            return render_template("verified.html", success=True, message="Your email was already verified. Redirecting you to the homepage.")
    else:
        return render_template("verified.html", success=False, message="No user found with this email.")

@app.route('/verified')
def verified_page():
    return render_template('verified.html')


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

        send_verification_email(data['email'])

        return jsonify({"success":True,"message":"Account created ! Check your email to verify."})
        
    except Exception as e:
        print(f"Error during signup: {e}")
        return jsonify({"success": False, "message": "Registration failed"}), 500


@app.route('/resend_verification', methods=['POST'])
def resend_verification():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400

    users_collection = get_users_collection()
    user = users_collection.find_one({'email': email})

    if user:
        if user.get('is_verified', False):
            return jsonify({'success': False, 'message': 'This email is already verified.'})
        send_verification_email(email)
        return jsonify({'success': True, 'message': 'Verification email resent!'})
    else:
        return jsonify({'success': False, 'message': 'No account found with this email.'}), 404




@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ('email', 'password')):
            return jsonify({"success": False, "message": "Missing email or password"}), 400
        
        users_collection=get_users_collection()
        user = users_collection.find_one({'email': data['email']})

        if not user.get('is_verified',False):
            return jsonify({"success": False,"message":"Please verify your email before logging in.  "}),403

        
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

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user's BMI records
        records = list(mongo.db.bmi_records.find({
            'user_id': ObjectId(current_user.id)
        }).sort('timestamp', -1))
        
        # Format records for display
        for record in records:
            record['_id'] = str(record['_id'])
            record['timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M')
            record['user_id'] = str(record['user_id'])
        
        return render_template("dashboard.html", records=records, user=current_user)
        
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template("dashboard.html", records=[], user=current_user, error="Error loading records")

@app.route('/api/user_stats')
@login_required
def user_stats():
    try:
        # Get user's BMI records for statistics
        bmi_records_collection=get_bmi_records_collection()
        records = list(bmi_records_collection.find({
            'user_id': ObjectId(current_user.id)
        }).sort('timestamp', -1))
        
        if not records:
            return jsonify({"stats": None, "message": "No records found"})
        
        # Calculate basic statistics
        bmis = [record['bmi'] for record in records]
        latest_record = records[0]
        
        stats = {
            "total_records": len(records),
            "latest_bmi": latest_record['bmi'],
            "latest_category": latest_record['category'],
            "average_bmi": round(sum(bmis) / len(bmis), 2),
            "min_bmi": min(bmis),
            "max_bmi": max(bmis),
            "latest_date": latest_record['timestamp'].strftime('%Y-%m-%d')
        }
        
        return jsonify({"stats": stats})
        
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return jsonify({"error": "Failed to get statistics"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)