import pytest
from app import app as flask_app # app.py should define 'app = Flask(...)'
from models import db as _db # models.py should define 'db = SQLAlchemy(...)'
import tempfile
import os

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""

    # Create a temporary file for the SQLite database
    db_fd, db_path = tempfile.mkstemp(suffix='.sqlite')

    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False, # Disable CSRF for forms if you have them
        "DEBUG": False, # Ensure debug mode is off for tests
        "LOGIN_DISABLED": True # If you have login logic that might interfere
    })

    with flask_app.app_context():
        _db.create_all() # Create database schema

    yield flask_app

    # Teardown: close and remove the temporary database file
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture() # Default scope is 'function'
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def db(app):
    """
    Provides the database instance for a test.
    This fixture also handles cleaning up the database after each test
    by rolling back any pending transactions and clearing the session.
    It does not drop all tables after each test to speed up testing,
    assuming tests clean up their own created data or are read-only.
    """
    with app.app_context():
        yield _db
        # Clean up the session to ensure no open transactions interfere between tests
        _db.session.remove()
        # If more aggressive cleanup is needed per test:
        # _db.drop_all()
        # _db.create_all()
