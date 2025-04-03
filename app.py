from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta

app = Flask(__name__)

# --------- In-Memory Storage ---------
meals = []

# --------- Data Classes ---------
class Dish:
    def __init__(self, name, ingredients, course_type):
        self.name = name
        self.ingredients = ingredients
        self.course_type = course_type

class Meal:
    def __init__(self, host_name, dishes, location, time, max_guests, fee, active_hours):
        self.host_name = host_name
        self.dishes = dishes
        self.location = location
        self.time = time
        self.max_guests = max_guests
        self.fee = fee
        self.active_until = datetime.now() + timedelta(hours=active_hours)
        self.guest_requests = []

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

        # Process dishes
        dishes = []
        for i in range(1, 4):  # Appetizer, Main, Dessert
            dish_name = request.form[f'dish{i}_name']
            ingredients = request.form[f'dish{i}_ingredients'].split(',')
            course = ['appetizer', 'main', 'dessert'][i - 1]
            dishes.append(Dish(dish_name, ingredients, course))

        meal = Meal(host_name, dishes, location, time, max_guests, fee, active_hours)
        meals.append(meal)
        return redirect(url_for('home'))
    return render_template('post_meal.html')

@app.route('/browse-meals')
def browse_meals():
    return render_template('browse_meals.html', meals=meals)

if __name__ == '__main__':
    app.run(debug=True)

