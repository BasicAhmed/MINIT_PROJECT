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

db = SQLAlchemy()
db.init_app(app)

with app.app_context():
    db.create_all()  
# Set the secret key
app.config['SECRET_KEY'] = os.getenv('APP_SECRET_KEY', 'fallback_secret_key')

# Routes
@app.route('/', methods=["POST", 'GET'])
def home():
    if "user" in session and session["user"] != "":
        # Read options from the .txt file
        try:
            with open('static/airport_lists.txt', 'r') as file:
                options = [line.strip() for line in file if line.strip()]  # Remove empty lines
        except FileNotFoundError:
            options = []
        if request.method == "POST":
            selected_trip = request.form.get('trip')
            if selected_trip == "round-trip":
                return_date = request.form.get('return-date')
            else:
                return_date = "None"
            passengers = request.form.get('number-of-passengers')
            promo_code = request.form.get('promo-code')
            print(promo_code)
            stops = []
            for key in request.form:
                if key.startswith('origin-location') or key.startswith('destination-location'):
                    stops.append({key: request.form[key]})
            departureDates = []
            for r in request.form:
                if r.startswith('departure-date'):
                    departureDates.append({r: request.form[r]})
            originLocations = ",".join(value for stop in stops for key, value in stop.items() if key.startswith('origin-location'))
            destinationLocations = ",".join(value2 for stop2 in stops for key2, value2 in stop2.items() if key2.startswith('destination-location'))
            departures = ",".join(value3 for date in departureDates for key3, value3 in date.items() if key3.startswith('departure-date'))
            if (("Sultan Haji Ahmad Shah (KUA)" in destinationLocations.split(',') and promo_code=="BASIC20")  or ("Sultan Mahmud Airport (TGG)" in destinationLocations.split(',') and promo_code=="BASIC10")) or (promo_code == ""):
                if selected_trip != "multi-city":
                    return redirect(url_for(
                        "flights",
                        trip=selected_trip,
                        return_date=return_date,
                        passengers=passengers,
                        promo_code=promo_code,
                        origin_locations=originLocations,
                        destination_locations=destinationLocations,
                        departure_dates=departures
                    ))
                else:
                    return redirect(url_for(
                        "flightsmulticity",
                        trip=selected_trip,
                        passengers=passengers,
                        promo_code=promo_code,
                        origin_locations=originLocations,
                        destination_locations=destinationLocations,
                        departure_dates=departures
                    ))
            else:
                if promo_code == "BASIC20" or promo_code == "BASIC10":
                    flash("Promo Code cannot be used for this destination!")
                    return redirect(url_for("home"))
                else:
                    flash("Invalid Promo Code")
                    return redirect(url_for("home"))
        return render_template("index.html", profile_Name=session["user"], options=options)
    else:
        return redirect(url_for("register"))

@app.route('/home')
def redirectToDefault():
    return redirect(url_for("home"))

@app.route('/register', methods=["POST", "GET"])
def register():
    if "user" in session and session["user"] != "":
        return redirect(url_for("home"))

    if request.method == "POST":
        new_ic = request.form["reg-ic"]
        new_name = request.form["reg-full-name"]
        new_hpNo = request.form["reg-hp-no"]
        new_email = request.form["reg-email"]
        new_username = request.form["reg-username"]
        new_password = request.form["reg-password"]
        try:
            int(new_ic)
            if Users.query.filter_by(icNumber=str(new_ic)).first():
                flash(f"User with IC number {new_ic} already exists!")
            if Users.query.filter_by(email=new_email).first() or Users.query.filter_by(username=new_username).first():
                flash("Email or Username already exists!")
            if Users.query.filter_by(phoneNumber=new_hpNo).first():
                flash("That phone number is already registered!")
            else:
                test_email = new_email.split("@")
                valid_emails = ['gmail.com', 'yahoo.com', 'hotmail.com', 'mmu.edu.my', 'live.com', 'student.mmu.edu.my']  # Only these for now
                if (len(test_email) == 1) or test_email[1] not in valid_emails:
                    flash("Invalid email!")
                isCode = new_hpNo[0]
                if isCode == "+":
                    new_user = Users(icNumber=new_ic, name=new_name, phoneNumber=new_hpNo, email=new_email, username=new_username, password=new_password)
                    db.session.add(new_user)
                    db.session.commit()
                    return redirect(url_for("login"))
                else:
                    flash("Please include country calling code!")
        except:
            flash("Please enter a valid IC Number.")

    return render_template("register.html")

@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        usernameInput = request.form["login-username"]
        passwordInput = request.form["login-password"]

        if Users.query.filter_by(username=usernameInput).first() and Users.query.filter_by(username=usernameInput).first().password == passwordInput:
            session.permanent = True
            session["user"] = usernameInput
            return redirect(url_for("home"))
        else:
            flash("Invalid Username or Password!")
    return render_template("login.html")

@app.route('/logout')
def logout():
    if "user" in session and session["user"] != "":
        session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True)
