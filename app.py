from flask import Flask, render_template, url_for
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Import routes
from routes import main_routes

# Register blueprints
app.register_blueprint(main_routes.bp)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
