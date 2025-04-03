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

if __name__ == '__main__':
    app.run(debug=True)
