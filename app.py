from flask import Flask, render_template, request, jsonify, session
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
from flask_cors import CORS
from datetime import datetime,timezone
from database import ConnectDB

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
timestamp=datetime.now(timezone.utc)

# Load environment variables
load_dotenv()

app = Flask(__name__)
mongo=ConnectDB(app)
app.config["SECRET_KEY"] = "b#up35#"





# Initialize extensions

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)



# JSON logic for child BMI classification
child_bmi_json = {
    "labels": ["< 5th", "5th–85th", "85th–95th", "> 95th"],
    "values": [14, 18, 20, 23],
    "categories": ["Underweight", "Healthy", "At Risk", "Overweight"]
}

# Adult BMI categories
adult_bmi_json = {
    "values": [18.4, 24.9, 29.9, 40],
    "categories": ["Underweight", "Normal", "Overweight", "Obese"]
}

def get_child_category(bmi):
    for i, val in enumerate(child_bmi_json["values"]):
        if bmi <= val:
            return {
                "percentile": child_bmi_json["labels"][i],
                "category": child_bmi_json["categories"][i]
            }
    return {
        "percentile": "> 95th",
        "category": "Overweight"
    }

def get_adult_category(bmi):
    for i, val in enumerate(adult_bmi_json["values"]):
        if bmi <= val:
            return adult_bmi_json["categories"][i]
    return "Obese"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/calculate_bmi', methods=['POST'])
def calculate_bmi():
    data = request.json
    age = int(data.get('age'))
    weight = float(data.get('weight'))
    height = float(data.get('height'))
    units = data.get('units')

    if units == 'metric':
        bmi = weight / ((height / 100) ** 2)
    else:
        bmi = (703 * weight) / (height ** 2)

    bmi = round(bmi, 2)

    if age < 19:
        child_result = get_child_category(bmi)
        result={
            "bmi": bmi,
            "category": child_result["category"],
            "percentile": child_result["percentile"],
            "type": "child"
        }
    else:
        result={
            "bmi": bmi,
            "category": get_adult_category(bmi),
            "type": "adult"
        }

        # Save to MongoDB if user is logged in
    if current_user.is_authenticated:
        mongo.db.bmi_records.insert_one({
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
    
    return jsonify(result)


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.email = user_doc['email']

@login_manager.user_loader
def load_user(user_id):
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return User(user) if user else None

# Routes


@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    existing_user = mongo.db.users.find_one({'email': data['email']})
    if existing_user:
        return jsonify({"success": False, "message": "Email already registered"}), 409

    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user_id = mongo.db.users.insert_one({
        'name': data['name'],
        'email': data['email'],
        'password': hashed_pw
    }).inserted_id

    user = mongo.db.users.find_one({'_id': user_id})
    login_user(User(user))
    return jsonify({"success": True})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = mongo.db.users.find_one({'email': data['email']})
    if user and bcrypt.check_password_hash(user['password'], data['password']):
        login_user(User(user))
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})


@app.route('/dashboard')
@login_required
def dashboard():
    records = list(mongo.db.bmi_records.find({
        'user_id': ObjectId(current_user.id)
    }).sort('timestamp', -1))

    # Convert ObjectId and datetime for rendering
    for record in records:
        record['_id'] = str(record['_id'])
        record['timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M')
    return render_template("dashboard.html", records=records, user=current_user)


if __name__ == '__main__':
    app.run(debug=True)