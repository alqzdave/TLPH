from flask import Flask, render_template, request, jsonify
from flask_mail import Mail
from config import Config
import firebase_admin
from firebase_admin import credentials, auth
from datetime import timedelta
import os

app = Flask(__name__)
app.config.from_object(Config)

FAVICON_URL = "https://res.cloudinary.com/dnfkplb3i/image/upload/v1774838705/tlph/branding/denr-favicon-image.ico?v=1774838705"
FAVICON_HEAD_SNIPPET = (
    f'  <link rel="icon" type="image/x-icon" href="{FAVICON_URL}">\n'
    f'  <link rel="shortcut icon" type="image/x-icon" href="{FAVICON_URL}">\n'
)

# Session configuration
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = False  # Set True if using HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Flask-Mail
mail = Mail(app)

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)


# Import routes
from routes import main_routes, api_routes, municipal_routes, seminar_routes, service_routes, service_api_routes, fisheries_routes, environment_routes, forest_routes, livestock_routes, permits_routes, wildlife_routes, farm_routes, payments_routes,regional_routes,superadmin_routes, national_routes, municipal_api_logs

# Initialize mail in api_routes
api_routes.init_mail(mail)

# Register blueprints
app.register_blueprint(main_routes.bp)
app.register_blueprint(api_routes.bp)
app.register_blueprint(municipal_routes.bp)
app.register_blueprint(seminar_routes.bp)
app.register_blueprint(service_routes.bp)
app.register_blueprint(service_api_routes.bp)
app.register_blueprint(fisheries_routes.bp)
app.register_blueprint(environment_routes.bp)
app.register_blueprint(forest_routes.bp)
app.register_blueprint(livestock_routes.bp)
app.register_blueprint(permits_routes.bp)
app.register_blueprint(wildlife_routes.bp)
app.register_blueprint(farm_routes.bp)
app.register_blueprint(payments_routes.bp)
app.register_blueprint(regional_routes.bp)
app.register_blueprint(superadmin_routes.bp)
app.register_blueprint(national_routes.bp)
app.register_blueprint(municipal_api_logs.bp)


# Jinja filter for date formatting
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%b %d, %Y'):
    from datetime import datetime
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except Exception:
            try:
                value = datetime.fromisoformat(value)
            except Exception:
                return format  # Return the format string if parsing fails
    try:
        return value.strftime(format)
    except Exception:
        return format

# Route for disabled account page
@app.route('/account-disabled')
def account_disabled():
    return render_template('account-disabled.html')


@app.after_request
def ensure_favicon_on_all_html(response):
    """Inject favicon links for templates that don't include base.html."""
    try:
        content_type = (response.content_type or '').lower()
        if 'text/html' not in content_type:
            return response

        body = response.get_data(as_text=True)
        if not body or '</head>' not in body.lower():
            return response

        if 'rel="icon"' in body.lower() or "rel='icon'" in body.lower() or 'shortcut icon' in body.lower():
            return response

        lower_body = body.lower()
        idx = lower_body.find('</head>')
        if idx == -1:
            return response

        updated = body[:idx] + FAVICON_HEAD_SNIPPET + body[idx:]
        response.set_data(updated)
    except Exception:
        return response

    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)

@app.route('/api/admin/update-password', methods=['POST'])
def admin_update_password():
    try:
        data = request.get_json()
        uid = data.get('uid')
        new_password = data.get('newPassword')
        
        if not uid or not new_password:
            return jsonify({"success": False, "error": "Missing UID or password"}), 400
            
        # Ito ang nagpapalit ng password sa Firebase Auth nang hindi kailangan ang old password
        auth.update_user(
            uid,
            password=new_password
        )
        
        return jsonify({"success": True})
        
    except Exception as e:
        print("Error updating password:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500