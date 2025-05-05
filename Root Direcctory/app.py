import os
import logging
import random
import string

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, current_user, login_user, logout_user, login_required


# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)

# Set a default secret key if not in environment
if not os.environ.get("SESSION_SECRET"):
    # Generate a random secret key
    secret_key = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
    app.secret_key = secret_key
else:
    app.secret_key = os.environ.get("SESSION_SECRET")

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'  # Redirects to home page instead of a separate login

# Register Jinja2 custom filters
from templates.jinja_filters import register_filters
register_filters(app)

# Import routes after app is initialized
with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    
    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))
    
    # Route for main index page
    @app.route('/')
    def index():
        return render_template('index.html')
        
    # Route for upload page with drag and drop interface
    @app.route('/upload')
    def upload():
        return render_template('upload.html')
        
    # Simple login route - just a placeholder for now
    @app.route('/login')
    def login():
        return redirect(url_for('index'))
        
    # Simple logout route - just a placeholder for now
    @app.route('/logout')
    def logout():
        return redirect(url_for('index'))
        
    # Simple register route - just a placeholder for now
    @app.route('/register')
    def register():
        return redirect(url_for('index'))

    # Import and register blueprints
    from routes.admin import admin_bp
    from routes.api import api_bp
    
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables
    db.create_all()
