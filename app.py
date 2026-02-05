from flask import Flask, render_template
from flask_mail import Mail
from config import Config
# from firebase_config import initialize_firebase_admin  # Temporarily disabled

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Flask-Mail
mail = Mail(app)

# Initialize Firebase (disabled for now)
# initialize_firebase_admin()

# Import routes
from routes import main_routes, api_routes

# Initialize mail in api_routes
api_routes.init_mail(mail)

# Register blueprints
app.register_blueprint(main_routes.bp)
app.register_blueprint(api_routes.bp)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
