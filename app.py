from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --------- Data Classes ---------
class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    ingredients = db.Column(db.Text)
    course_type = db.Column(db.String(50))
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'))

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    time = db.Column(db.DateTime)
    max_guests = db.Column(db.Integer)
    fee = db.Column(db.Float)
    active_until = db.Column(db.DateTime)
    dishes = db.relationship('Dish', backref='meal', cascade="all, delete-orphan")

    def is_active(self):
        return datetime.now() <= self.active_until

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/post-meal', methods=['GET', 'POST'])
def post_meal():
    if request.method == 'POST':
        host_name = request.form['host']
        location = request.form['location']
        date_str = request.form['meal_date']
        time_str = request.form['meal_time']
        time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        max_guests = int(request.form['max_guests'])
        fee = float(request.form['fee'])
        active_hours = int(request.form['active_hours'])

        meal = Meal(
            host_name=host_name,
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


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

