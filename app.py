from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, make_response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_wtf import CSRFProtect
from flask import (render_template, redirect, url_for, request, 
                  flash, jsonify, make_response, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import random
import string
import json
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import abort
from functools import wraps


# Import the db object from your extensions module (or adjust if importing from __init__)
from extensions import db

from models import Users, Flights, Bookings

# --------------------------
# INITIALIZING EXTENSIONS
# --------------------------
login_manager = LoginManager()
csrf = CSRFProtect()

# --------------------------
# APPLICATION FACTORY
# --------------------------
def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flyin.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize db, login_manager, and csrf with the app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'login'

    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    @login_manager.user_loader
    def load_user(user_id):
        return Users.query.get(int(user_id))

    with app.app_context():
        db.create_all()  # Ensure all tables are created

    return app

app = create_app()

# --------------------------
# COMMON UTILITY FUNCTIONS
# --------------------------
def generate_booking_ref():
    while True:
        ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not Bookings.query.filter_by(bookingNum=ref).first():
            return ref

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated

# --------------------------
# AUTHENTICATION ROUTES
# --------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Validate required fields
        required_fields = ['icNumber', 'name', 'phoneNumber', 'email', 'username', 'password']
        if not all(field in request.form for field in required_fields):
            flash('All fields are required!', 'error')
            return redirect(url_for('register'))

        # Check for existing user
        existing_user = Users.query.filter(
            (Users.email == request.form['email']) | 
            (Users.username == request.form['username']) | 
            (Users.icNumber == request.form['icNumber'])
        ).first()

        if existing_user:
            flash('User already exists with these details!', 'error')
            return redirect(url_for('register'))

        # Create user
        try:
            new_user = Users(
                icNumber=request.form['icNumber'],
                name=request.form['name'],
                phoneNumber=request.form['phoneNumber'],
                email=request.form['email'],
                username=request.form['username'],
                is_admin=False  # Explicitly set default
            )
            new_user.set_password(request.form['password'])
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'error')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Users.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))



# --------------------------
# CUSTOMER ROUTES
# --------------------------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    bookings = Bookings.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html', bookings=bookings)

@app.route('/profile_settings', methods=['POST'])
@login_required
def profile_settings():
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            # Verify current password if changing sensitive fields
            if any([
                request.form.get('email') != current_user.email,
                request.form.get('username') != current_user.username,
                new_password
            ]):
                if not current_password or not current_user.check_password(current_password):
                    flash('Current password is required for these changes', 'error')
                    return redirect(url_for('user_dashboard'))

            # Check unique constraints
            fields_to_check = {
                'email': request.form['email'],
                'username': request.form['username'],
                'icNumber': request.form['icNumber'],
                'phoneNumber': request.form['phoneNumber']
            }

            for field, value in fields_to_check.items():
                existing = Users.query.filter(
                    getattr(Users, field) == value,
                    Users.id != current_user.id
                ).first()
                if existing:
                    flash(f'{field.capitalize()} already exists!', 'error')
                    return redirect(url_for('user_dashboard'))

            # Update profile fields
            current_user.name = request.form['name']
            current_user.icNumber = request.form['icNumber']
            current_user.phoneNumber = request.form['phoneNumber']
            current_user.username = request.form['username']
            current_user.email = request.form['email']

            # Handle password change
            if new_password:
                if new_password != confirm_password:
                    flash('New passwords do not match!', 'error')
                    return redirect(url_for('user_dashboard'))
                current_user.set_password(new_password)

            db.session.commit()
            flash('Profile updated successfully!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Update failed: {str(e)}', 'error')

    return redirect(url_for('user_dashboard'))

from flask import request, render_template, jsonify
from flask_login import login_required
from datetime import datetime

from datetime import datetime, time

@app.route('/search_flights', methods=['GET', 'POST'])
@login_required
def search_flights():
    if request.method == 'POST':
        try:
            origin = request.form.get('origin', '').strip().upper()
            destination = request.form.get('destination', '').strip().upper()
            departure_date = datetime.strptime(request.form.get('departure_date'), '%Y-%m-%d').date()

            flights = Flights.query.filter(
                Flights.origin == origin,
                Flights.destination == destination,
                Flights.date == departure_date,
                Flights.availableSeats > 0
            ).all()

            if not flights:
                flash('No flights found. Try different dates or routes.', 'info')
                return redirect(url_for('search_flights'))

            return render_template('search_results.html', flights=flights)

        except ValueError:
            flash('Invalid date format', 'error')
        except Exception as e:
            flash(f'Search error: {str(e)}', 'error')

    return render_template('search_flights.html', datetime=datetime)

