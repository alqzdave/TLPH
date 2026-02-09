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
from routes import main_routes, api_routes, seminar_routes, service_routes, fisheries_routes, environment_routes, forest_routes, livestock_routes, permits_routes, wildlife_routes, farm_routes

# Initialize mail in api_routes
api_routes.init_mail(mail)

# Register blueprints
app.register_blueprint(main_routes.bp)
app.register_blueprint(api_routes.bp)
app.register_blueprint(seminar_routes.bp)
app.register_blueprint(service_routes.bp)
app.register_blueprint(fisheries_routes.bp)
app.register_blueprint(environment_routes.bp)
app.register_blueprint(forest_routes.bp)
app.register_blueprint(livestock_routes.bp)
app.register_blueprint(permits_routes.bp)
app.register_blueprint(wildlife_routes.bp)
app.register_blueprint(farm_routes.bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
