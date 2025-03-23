from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
db = SQLAlchemy()

# ✅ New User model for authentication
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='barber')  # Default role

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ✅ Check role methods
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role == 'manager'
    
    def is_barber(self):
        return self.role == 'barber'

class Barber(db.Model):
    __tablename__ = 'barbers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<Barber {self.name}>"

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    last_haircut = db.Column(db.Date, nullable=True)
    interval_days = db.Column(db.Integer, nullable=True)
    barber_id = db.Column(db.Integer, db.ForeignKey('barbers.id'), nullable=True)
    barber = db.relationship("Barber", backref="clients")
    haircut_image = db.Column(db.String(200), nullable=True)
    haircut_description = db.Column(db.String(200), default='غير محدد')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Do NOT add another relationship named 'haircuts' here!
    haircuts = db.relationship(
        "Haircut",
        backref="client",
        cascade="all, delete-orphan"
    )


class Haircut(db.Model):
    __tablename__ = 'haircuts'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    barber_id = db.Column(db.Integer, db.ForeignKey('barbers.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    price = db.Column(db.Float, nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    # Here's the relationship
    #client = db.relationship("Client", backref="haircuts")
    barber = db.relationship("Barber", backref="haircuts")
    client_id = db.Column(
        db.Integer,
        db.ForeignKey('clients.id', ondelete='SET NULL'),
        nullable=True
    )