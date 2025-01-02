from flask import Flask, render_template
from flask_migrate import Migrate  # Import Flask-Migrate
from models import db  # Import db from models
from login import login_bp   
from checkin import checkin_bp  

app = Flask(__name__)
app.secret_key = "your_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Register blueprints
app.register_blueprint(login_bp)
app.register_blueprint(checkin_bp)  

@app.route("/")
def home():
    return render_template("index.html")  # Rendering the home page template

if __name__ == "__main__":
    app.run(debug=True)
