import os
import bcrypt
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS to allow frontend requests
app.secret_key = '123456abc'
# File Upload Configuration
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# SQLAlchemy Configuration (replace with your credentials)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://Veeresh:Veeresh123@localhost/career"  # Database URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Ensure upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Database Models

# User Table
class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(50), nullable=False)
    lname = db.Column(db.String(50), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)
    recommendations = db.Column(db.Text, nullable=True)

# Login Table
class Login(db.Model):
    __tablename__ = 'Login'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, nullable=False)

class jobs(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    Company_name = db.Column(db.String(255), nullable=False)
    skill_1 = db.Column(db.String(255), nullable=False)
    skill_2 = db.Column(db.String(255), nullable=True)
    skill_3 = db.Column(db.String(255), nullable=True)


class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    skill_1 = db.Column(db.String(255), nullable=False)
    skill_2 = db.Column(db.String(255), nullable=True)
    skill_3 = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)  # Foreign key to User table
    user = db.relationship('User', backref=db.backref('skills', lazy=True))



# Projects Table
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(255), nullable=False)
    project_link = db.Column(db.String(255), nullable=False)
    project_role = db.Column(db.String(255), nullable=False)
    tools = db.Column(db.String(255))
    project_description = db.Column(db.Text)

# Certifications Table
class Certification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    certification_name = db.Column(db.String(255), nullable=False)
    issuing_organization = db.Column(db.String(255), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    certificate_file = db.Column(db.String(255), nullable=False)

class UserSkill(db.Model):
    __tablename__ = 'UserSkill'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
    skill_name = db.Column(db.String(255), nullable=False)


# Initialize the database
with app.app_context():
    db.create_all()  # Create tables if they do not exist

# Career Recommendation Logic
def analyze_skills(user_skills):
    # Fetch all jobs and their required skills
    skills_data = Skill.query.all()

    recommendations = []

    for job in skills_data:
        required_skills = {job.skill_1, job.skill_2, job.skill_3}
        required_skills.discard(None)  # Remove None values

        # Calculate match percentage
        matches = set(user_skills).intersection(required_skills)
        match_percentage = (len(matches) / len(required_skills)) * 100 if required_skills else 0

        recommendations.append({
            "job_name": job.job_name,
            "match_percentage": match_percentage
        })

    # Sort recommendations by match percentage (descending order)
    recommendations.sort(key=lambda x: x['match_percentage'], reverse=True)

    return recommendations

# Routes
@app.route("/")
def home():
    return render_template("first.html")

# User Registration
@app.route("/reg_page")
def register_page():
    return render_template("reg.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    fname = data["fname"]
    lname = data["lname"]
    dob = data["dob"]
    gender = data["gender"]
    phone = data["phone"]
    email = data["email"]
    password = data["password"]

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    if User.query.filter_by(email=email).first() or User.query.filter_by(phone=phone).first():
        return jsonify({"message": "Email or phone already registered"}), 400

    user = User(
        fname=fname,
        lname=lname,
        dob=dob,
        gender=gender,
        phone=phone,
        email=email,
        password=hashed_password,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "user_id": user.id})

# User Login
@app.route("/login_page")
def login_page():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
    email_or_phone = request.form['email_or_number']
    password = request.form['password']

    user = User.query.filter((User.email == email_or_phone) | (User.phone == email_or_phone)).first()

    if user and bcrypt.checkpw(password.encode('utf-8'), user.password):
        session['user_id'] = user.id  # Store user ID in session
        login_attempt = Login(user_id=user.id, success=True)
        db.session.add(login_attempt)
        db.session.commit()
        return redirect(url_for('form'))
    else:
        flash("Invalid credentials.")
        return redirect(url_for('home'))



# Career Recommendation Form and Results
@app.route("/form")
def form():
    return render_template("form.html")

@app.route("/recommend", methods=["POST"])
def recommend():
    # Get user's skills from the form
    user_skills = request.form.getlist('skills[]')

    # Analyze the skills and get recommendations
    recommendations = analyze_skills(user_skills)

    return render_template("results.html", recommendations=recommendations)

# Thank You Page
@app.route("/thank_you")
def thank_you():
    return "Thank you for your submission!"

# Get All Users (Admin Feature)
@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    user_list = [
        {
            "id": user.id,
            "fname": user.fname,
            "lname": user.lname,
            "dob": user.dob.isoformat(),
            "gender": user.gender,
            "phone": user.phone,
            "email": user.email,
        }
        for user in users
    ]
    return jsonify(user_list)

@app.route('/submit-form', methods=['POST'])
def submit_form():
    return redirect(url_for('job_selection'))

# Route for the job selection page
@app.route('/job-selection')
def job_selection():
    return render_template('job_selection.html')



@app.route('/job_page')
def job_page():
    return render_template('job_selection.html')

@app.route('/submit-job', methods=['POST'])
def submit_job():
    selected_job = request.form['job']

    # Use the helper functions to calculate the match percentage and recommended job
    match_percentage = calculate_match(selected_job)
    recommended_job = get_recommended_job()

    return render_template(
        'final.html', 
        preferred_job=selected_job,
        match_percentage=match_percentage,
        recommended_job=recommended_job
    )


def calculate_match(selected_job):
    # Fetch the required skills for the selected job from the jobs table
    job = jobs.query.filter_by(Company_name=selected_job).first()
    if not job:
        return 0  # Return 0% if the job is not found in the database

    # Fetch the user's skills from the skill table based on user_id
    # Assuming the user is already logged in and user_id is available in session
    user_id = session.get('user_id')  # Or pass it as a parameter if necessary
    user_skills_data = Skill.query.filter_by(user_id=user_id).first()

    if not user_skills_data:
        return 0  # Return 0% if no skills are found for the user

    # Collect the skills from the user's entry (skill_1, skill_2, skill_3)
    user_skills = {user_skills_data.skill_1, user_skills_data.skill_2, user_skills_data.skill_3}
    user_skills.discard(None)  # Remove None values, as they are not considered valid skills

    # Create a set of required skills for the selected job
    required_skills = {job.skill_1, job.skill_2, job.skill_3}
    required_skills.discard(None)  # Remove None values

    # Calculate the match percentage
    if not required_skills:
        return 0  # Return 0% if there are no required skills for the job

    matches = user_skills.intersection(required_skills)
    match_percentage = (len(matches) / len(required_skills)) * 100

    return match_percentage



def get_recommended_job():
    # Fetch all jobs and their required skills
    jobs_data = jobs.query.all()

    # Fetch the user's skills from the Skill table (based on user_id in session)
    user_id = session.get('user_id')  # Assuming user_id is stored in the session
    user_skills_data = Skill.query.filter_by(user_id=user_id).first()  # Get the first skill record for the user

    if not user_skills_data:
        return "No skills found for the user."

    # Collect the user's skills from the skill_1, skill_2, skill_3 columns
    user_skills = {user_skills_data.skill_1, user_skills_data.skill_2, user_skills_data.skill_3}
    user_skills.discard(None)  # Remove None values, as they are not valid skills

    recommendations = []

    for job in jobs_data:
        # Create a set of required skills for the selected job
        required_skills = {job.skill_1, job.skill_2, job.skill_3}
        required_skills.discard(None)  # Remove None values from required skills

        if not required_skills:
            continue  # Skip jobs with no required skills

        # Calculate match percentage
        matches = user_skills.intersection(required_skills)
        match_percentage = (len(matches) / len(required_skills)) * 100 if required_skills else 0

        recommendations.append({
            "Company_name": job.Company_name,
            "match_percentage": match_percentage
        })

    # Sort recommendations by match percentage (descending order)
    recommendations.sort(key=lambda x: x['match_percentage'], reverse=True)

    # Return the job with the highest match percentage
    return recommendations[0]['Company_name'] if recommendations else "No recommendations available"

@app.route('/submit_skills', methods=['POST'])
def submit_skills():
    if 'user_id' not in session:  # Check if the user is logged in
        flash("You must be logged in to submit skills.")
        return redirect(url_for('login_page'))

    user_id = session['user_id']  # Get the logged-in user's ID
    skills = request.form.getlist('skills[]')  # Get the list of skills from the form

    print("Skills received:", skills)  # Debug print to check if the skills are being passed

    # Limit to 3 skills for skill_1, skill_2, and skill_3
    skills = skills[:3]

    # Ensure there are no empty skills
    while len(skills) < 3:
        skills.append(None)  # Fill missing skill slots with None

    # Store the skills in the Skill table
    new_skill = Skill(
        skill_1=skills[0],
        skill_2=skills[1] if len(skills) > 1 else None,
        skill_3=skills[2] if len(skills) > 2 else None,
        user_id=user_id
    )

    db.session.add(new_skill)
    db.session.commit()  # Commit the transaction to save the skills
    flash("Skills have been submitted successfully!")
    return redirect(url_for('form'))  # Redirect to the form page after successful submission

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)