@app.route('/book_flight/<int:flight_id>', methods=['GET', 'POST'])
@login_required
def book_flight(flight_id):
    flight = Flights.query.get_or_404(flight_id)
    
    if request.method == 'POST':
        try:
            if flight.availableSeats <= 0:
                flash('No seats available', 'error')
                return redirect(url_for('search_flights'))

            booking = Bookings(
                bookingNum=generate_booking_ref(),
                user_id=current_user.id,
                flight_id=flight.id,
                seatNum=request.form.get('seat_number', '').upper() or None
            )

            flight.availableSeats -= 1
            db.session.add(booking)
            db.session.commit()
            
            return redirect(url_for('booking_confirmation', booking_ref=booking.bookingNum))

        except Exception as e:
            db.session.rollback()
            flash(f'Booking failed: {str(e)}', 'error')
    
    return render_template('book_flight.html', flight=flight)

def assign_seat(flight):
    """Assigns a seat while maintaining airplane balance factors"""
    # Get all booked seats for this flight
    booked_seats = [booking.seatNum for booking in flight.bookings if booking.seatNum]
    
    # Define seat layout (6 seats per row, 10 rows)
    rows = 'ABCDEF'
    all_seats = [f"{row}{col}" for row in rows for col in range(1, 11)]
    
    # Get current balance counts
    front_seats = 0
    back_seats = 0
    left_seats = 0
    right_seats = 0
    
    for seat in booked_seats:
        row = seat[0]
        col = int(seat[1:])
        
        # Front/Back balance
        if col <= 5:
            front_seats += 1
        else:
            back_seats += 1
            
        # Left/Right balance
        if row in {'A', 'B', 'C'}:
            left_seats += 1
        else:
            right_seats += 1

    # Find first available seat that maintains balance
    for seat in all_seats:
        if seat in booked_seats:
            continue
            
        row = seat[0]
        col = int(seat[1:])
        
        # Calculate potential new balances
        new_front = front_seats + (1 if col <= 5 else 0)
        new_back = back_seats + (1 if col > 5 else 0)
        new_left = left_seats + (1 if row in {'A', 'B', 'C'} else 0)
        new_right = right_seats + (1 if row in {'D', 'E', 'F'} else 0)
        
        # Check balance factors
        front_back_diff = abs(new_front - new_back)
        left_right_diff = abs(new_left - new_right)
        
        if front_back_diff <= 3 and left_right_diff <= 3:
            return seat
    
    return None

@app.route('/checkin/<string:booking_num>', methods=['POST'])
@login_required
def checkin(booking_num):
    booking = Bookings.query.filter_by(
        bookingNum=booking_num,
        user_id=current_user.id
    ).first_or_404()

    if booking.bookingStatus == "Checked-in":
        flash("Already checked-in", "error")
        return jsonify(success=False)

    if not booking.seatNum:
        flight = booking.flight
        assigned_seat = assign_seat(flight)
        if not assigned_seat:
            flash("No available seats maintaining balance", "error")
            return jsonify(success=False)
            
        booking.seatNum = assigned_seat
        flash(f"Assigned seat {assigned_seat}", "success")

    booking.bookingStatus = "Checked-in"
    db.session.commit()
    flash("Check-in successful!", "success")
    return jsonify(success=True)

@app.route('/booking_confirmation/<booking_ref>')
@login_required
def booking_confirmation(booking_ref):
    booking = Bookings.query.filter_by(bookingNum=booking_ref, user_id=current_user.id).first_or_404()
    return render_template('booking_confirmation.html', booking=booking)

@app.route('/manage_booking', methods=['GET', 'POST'])
@login_required
def manage_booking():
    if request.method == 'POST':
        booking_num = request.form.get('bookingNum', '').strip().upper()
        booking = Bookings.query.filter_by(
            bookingNum=booking_num, 
            user_id=current_user.id
        ).first()
        
        if not booking:
            flash('No booking found with that reference', 'error')
            return redirect(url_for('manage_booking'))
            
        return render_template('manage_booking.html', booking=booking)
    
    bookings = Bookings.query.filter_by(user_id=current_user.id).all()
    return render_template('manage_booking.html', bookings=bookings)

@app.route('/cancel_booking/<string:booking_num>', methods=['POST'])
@login_required
def cancel_booking(booking_num):
    booking = Bookings.query.filter_by(
        bookingNum=booking_num,
        user_id=current_user.id
    ).first_or_404()

    try:
        db.session.delete(booking)
        db.session.commit()
        flash('Booking cancelled successfully!', 'success')
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling booking: {str(e)}', 'error')
        return jsonify(success=False)

@app.route('/download_ticket/<booking_ref>')
def download_ticket(booking_ref):
    booking = Bookings.query.filter_by(bookingNum=booking_ref).first_or_404()
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    
    # Add ticket content
    p.drawString(100, 700, f"Ticket for {booking.user.name}")
    p.drawString(100, 680, f"Flight: {booking.flight.flightNum}")
    p.drawString(100, 660, f"Seat: {booking.seatNum}")
    
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"ticket_{booking_ref}.pdf")

