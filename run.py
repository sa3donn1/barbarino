from app import create_app
from apscheduler.schedulers.background import BackgroundScheduler
from app.routes import check_and_send_reminders
import atexit
import os
import sys
from flask_login import LoginManager, current_user
from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from models import db
app = create_app()

@app.before_request
def set_db_for_manager():
    if current_user.is_authenticated and current_user.is_manager():
        # Ensure the instance folder exists
        instance_dir = os.path.join(create_app.root_path, 'instance')
        if not os.path.exists(instance_dir):
            os.makedirs(instance_dir)

        # Build the database URI and file path
        manager_db_uri = f"sqlite:///instance/{current_user.username}.sqlite"
        db_file_path = os.path.join(instance_dir, f"{current_user.username}.sqlite")
        
        # Create a new engine for the manager-specific database
        engine = create_engine(manager_db_uri)
        
        # If the database file doesn't exist, create the tables
        if not os.path.exists(db_file_path):
            # This creates all tables defined in your models for the manager database
            db.metadata.create_all(engine)
        
        # Bind the manager-specific session to g.db_session
        g.db_session = scoped_session(sessionmaker(bind=engine))
    else:
        g.db_session = db.session


@app.teardown_request
def remove_session(exception=None):
        if hasattr(g, 'db_session'):
            g.db_session.remove()

# Only do this in a dev environment if you need to:
# with app.app_context():
#  db.create_all()  # This will create tables if they don't exist, but won't drop them.

# Set up APScheduler to run check_and_send_reminders every 24 hours.
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_and_send_reminders, trigger="interval", hours=24)
scheduler.start()

# Ensure the scheduler shuts down when the app exits.
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
