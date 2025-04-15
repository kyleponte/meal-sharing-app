from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')  # For session management
db = SQLAlchemy(app)

# Add debug logging
print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

# --------- Data Classes ---------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    meals = db.relationship('Meal', backref='host', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    ingredients = db.Column(db.Text)
    course_type = db.Column(db.String(50))
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'))

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location = db.Column(db.String(100))
    time = db.Column(db.DateTime)
    max_guests = db.Column(db.Integer)
    fee = db.Column(db.Float)
    active_until = db.Column(db.DateTime)
    dishes = db.relationship('Dish', backref='meal', cascade="all, delete-orphan")

    def is_active(self):
        return datetime.now() <= self.active_until

# --------- Routes ---------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        print(f"Attempting to create user: {username}")
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('signup'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('signup'))
            
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            print(f"Successfully created user: {username}")
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            db.session.rollback()
            flash('Error creating account', 'error')
            return redirect(url_for('signup'))
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# --------- Helper Functions ---------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/post-meal', methods=['GET', 'POST'])
@login_required
def post_meal():
    if request.method == 'POST':
        location = request.form['location']
        date_str = request.form['meal_date']
        time_str = request.form['meal_time']
        time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        max_guests = int(request.form['max_guests'])
        fee = float(request.form['fee'])
        active_hours = int(request.form['active_hours'])

        meal = Meal(
            host_id=session['user_id'],
            location=location,
            time=time,
            max_guests=max_guests,
            fee=fee,
            active_until=datetime.now() + timedelta(hours=active_hours)
        )

        for i in range(1, 4):
            dish_name = request.form[f'dish{i}_name']
            ingredients = request.form[f'dish{i}_ingredients']
            course = ['appetizer', 'main', 'dessert'][i - 1]
            dish = Dish(name=dish_name, ingredients=ingredients, course_type=course)
            meal.dishes.append(dish)

        db.session.add(meal)
        db.session.commit()

        return redirect(url_for('home'))
    return render_template('post_meal.html')

@app.route('/browse-meals')
def browse_meals():
    meals = Meal.query.all()
    return render_template('browse_meals.html', meals=meals)

@app.route('/delete-meal/<int:meal_id>', methods=['POST'])
@login_required
def delete_meal(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    # Check if the current user is the host of the meal
    if meal.host_id != session['user_id']:
        flash('You can only delete your own meals', 'error')
        return redirect(url_for('browse_meals'))
    
    db.session.delete(meal)
    db.session.commit()
    flash('Meal deleted successfully', 'success')
    return redirect(url_for('browse_meals'))

with app.app_context():
    # Only create tables if they don't exist
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

