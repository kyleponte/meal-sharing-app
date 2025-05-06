from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
from sqlalchemy import or_

load_dotenv()

app = Flask(__name__)
# Fix for Supabase connection string format
database_url = os.getenv('DATABASE_URL')
print(f"Database URL being used: {database_url}")  # Debug print

if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    print(f"Modified database URL: {database_url}")  # Debug print

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
db = SQLAlchemy(app)

# --------- Data Classes ---------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    meals = db.relationship('Meal', backref='host', lazy=True)
    bio = db.Column(db.Text)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_host_rating(self):
        host_ratings = [r.rating for r in self.ratings_received if r.rating_type == 'host']
        return sum(host_ratings) / len(host_ratings) if host_ratings else None
    
    def get_guest_rating(self):
        guest_ratings = [r.rating for r in self.ratings_received if r.rating_type == 'guest']
        return sum(guest_ratings) / len(guest_ratings) if guest_ratings else None
    
    def has_hosted_meals(self):
        return bool(self.meals)
    
    def has_attended_meals(self):
        return bool([rsvp for rsvp in self.rsvps if rsvp.status == 'confirmed'])
    
    def can_rate_host(self, meal):
        # Check if user was a confirmed guest and hasn't rated the host yet
        rsvp = RSVP.query.filter_by(meal_id=meal.id, guest_id=self.id, status='confirmed').first()
        if not rsvp:
            return False
        existing_rating = Rating.query.filter_by(
            rater_id=self.id,
            rated_user_id=meal.host_id,
            meal_id=meal.id,
            rating_type='host'
        ).first()
        return not existing_rating
    
    def can_rate_guest(self, guest, meal):
        # Check if user was the host and hasn't rated this guest yet
        if meal.host_id != self.id:
            return False
        rsvp = RSVP.query.filter_by(meal_id=meal.id, guest_id=guest.id, status='confirmed').first()
        if not rsvp:
            return False
        existing_rating = Rating.query.filter_by(
            rater_id=self.id,
            rated_user_id=guest.id,
            meal_id=meal.id,
            rating_type='guest'
        ).first()
        return not existing_rating

class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    ingredients = db.Column(db.Text)
    course_type = db.Column(db.String(50))
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'))

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    time = db.Column(db.DateTime)
    max_guests = db.Column(db.Integer)
    fee = db.Column(db.Float)
    active_until = db.Column(db.DateTime)
    description = db.Column(db.Text, nullable=True)
    dishes = db.relationship('Dish', backref='meal', cascade="all, delete-orphan")
    guests = db.relationship('RSVP', backref='meal', cascade="all, delete-orphan")

    def is_active(self):
        return datetime.now() <= self.active_until
    
    def get_guest_count(self):
        return len([rsvp for rsvp in self.guests if rsvp.status == 'confirmed'])
    
    def can_accept_more_guests(self):
        return self.get_guest_count() < self.max_guests

class RSVP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=False)
    guest_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, rejected
    created_at = db.Column(db.DateTime, default=datetime.now)
    guest = db.relationship('User', backref='rsvps')

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Who gave the rating
    rater_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rater = db.relationship('User', foreign_keys=[rater_id], backref='ratings_given')
    
    # Who received the rating
    rated_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rated_user = db.relationship('User', foreign_keys=[rated_user_id], backref='ratings_received')
    
    # The meal this rating is for
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=False)
    meal = db.relationship('Meal', backref='ratings')
    
    # Type of rating (host or guest)
    rating_type = db.Column(db.String(10))  # 'host' or 'guest'

# --------- Routes ---------
@app.route('/')
def home():
    return redirect(url_for('browse_meals'))

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
        name = request.form['name']
        location = request.form['location']
        date_str = request.form['meal_date']
        time_str = request.form['meal_time']
        time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        max_guests = int(request.form['max_guests'])
        fee = float(request.form['fee'])
        active_until = datetime.strptime(request.form['active_until'], "%Y-%m-%dT%H:%M")
        description = request.form.get('description', '').strip()

        meal = Meal(
            host_id=session['user_id'],
            name=name,
            location=location,
            time=time,
            max_guests=max_guests,
            fee=fee,
            active_until=active_until,
            description=description
        )

        # Handle multiple dishes for each course type
        course_types = ['appetizer', 'main', 'dessert']
        for course in course_types:
            dish_names = request.form.getlist(f'{course}_name[]')
            dish_ingredients = request.form.getlist(f'{course}_ingredients[]')
            
            for name, ingredients in zip(dish_names, dish_ingredients):
                if name and ingredients:  # Only add if both fields are filled
                    dish = Dish(
                        name=name,
                        ingredients=ingredients,
                        course_type=course
                    )
                    meal.dishes.append(dish)

        db.session.add(meal)
        db.session.commit()

        return redirect(url_for('home'))
    return render_template('post_meal.html')

