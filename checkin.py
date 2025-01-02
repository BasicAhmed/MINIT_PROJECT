from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Flight

checkin_bp = Blueprint('checkin', __name__)

@checkin_bp.route("/checkin", methods=["GET", "POST"])
def checkin():
    if request.method == "POST":
        booking_reference = request.form["booking_reference"]
        last_name = request.form["last_name"]
        
        # Query the flight based on booking reference and last name
        flight = Flight.query.filter_by(booking_reference=booking_reference, last_name=last_name).first()
        
        if flight:
            flight.checked_in = True  # Set checked_in to True
            db.session.commit()
            return redirect(url_for("checkin.checkin_success"))  # Redirect to success page
        else:
            error_message = "Booking reference and/or last name not found."
            return render_template("checkin.html", error_message=error_message)

    return render_template("checkin.html")

@checkin_bp.route("/checkin/success")
def checkin_success():
    return render_template("checkin_success.html")
