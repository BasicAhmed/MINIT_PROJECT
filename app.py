from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import timedelta
import os
from utils import get_access_token, get_flights, extract_flight_details
from models import db, Users, Bookings
from config import Config

# Initialize the Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy with the app
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Set the secret key
app.config['SECRET_KEY'] = os.getenv('APP_SECRET_KEY', 'fallback_secret_key')


# Routes
@app.route('/', methods=["POST", 'GET'])
def home():
    if "user" not in session or not session.get("user"):
        return redirect(url_for("login"))  # Redirect to login if user is not logged in
    
    # Load options from file
    try:
        with open('static/airport_lists.txt', 'r') as file:
            options = [line.strip() for line in file if line.strip()]  # Remove empty lines
    except FileNotFoundError:
        options = []

    if request.method == "POST":
        selected_trip = request.form.get('trip')
        return_date = request.form.get('return-date') if selected_trip == "round-trip" else "None"
        passengers = request.form.get('number-of-passengers')
        promo_code = request.form.get('promo-code')
        
        stops = [
            {key: request.form[key]} for key in request.form
            if key.startswith('origin-location') or key.startswith('destination-location')
        ]
        departure_dates = [
            {key: request.form[key]} for key in request.form
            if key.startswith('departure-date')
        ]

        origin_locations = ",".join(value for stop in stops for key, value in stop.items() if key.startswith('origin-location'))
        destination_locations = ",".join(value for stop in stops for key, value in stop.items() if key.startswith('destination-location'))
        departures = ",".join(value for date in departure_dates for key, value in date.items() if key.startswith('departure-date'))

        if (("Sultan Haji Ahmad Shah (KUA)" in destination_locations.split(',') and promo_code == "BASIC20") or 
            ("Sultan Mahmud Airport (TGG)" in destination_locations.split(',') and promo_code == "BASIC10")) or not promo_code:
            if selected_trip != "multi-city":
                return redirect(url_for(
                    "flights",
                    trip=selected_trip,
                    return_date=return_date,
                    passengers=passengers,
                    promo_code=promo_code,
                    origin_locations=origin_locations,
                    destination_locations=destination_locations,
                    departure_dates=departures
                ))
            else:
                return redirect(url_for(
                    "flightsmulticity",
                    trip=selected_trip,
                    passengers=passengers,
                    promo_code=promo_code,
                    origin_locations=origin_locations,
                    destination_locations=destination_locations,
                    departure_dates=departures
                ))
        else:
            flash("Invalid or unusable promo code!")
            return redirect(url_for("home"))

    return render_template("index.html", profile_Name=session["user"], options=options)

@app.route('/register', methods=["POST", "GET"])
def register():
    if "user" in session and session["user"]:
        return redirect(url_for("home"))

    if request.method == "POST":
        try:
            new_ic = int(request.form["reg-ic"])
            new_user = Users.query.filter((Users.icNumber == str(new_ic)) | (Users.email == request.form["reg-email"]) | (Users.username == request.form["reg-username"])).first()
            if new_user:
                flash("User with provided details already exists!")
            else:
                new_user = Users(
                    icNumber=new_ic,
                    name=request.form["reg-full-name"],
                    phoneNumber=request.form["reg-hp-no"],
                    email=request.form["reg-email"],
                    username=request.form["reg-username"],
                    password=request.form["reg-password"]
                )
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for("login"))
        except ValueError:
            flash("Please enter a valid IC Number.")
    return render_template("register.html")

@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        user = Users.query.filter_by(username=request.form["login-username"]).first()
        if user and user.password == request.form["login-password"]:
            session.permanent = True
            session["user"] = user.username
            return redirect(url_for("home"))
        flash("Invalid Username or Password!")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True)