@app.route('/browse-meals')
def browse_meals():
    search_query = request.args.get('search', '').strip()
    meals = Meal.query

    if search_query:
        # Search in meal name, description, location, and host's username
        meals = meals.join(User, Meal.host_id == User.id).filter(
            db.or_(
                Meal.name.ilike(f'%{search_query}%'),
                Meal.description.ilike(f'%{search_query}%'),
                Meal.location.ilike(f'%{search_query}%'),
                User.username.ilike(f'%{search_query}%')
            )
        )
    
    meals = meals.all()
    user_id = session.get('user_id')

    def meal_sort_key(meal):
        # Active meals come before expired, then by active_until descending
        return (not meal.is_active(), -meal.active_until.timestamp())

    if user_id:
        # Separate meals hosted by the user and others
        hosted_meals = [meal for meal in meals if meal.host_id == user_id]
        other_meals = [meal for meal in meals if meal.host_id != user_id]
        # Sort both lists: active first, then by active_until descending
        hosted_meals.sort(key=meal_sort_key)
        other_meals.sort(key=meal_sort_key)
        # Combine: hosted meals first
        sorted_meals = hosted_meals + other_meals
    else:
        # No user logged in, just sort all meals
        sorted_meals = sorted(meals, key=meal_sort_key)

    return render_template('browse_meals.html', meals=sorted_meals, search_query=search_query)

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

