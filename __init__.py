
from flask import Flask
from routes.search_routes import search_bp
from routes.export_routes import export_bp
from routes.history_routes import history_bp
from utils.db_utils import init_db

def create_app():
    app = Flask(__name__)
    app.register_blueprint(search_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(history_bp)
    init_db()
    return app
