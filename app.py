import os
import logging
from flask import Flask
# SQLAlchemy and Base are now primarily managed in models.py
# from flask_sqlalchemy import SQLAlchemy # No longer directly used to create db here
# from sqlalchemy.orm import DeclarativeBase # No longer directly used to create Base here
from werkzeug.middleware.proxy_fix import ProxyFix
from logging.handlers import RotatingFileHandler
import os
from models import db # Import db instance from models.py

# Create the app
app = Flask(__name__)

# Logging Configuration will be set up after app initialization

# --- Logging Configuration START ---
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO) # Convert string to logging level
log_file_path = os.environ.get("LOG_FILE_PATH", "osint_tool.log")

# Configure app.logger directly
# Avoid adding handlers multiple times if app reloads (though less of an issue with Flask's typical run)
if not app.logger.handlers:
    app.logger.setLevel(log_level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s")

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    app.logger.addHandler(ch)

    # File Handler
    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
                print(f"Log directory created: {log_dir}")
            except Exception as e:
                print(f"Error creating log directory {log_dir}: {e}")
                # Fallback or skip file logging if directory creation fails

        if not log_dir or os.path.exists(log_dir): # Proceed if no dir needed or dir exists/was created
            try:
                fh = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5)
                fh.setLevel(log_level)
                fh.setFormatter(formatter)
                app.logger.addHandler(fh)
                app.logger.info("File logging enabled to %s", log_file_path)
            except Exception as e:
                 app.logger.error("Failed to set up file logging to %s: %s", log_file_path, e, exc_info=True)
        else:
            app.logger.warning("File logging skipped as log directory could not be confirmed: %s", log_dir)

# Remove Flask's default handler if we've added our own to app.logger
# This is to prevent duplicate messages to console if Flask adds one by default.
# However, app.logger is separate from Werkzeug logger.
# For more comprehensive logging (incl. Werkzeug), one might configure logging.getLogger() (root)
# or specific loggers like logging.getLogger('werkzeug').
# For now, focusing on app.logger.

app.logger.info("OSINT Tool application starting with log level %s", log_level_str)
# --- Logging Configuration END ---

app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///osint_tool.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the imported db with the app
db.init_app(app)

# Models are already imported via 'from models import db' which executes models.py.
# To ensure all models defined in models.py are known to SQLAlchemy before create_all,
# an explicit 'import models' can still be useful if models.py contains more than just db definition.
# However, since SearchResult etc are defined in models.py using the 'db' from that file,
# they are already registered with that db instance.

# Import routes AFTER app, db (initialized), and models (defined via models.py execution)
from routes import *  # noqa: F401, F403

with app.app_context():
    # db.create_all() will now use the db instance that has been initialized with the app
    # and knows about the models defined in models.py
    db.create_all()