@app.route('/meal/<int:meal_id>')
def meal_details(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    is_host = 'user_id' in session and meal.host_id == session['user_id']
    
    # Get current user if logged in
    current_user = None
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
    
    # Get RSVP status for current user if logged in
    current_rsvp = None
    if 'user_id' in session:
        current_rsvp = RSVP.query.filter_by(
            meal_id=meal_id,
            guest_id=session['user_id']
        ).first()
    
    # Get list of confirmed guests
    confirmed_guests = [rsvp.guest for rsvp in meal.guests if rsvp.status == 'confirmed']
    
    return render_template('meal_details.html', 
                         meal=meal, 
                         is_host=is_host,
                         current_rsvp=current_rsvp,
                         confirmed_guests=confirmed_guests,
                         user=current_user)

@app.route('/edit-meal/<int:meal_id>', methods=['GET', 'POST'])
@login_required
def edit_meal(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    
    # Check if the current user is the host of the meal
    if meal.host_id != session['user_id']:
        flash('You can only edit your own meals', 'error')
        return redirect(url_for('browse_meals'))
    
    if request.method == 'POST':
        # Update basic meal information
        meal.name = request.form['name']
        meal.location = request.form['location']
        date_str = request.form['meal_date']
        time_str = request.form['meal_time']
        meal.time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        meal.max_guests = int(request.form['max_guests'])
        meal.fee = float(request.form['fee'])
        meal.active_until = datetime.strptime(request.form['active_until'], "%Y-%m-%dT%H:%M")
        meal.description = request.form.get('description', '').strip()

        # Remove all existing dishes
        for dish in meal.dishes:
            db.session.delete(dish)
        
        # Add updated dishes
        course_types = ['appetizer', 'main', 'dessert']
        for course in course_types:
            dish_names = request.form.getlist(f'{course}_name[]')
            dish_ingredients = request.form.getlist(f'{course}_ingredients[]')
            
            for name, ingredients in zip(dish_names, dish_ingredients):
                if name and ingredients:  # Only add if both fields are filled
                    dish = Dish(
                        name=name,
                        ingredients=ingredients,
                        course_type=course
                    )
                    meal.dishes.append(dish)

        db.session.commit()
        flash('Meal updated successfully!', 'success')
        return redirect(url_for('meal_details', meal_id=meal.id))
        
    return render_template('edit_meal.html', meal=meal)

@app.route('/rsvp/<int:meal_id>', methods=['POST'])
@login_required
def rsvp_meal(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    
    # Check if user is not the host
    if meal.host_id == session['user_id']:
        flash('You cannot RSVP to your own meal', 'error')
        return redirect(url_for('meal_details', meal_id=meal_id))
    
    # Check if meal is active
    if not meal.is_active():
        flash('This meal is no longer active', 'error')
        return redirect(url_for('meal_details', meal_id=meal_id))
    
    # Check if user already has an RSVP
    existing_rsvp = RSVP.query.filter_by(
        meal_id=meal_id,
        guest_id=session['user_id']
    ).first()
    
    if existing_rsvp:
        flash('You have already RSVPed to this meal', 'error')
        return redirect(url_for('meal_details', meal_id=meal_id))
    
    # Check if meal is full
    if not meal.can_accept_more_guests():
        flash('Sorry, this meal is full', 'error')
        return redirect(url_for('meal_details', meal_id=meal_id))
    
    # Create new RSVP
    rsvp = RSVP(meal_id=meal_id, guest_id=session['user_id'])
    db.session.add(rsvp)
    db.session.commit()
    
    flash('RSVP submitted successfully! Waiting for host confirmation.', 'success')
    return redirect(url_for('meal_details', meal_id=meal_id))

@app.route('/confirm-rsvp/<int:rsvp_id>', methods=['POST'])
@login_required
def confirm_rsvp(rsvp_id):
    rsvp = RSVP.query.get_or_404(rsvp_id)
    meal = rsvp.meal
    
    # Check if current user is the host
    if meal.host_id != session['user_id']:
        flash('Only the host can confirm RSVPs', 'error')
        return redirect(url_for('meal_details', meal_id=meal.id))
    
    # Check if meal is full
    if not meal.can_accept_more_guests():
        flash('Cannot confirm RSVP: meal is full', 'error')
        return redirect(url_for('meal_details', meal_id=meal.id))
    
    rsvp.status = 'confirmed'
    db.session.commit()
    
    flash('RSVP confirmed successfully!', 'success')
    return redirect(url_for('meal_details', meal_id=meal.id))

@app.route('/reject-rsvp/<int:rsvp_id>', methods=['POST'])
@login_required
def reject_rsvp(rsvp_id):
    rsvp = RSVP.query.get_or_404(rsvp_id)
    meal = rsvp.meal
    
    # Check if current user is the host
    if meal.host_id != session['user_id']:
        flash('Only the host can reject RSVPs', 'error')
        return redirect(url_for('meal_details', meal_id=meal.id))
    
    rsvp.status = 'rejected'
    db.session.commit()
    
    flash('RSVP rejected', 'success')
    return redirect(url_for('meal_details', meal_id=meal.id))

@app.route('/remove-guest/<int:rsvp_id>', methods=['POST'])
@login_required
def remove_guest(rsvp_id):
    rsvp = RSVP.query.get_or_404(rsvp_id)
    meal = rsvp.meal
    
    # Check if current user is the host
    if meal.host_id != session['user_id']:
        flash('Only the host can remove guests', 'error')
        return redirect(url_for('meal_details', meal_id=meal.id))
    
    db.session.delete(rsvp)
    db.session.commit()
    
    flash('Guest removed successfully', 'success')
    return redirect(url_for('meal_details', meal_id=meal.id))

@app.route('/profile/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    is_own_profile = 'user_id' in session and session['user_id'] == user_id
    
    # Get hosted meals
    hosted_meals = Meal.query.filter_by(host_id=user_id).all()
    
    # Get attended meals
    attended_meals = [rsvp.meal for rsvp in user.rsvps if rsvp.status == 'confirmed']
    
    # Get ratings
    host_ratings = [r for r in user.ratings_received if r.rating_type == 'host']
    guest_ratings = [r for r in user.ratings_received if r.rating_type == 'guest']
    
    return render_template('user_profile.html',
                         user=user,
                         is_own_profile=is_own_profile,
                         hosted_meals=hosted_meals,
                         attended_meals=attended_meals,
                         host_ratings=host_ratings,
                         guest_ratings=guest_ratings)

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        # Update user information
        user.bio = request.form.get('bio', '').strip()
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_profile', user_id=user.id))
    return render_template('edit_profile.html', user=user)

@app.route('/rate/<int:meal_id>/<int:rated_user_id>', methods=['POST'])
@login_required
def rate_user(meal_id, rated_user_id):
    meal = Meal.query.get_or_404(meal_id)
    rated_user = User.query.get_or_404(rated_user_id)
    rating_type = request.form['rating_type']
    
    # Validate rating type and permissions
    if rating_type == 'host' and not session['user_id'] in [rsvp.guest_id for rsvp in meal.guests if rsvp.status == 'confirmed']:
        flash('You must be a confirmed guest to rate the host', 'error')
        return redirect(url_for('meal_details', meal_id=meal_id))
    
    if rating_type == 'guest' and meal.host_id != session['user_id']:
        flash('Only the host can rate guests', 'error')
        return redirect(url_for('meal_details', meal_id=meal_id))
    
    # Check if rating already exists
    existing_rating = Rating.query.filter_by(
        rater_id=session['user_id'],
        rated_user_id=rated_user_id,
        meal_id=meal_id,
        rating_type=rating_type
    ).first()
    
    if existing_rating:
        flash('You have already rated this user for this meal', 'error')
        return redirect(url_for('meal_details', meal_id=meal_id))
    
    # Create rating
    rating = Rating(
        rating=int(request.form['rating']),
        comment=request.form.get('comment', '').strip(),
        rater_id=session['user_id'],
        rated_user_id=rated_user_id,
        meal_id=meal_id,
        rating_type=rating_type
    )
    
    db.session.add(rating)
    db.session.commit()
    
    flash('Rating submitted successfully!', 'success')
    return redirect(url_for('meal_details', meal_id=meal_id))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

