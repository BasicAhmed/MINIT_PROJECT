from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    icNumber = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    phoneNumber = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(18), nullable=False)

class Bookings(db.Model):
    __tablename__ = 'bookings'
    bookingNum = db.Column(db.String(5), primary_key=True, unique=True, nullable=False)
    firstName = db.Column(db.String(255), nullable=False)
    surname = db.Column(db.String(255), nullable=False)
    icNum = db.Column(db.String(12), nullable=False)
    phoneNum = db.Column(db.String(15), nullable=False)
    origin = db.Column(db.String(255), nullable=False)
    destination = db.Column(db.String(255), nullable=False)
    departureTime = db.Column(db.String(5), nullable=False)
    arrivalTime = db.Column(db.String(5), nullable=False)
    date = db.Column(db.String(12), nullable=False)
    flightNum = db.Column(db.String(7), nullable=False)
    seatNum = db.Column(db.String(4), nullable=False)
