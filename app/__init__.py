from flask import Flask
from models import db, User
from app.routes import main
from flask_login import LoginManager, current_user

# ✅ تهيئة الـ login_manager
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # ✅ إعدادات التطبيق
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///barbershop.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = "secret123"
    app.config['SERVER_NAME'] = 'localhost:5000'
    app.config['APPLICATION_ROOT'] = '/'
    app.config['PREFERRED_URL_SCHEME'] = 'http'

    # ✅ تهيئة الـ login_manager
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = "يجب تسجيل الدخول أولاً!"
    login_manager.login_message_category = "warning"

    # ✅ تهيئة الـ database (من models.py)
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
        # ✅ إنشاء الـ admin user لو مش موجود
        create_admin_user(app)

    # ✅ ربط الـ Blueprint مرة واحدة
    app.register_blueprint(main)

    # ✅ تحديد loader الخاص بـ login_manager
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ✅ تفعيل current_user في كل templates
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    return app

# ✅ دالة لإنشاء يوزر admin تلقائيًا لو مش موجود
def create_admin_user(app):
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            new_admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(new_admin)
            db.session.commit()