# --------------------------
# ADMIN ROUTES
# --------------------------

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Unauthorized access!', 'error')
        return redirect(url_for('user_dashboard'))
    users = Users.query.all()
    flights = Flights.query.all()
    current_date = datetime.now()
    return render_template('admin_dashboard.html', flights=flights, current_date=current_date, datetime=datetime)
    
@app.route('/admin/add_flight', methods=['POST'])
@admin_required
def add_flight():
    if not current_user.is_admin:
        abort(403)
    
    try:
        flight_num = request.form['flightNum'].strip().upper()
        
        # Check for existing flight number
        if Flights.query.filter_by(flightNum=flight_num).first():
            flash(f'Flight {flight_num} already exists!', 'error')
            return redirect(url_for('admin_dashboard'))

        # Convert times properly
        departure_time = datetime.strptime(request.form['departureTime'], '%H:%M').time()
        arrival_time = datetime.strptime(request.form['arrivalTime'], '%H:%M').time()
        
        new_flight = Flights(
            flightNum=flight_num,
            airline=request.form['airline'],
            origin=request.form['origin'].strip().upper(),
            destination=request.form['destination'].strip().upper(),
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            departureTime=departure_time,
            arrivalTime=arrival_time,
            price=float(request.form['price']),
            availableSeats=int(request.form['availableSeats'])
        )

        db.session.add(new_flight)
        db.session.commit()
        flash(f'Flight {flight_num} added successfully!', 'success')
        
    except ValueError as e:
        db.session.rollback()
        flash(f'Invalid input format: {str(e)}', 'error')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Database error: {str(e)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Unexpected error: {str(e)}', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_flight/<int:flight_id>', methods=['POST'])
@admin_required
def edit_flight(flight_id):
    if not current_user.is_admin:
        abort(403)
    
    try:
        flight = Flights.query.get_or_404(flight_id)

        # Update flight details
        flight.flightNum = request.form['flightNum']
        flight.airline = request.form['airline']
        flight.origin = request.form['origin']
        flight.destination = request.form['destination']
        flight.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        flight.departureTime = datetime.strptime(request.form['departureTime'], '%H:%M').time()
        flight.arrivalTime = datetime.strptime(request.form['arrivalTime'], '%H:%M').time()
        flight.price = float(request.form['price'])
        flight.availableSeats = int(request.form['availableSeats'])

        # Commit changes
        db.session.commit()
        flash('Flight updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating flight: {str(e)}', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_flight/<int:flight_id>', methods=['POST'])
@admin_required
def delete_flight(flight_id):
    if not current_user.is_admin:
        abort(403)
    
    try:
        flight = Flights.query.get_or_404(flight_id)
        db.session.delete(flight)
        db.session.commit()
        flash('Flight deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting flight: {str(e)}', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/view_passengers/<int:flight_id>')
@admin_required
def view_passengers(flight_id):
    flight = Flights.query.get_or_404(flight_id)
    
    # Get passengers with booking details
    passengers = db.session.query(
        Users.name,
        Users.icNumber,
        Users.email,
        Bookings.bookingNum,
        Bookings.seatNum,
        Bookings.bookingStatus
    ).join(Bookings).filter(
        Bookings.flight_id == flight_id
    ).all()

    return render_template('view_passengers.html', 
                         flight=flight,
                         passengers=passengers)

# --------------------------
# API ENDPOINTS
# --------------------------
@app.route('/get_airports', methods=['GET'])
def get_airports():
    query = request.args.get('query', '').strip().upper()
    
    if len(query) < 2:
        return jsonify([])

    # Get unique airports from existing flights
    origins = db.session.query(Flights.origin).filter(
        Flights.origin.ilike(f'%{query}%')
    ).distinct().all()

    destinations = db.session.query(Flights.destination).filter(
        Flights.destination.ilike(f'%{query}%')
    ).distinct().all()

    suggestions = [{'code': o[0], 'name': ''} for o in origins] + \
                 [{'code': d[0], 'name': ''} for d in destinations]

    return jsonify(suggestions[:10])  # Limit to 10 suggestions

@app.route('/get_available_seats', methods=['GET'])
@login_required
def get_available_seats():
    flight_id = request.args.get('flight_id')
    flight = Flights.query.get_or_404(flight_id)
    booked_seats = [b.seatNum for b in flight.bookings if b.seatNum]
    all_seats = [f"{row}{col}" for row in 'ABCDEF' for col in range(1, 11)]
    return jsonify({'available_seats': [s for s in all_seats if s not in booked_seats]})

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

if __name__ == '__main__':
    app.run(debug=True)
