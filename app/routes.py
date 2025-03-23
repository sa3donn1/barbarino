import os
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app,session
from models import db, Client, Haircut, Barber, User
from sqlalchemy import func,extract
from utils import validate_phone, validate_date
from werkzeug.utils import secure_filename
#from twilio_utils import send_reminder_message
import calendar
from flask_login import login_user
from flask_login import logout_user
from flask import g

from app.kpi_utils import get_barbers_overview
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import or_
import logging
logging.basicConfig(level=logging.DEBUG)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import current_user

main = Blueprint('main', __name__)
@main.route('/')
def index():
    # ✅ لو المستخدم مش مسجل دخول --> يحوله على صفحة تسجيل الدخول
    if not current_user.is_authenticated:
        return redirect(url_for('main.login'))
    # ✅ لو المستخدم مسجل دخول --> يفتح الصفحة الرئيسية
    return render_template('index.html')

# ✅ صفحة تسجيل الدخول

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('main.dashboard'))

        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'danger')

    return render_template('login.html')

@main.route('/logout')
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('main.login'))

# ✅ صفحة الداشبورد
@main.route('/dashboard')
def dashboard():
    if not current_user.is_authenticated:
        flash('You must log in first.', 'warning')
        return redirect(url_for('main.login'))
    
    if current_user.is_admin():
        # ✅ Show full dashboard for admin
        return render_template('admin_dashboard.html')

    elif current_user.is_manager():
        # ✅ Show limited dashboard for manager
        return render_template('index.html')

    elif current_user.is_barber():
        # ✅ Show restricted dashboard for barber
        return render_template('index.html')

    else:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))


@main.route("/add", methods=["GET", "POST"])
def add_client():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        date_str = request.form.get("last_haircut", "").strip()
        interval_days = request.form.get("interval_days", "").strip()
        typed_barber_name = request.form.get("barber_name", "").strip()
        haircut_desc = request.form.get("haircut_desc", "").strip()

        # 1) تأكد من ملء الحقول المطلوبة
        if not (name and phone and date_str and interval_days and typed_barber_name):
            flash("يرجى ملء جميع الحقول المطلوبة", "error")
            return redirect(url_for("main.add_client"))

        # 2) تحقق من رقم الهاتف
        if not validate_phone(phone):
            flash("رقم الهاتف غير صالح! يجب أن يبدأ بـ 1 ويكون مكونًا من 10 أرقام", "error")
            return redirect(url_for("main.add_client"))

        # 3) تحقق من تاريخ الحلاقة باستخدام validate_date(date_str)
        parsed_date = validate_date(date_str)  # <-- store the return value in a variable
        if not parsed_date:
            flash("تاريخ الحلاقة غير صالح! يرجى إدخاله بصيغة dd/mm/yyyy", "error")
            return redirect(url_for("main.add_client"))

        # 4) تحقق من عدد الأيام
        try:
            interval_val = int(interval_days)
        except ValueError:
            flash("عدد الأيام يجب أن يكون رقمًا صحيحًا", "error")
            return redirect(url_for("main.add_client"))

        # 5) تحقق مما إذا كان الهاتف موجود مسبقًا
        existing = Client.query.filter_by(phone=phone).first()
        if existing:
            flash("العميل برقم الهاتف هذا موجود مسبقًا!", "error")
            return redirect(url_for("main.add_client"))

        # 6) حوّل parsed_date (وهو YYYY-MM-DD) إلى كائن تاريخ
        last_haircut_date = datetime.strptime(parsed_date, "%Y-%m-%d").date()

        # 7) أنشئ كائن Client
        client = Client(
            name=name,
            phone=phone,
            last_haircut=last_haircut_date,
            interval_days=interval_val,
            haircut_description=haircut_desc if haircut_desc else "غير محدد"
        )

        # 8) ابحث عن الحلاق بالاسم المعطى، ثم عيّن barber_id لو وجدناه
        barber = Barber.query.filter_by(name=typed_barber_name).first()
        if barber:
            client.barber_id = barber.id
        else:
            flash("لا يوجد حلاق بهذا الاسم!", "error")
            return redirect(url_for("main.add_client"))

        # 9) تعامل مع رفع الصورة (إن وجدت)
        uploaded_file = request.files.get("haircut_image")
        if uploaded_file and uploaded_file.filename != "":
            filename = secure_filename(uploaded_file.filename)
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
            uploaded_file.save(upload_path)
            client.haircut_image = filename
 # 9) احفظ في قاعدة البيانات باستخدام g.db_session
        # ملاحظة: استخدم g.db_session فقط إذا كان current_user مديرًا
        # أو استخدم طريقة ذكية لاختيار الجلسة حسب الحالة.
        # 10) احفظ في قاعدة البيانات
        if current_user.is_manager():
            g.db_session.add(client)
            g.db_session.commit()
        else: 
        
         db.session.add(client)
         db.session.commit()

        flash("تمت إضافة العميل بنجاح!", "success")
        return redirect(url_for("main.index"))

    # إذا GET, نعرض صفحة الإضافة
    return render_template("add_client.html")





@main.route("/delete/<phone>")
def delete_client(phone):
    client = Client.query.filter_by(phone=phone).first()
    if client:
        db.session.delete(client)
        db.session.commit()   # <-- triggers cascade
        flash("تم حذف العميل بنجاح!", "success")
    else:
        flash("العميل غير موجود", "error")
    return redirect(url_for("main.index"))

@main.route("/search", methods=["POST"])
def search():
    query = request.form.get("query", "").strip()
    
    # إذا لم يُدخل المستخدم أي شيء، أعِد كل النتائج أو تصرّف حسب رغبتك
    if not query:
        clients = Client.query.all()
        return render_template("index.html", clients=clients, search_query=query)

    # جرّب تحويل النص إلى تاريخ بصيغة dd/mm/yyyy
    date_value = None
    try:
        date_value = datetime.strptime(query, "%d/%m/%Y").date()
    except ValueError:
        pass  # لو فشل التحويل، سيبقى date_value = None

    # في حال نجح التحويل إلى تاريخ
    if date_value:
        # استخدم OR للبحث في الاسم + الهاتف + تطابق تاريخ الحلاقة
        clients = Client.query.filter(
            or_(
                Client.name.ilike(f"%{query}%"),       # الاسم
                Client.phone.ilike(f"%{query}%"),      # الهاتف
                Client.last_haircut == date_value      # تاريخ آخر حلاقة
            )
        ).all()
    else:
        # لم نتمكن من تحويل النص إلى تاريخ، إذن ابحث فقط في الاسم والهاتف
        clients = Client.query.filter(
            or_(
                Client.name.ilike(f"%{query}%"),
                Client.phone.ilike(f"%{query}%")
            )
        ).all()

    return render_template("index.html", clients=clients, search_query=query)
@main.route("/next")
def next_haircuts():
    clients = Client.query.all()
    today = date.today()
    next_list = []

    for c in clients:
        if c.last_haircut:
            next_date = c.last_haircut + timedelta(days=c.interval_days)
            remaining_days = (next_date - today).days

            barber_name = c.barber.name if c.barber else "لم يتم تعيين حلاق"

            # We now have 6 items in the tuple:
            #  (name, barber_name, next_date, remaining_days, phone, client_id)
            next_list.append((
                c.name,
                barber_name,
                next_date.strftime("%d/%m/%Y"),
                remaining_days,
                c.phone,
                c.id  # <-- so we can build the change_barber link
            ))

    return render_template("next.html", next_list=next_list)


@main.route("/renew/<phone>", methods=["POST"])
def renew_haircut(phone):
    client = Client.query.filter_by(phone=phone).first_or_404()

    # Grab the rating (if any) from the form
    rating_str = request.form.get("rating", "")
    rating_val = 0.0
    if rating_str:
        try:
            rating_val = float(rating_str)
        except ValueError:
            rating_val = 0.0

    # Create a new Haircut row with the chosen rating
    new_haircut = Haircut(
        client_id=client.id,
        barber_id=client.barber_id,
        date=datetime.utcnow(),
        rating=rating_val
    )
    db.session.add(new_haircut)

    # Update the client's last_haircut date
    client.last_haircut = date.today()
    db.session.commit()

    return redirect(url_for("main.next_haircuts"))

#def check_and_send_reminders():
    from models import Client
    from datetime import date, timedelta
    logging.info("=== [check_and_send_reminders] Started ===")
    today = date.today()
    clients = Client.query.all()
    logging.info(f"Found {len(clients)} clients in the database.")
    for client in clients:
        if client.last_haircut:
            next_date = client.last_haircut + timedelta(days=client.interval_days)
            remaining_days = (next_date - today).days
            logging.info(f"[Client: {client.name}] remaining_days = {remaining_days}")
            if remaining_days == 1:
                msg = f"مرحباً {client.name}! تذكير: موعد حلاقتك غدًا."
                logging.info(f"--> Sending reminder to {client.phone} with message: {msg}")
                #from twilio_utils import send_reminder_message
                sid = send_reminder_message(client.phone, msg)
                logging.info(f"--> Message sent! SID: {sid}")
    logging.info("=== [check_and_send_reminders] Finished ===")

@main.route("/edit/<phone>", methods=["GET", "POST"])
def edit_client(phone):
    client = Client.query.filter_by(phone=phone).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        new_phone = request.form.get("phone", "").strip()
        date_str = request.form.get("last_haircut", "").strip()
        interval_days = request.form.get("interval_days", "").strip()
        barber_name = request.form.get("barber_name", "").strip()
        haircut_desc = request.form.get("haircut_desc", "").strip()

        if not (name and new_phone and date_str and interval_days and barber_name):
            flash("يرجى ملء جميع الحقول المطلوبة", "error")
            return redirect(url_for("main.edit_client", phone=phone))

        if not validate_phone(new_phone):
            flash("رقم الهاتف غير صالح!", "error")
            return redirect(url_for("main.edit_client", phone=phone))

        valid_date = validate_date(date_str)
        if not valid_date:
            flash("تاريخ الحلاقة غير صالح!", "error")
            return redirect(url_for("main.edit_client", phone=phone))

        try:
            interval_val = int(interval_days)
        except ValueError:
            flash("عدد الأيام يجب أن يكون رقمًا صحيحًا", "error")
            return redirect(url_for("main.edit_client", phone=phone))

        # تحديث الحقول الأساسية
        client.name = name
        client.phone = new_phone
        client.last_haircut = datetime.strptime(valid_date, "%Y-%m-%d").date()
        client.interval_days = interval_val
        client.haircut_description = haircut_desc if haircut_desc else "غير محدد"

        # ربط client ب barber_id إن وجد حلاق بنفس الاسم
        barber = Barber.query.filter_by(name=barber_name).first()
        if barber:
            client.barber_id = barber.id
        else:
            # لو ما لقيناش حلاق بنفس الاسم، ممكن نخلي barber_id = None أو نتجاهل
            client.barber_id = None

        # تعامل مع الصورة الجديدة
        uploaded_file = request.files.get("haircut_image")
        if uploaded_file and uploaded_file.filename != "":
            filename = secure_filename(uploaded_file.filename)
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
            uploaded_file.save(upload_path)
            client.haircut_image = filename

        db.session.commit()
        flash("تم تحديث بيانات العميل بنجاح!", "success")
        return redirect(url_for("main.index"))

    # GET: عرض النموذج ببيانات العميل الحالية
    return render_template("edit_client.html", client=client)

#def check_whatsapp():
    phone = "1065766357"
    msg = "مرحباً! هذه رسالة تجربة عبر WhatsApp."
    #sid = send_reminder_message(phone, msg)
    print(f"Message SID: {sid}")


@main.route("/barbers_kpi")
def barbers_kpi():
    from sqlalchemy import func, distinct

    # Query each Barber’s: barber_id, barber_name, #haircuts, #distinct clients, and average rating
    results = (
        db.session.query(
            Barber.id.label("barber_id"),
            Barber.name.label("barber_name"),
            func.count(Haircut.id).label("num_haircuts"),
            func.count(distinct(Haircut.client_id)).label("num_clients"),
            func.avg(Haircut.rating).label("avg_rating")
        )
        .join(Haircut, Haircut.barber_id == Barber.id)
        # If you want EVERY barber, even those with 0 haircuts, use .outerjoin(...) instead
        .group_by(Barber.id, Barber.name)
        .all()
    )

    # Now each row has: .barber_id, .barber_name, .num_haircuts, .num_clients, .avg_rating
    return render_template("barbers_kpi.html", data=results)



@main.route("/add_barber", methods=["GET", "POST"])
def add_barber():
    if request.method == "POST":
        barber_name = request.form.get("barber_name", "").strip()
        if not barber_name:
            flash("يرجى إدخال اسم الحلاق", "error")
            return redirect(url_for("main.add_barber"))

        existing_barber = Barber.query.filter_by(name=barber_name).first()
        if existing_barber:
            flash("هذا الحلاق موجود مسبقًا!", "error")
            return redirect(url_for("main.add_barber"))

        new_barber = Barber(name=barber_name)
        db.session.add(new_barber)
        db.session.commit()

        flash("تمت إضافة الحلاق بنجاح!", "success")
        return redirect(url_for("main.index"))

    return render_template("add_barber.html")
@main.route("/add_haircut/<int:client_id>", methods=["POST"])
def add_haircut(client_id):
    client = Client.query.get_or_404(client_id)

    # Create the haircut row
    new_haircut = Haircut(
        client_id=client.id,
        barber_id=client.barber_id,
        date=datetime.utcnow(),
        price=50.0
    )
    db.session.add(new_haircut)

    # Update the client's 'last_haircut'
    client.last_haircut = datetime.utcnow().date()
    db.session.commit()

    flash("تمت إضافة حلاقة جديدة!", "success")
    return redirect(url_for("main.index"))

@main.route("/change_barber/<int:client_id>", methods=["GET", "POST"])
def change_barber(client_id):
    client = Client.query.get_or_404(client_id)
    
    if request.method == "POST":
        # Get the new barber_id from the form
        new_barber_id = request.form.get("new_barber_id")
        if not new_barber_id:
            flash("يرجى اختيار الحلاق من القائمة", "error")
            return redirect(url_for("main.change_barber", client_id=client_id))

        # Convert to int and verify barber exists
        new_barber_id = int(new_barber_id)
        new_barber = Barber.query.get(new_barber_id)
        if not new_barber:
            flash("الحلاق المختار غير موجود", "error")
            return redirect(url_for("main.change_barber", client_id=client_id))
        
        # Update the client record
        client.barber_id = new_barber_id
        db.session.commit()
        
        flash(f"تم تغيير الحلاق للعميل {client.name} بنجاح!", "success")
        return redirect(url_for("main.index"))
    
    # GET request: render a form with a list of barbers
    all_barbers = Barber.query.all()
    return render_template("change_barber.html", client=client, barbers=all_barbers)
@main.route("/client/<int:client_id>")
def client_profile(client_id):
    client = Client.query.get_or_404(client_id)
    return render_template("client_profile.html", client=client)

@main.route("/landing")
def landing():
    """Displays a 'dashboard' landing page with date, total clients, monthly new, monthly returning, etc."""
    from datetime import datetime
    from sqlalchemy import func, extract

    # 1) اجلب التاريخ الحالي
    now = datetime.now()
    day_of_month = now.day                # 1..31
    day_of_week_index = now.weekday()     # Monday=0..Sunday=6
    # بإمكانك استخدام مكتبة calendar للحصول على الاسم العربي/الإنجليزي لليوم
    # أو تستخدم قاموس:
    days_ar = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    # لكن انتبه لـ weekday() يبدأ من الاثنين=0. قد تضطر لإزاحة أو إعادة ترتيب القائمة.
    day_of_week = days_ar[day_of_week_index]

    # اسم الشهر
    months_ar = ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
                 "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
    month_name = months_ar[now.month - 1]

    # 2) العدد الكلي للعملاء
    total_clients = Client.query.count()

    # 3) العملاء الجدد لهذا الشهر
    current_month = now.month
    current_year  = now.year
    monthly_new_clients = Client.query.filter(
        extract('month', Client.created_at) == current_month,
        extract('year', Client.created_at) == current_year
    ).count()

    # 4) العملاء العائدون لهذا الشهر
    returning_clients_query = Client.query.join(Haircut).filter(
    extract('month', Haircut.date) == current_month,
    extract('year', Haircut.date) == current_year,
    (extract('month', Client.created_at) < current_month) |
    (db.session.query(func.count(Haircut.id)).filter(Haircut.client_id == Client.id).scalar() > 1)
)

    monthly_returning_clients = returning_clients_query.distinct(Client.id).count()

    # 5) لعرض أفضل الحلاقين في آخر 30 يومًا (إن أردت إبقائها)
    from datetime import timedelta
    thirty_days_ago = now - timedelta(days=30)
    top_barbers = (
        db.session.query(
            Barber.name.label("barber_name"),
            func.count(Haircut.id).label("haircut_count")
        )
        .join(Haircut, Haircut.barber_id == Barber.id)
        .filter(Haircut.date >= thirty_days_ago)
        .group_by(Barber.name)
        .order_by(func.count(Haircut.id).desc())
        .limit(5)
        .all()
    )

    # 6) توزيع الأيام (لو أردت رسمه)
    day_of_week_counts = (
        db.session.query(
            func.strftime('%w', Haircut.date).label('dow'),
            func.count(Haircut.id)
        )
        .filter(Haircut.date >= thirty_days_ago)
        .group_by('dow')
        .all()
    )
    dow_map = {str(i): 0 for i in range(7)}
    for dow, cnt in day_of_week_counts:
        dow_map[dow] = cnt

    # 7) اتجاه العملاء الجدد (6 أشهر)
    six_months_ago = now - timedelta(days=6*30)
    monthly_trend = (
        db.session.query(
            extract('year', Client.created_at).label('yr'),
            extract('month', Client.created_at).label('mo'),
            func.count(Client.id).label('new_count')
        )
        .filter(Client.created_at >= six_months_ago)
        .group_by('yr', 'mo')
        .order_by('yr', 'mo')
        .all()
    )
    months_labels = []
    new_counts = []
    for yr, mo, new_count in monthly_trend:
        label = f"{int(mo)}/{int(yr)}"
        months_labels.append(label)
        new_counts.append(int(new_count))

    return render_template(
        "landing.html",
        # معلومات التاريخ
        day_of_month=day_of_month,
        day_of_week=day_of_week,
        month_name=month_name,
        # معلومات العملاء
        total_clients=total_clients,
        monthly_new_clients=monthly_new_clients,
        monthly_returning_clients=monthly_returning_clients,
        # الباقي (للرسم)
        top_barbers=top_barbers,
        dow_map=dow_map,
        months_labels=months_labels,
        new_counts=new_counts
    )



    
@main.route("/analysis")
def analysis():
    """
    Displays additional analyses:
       1) Average time between visits
       2) Most frequent clients
       3) Average feedback (rating)
    """

    # 1) Average Time Between Visits
    overall_gaps = []
    all_clients = Client.query.all()

    for client in all_clients:
        sorted_hc = sorted(client.haircuts, key=lambda h: h.date)
        if len(sorted_hc) > 1:
            day_gaps = []
            for i in range(1, len(sorted_hc)):
                gap_days = (sorted_hc[i].date - sorted_hc[i - 1].date).days
                day_gaps.append(gap_days)
            client_avg = sum(day_gaps) / len(day_gaps)
            overall_gaps.append(client_avg)

    if overall_gaps:
        avg_time_between_visits = round(sum(overall_gaps) / len(overall_gaps), 1)
    else:
        avg_time_between_visits = 0

    # 2) Most Frequent Clients
    most_frequent = (
        db.session.query(
            Client.name,
            func.count(Haircut.id).label("num_haircuts")
        )
        .join(Haircut, Haircut.client_id == Client.id)
        .group_by(Client.id, Client.name)
        .order_by(func.count(Haircut.id).desc())
        .limit(5)
        .all()
    )

    # 3) Average rating (feedback) from all haircuts
    avg_rating = db.session.query(func.avg(Haircut.rating)).scalar()
    if avg_rating is None:
        avg_rating = 0

    return render_template(
        "analysis.html",
        avg_time_between_visits=avg_time_between_visits,
        most_frequent=most_frequent,
        avg_rating=round(avg_rating, 1)
    )
import os

@main.route('/initialize_database/<username>')
def initialize_database(username):
    # إنشاء قاعدة بيانات خاصة لكل حلاق
    database_path = f"instance/{username}.sqlite"

    if not os.path.exists(database_path):
        db.create_all()
        flash(f"تم إنشاء قاعدة البيانات الخاصة بالحلاق: {username}", "success")
    else:
        flash("قاعدة البيانات موجودة بالفعل.", "info")

    return redirect(url_for('main.index'))

@main.route('/redirect_to_database')
def redirect_to_database():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول أولاً.', 'warning')
        return redirect(url_for('main.login'))

    user = User.query.get(session['user_id'])
    return redirect(url_for('initialize_database', username=user.username))
@main.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if not current_user.is_authenticated or not current_user.is_admin():
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))


    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        # ✅ Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('main.add_user'))

        # ✅ Create new user
        new_user = User(username=username)
        new_user.set_password(password)  # Hash the password
        new_user.role = role

        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully!', 'success')
        return redirect(url_for('main.index'))

    return render_template('add_user.html')
@main.route('/admin')
def admin():
    # Optionally, verify the user is authenticated and an admin
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Access denied!", "danger")
        return redirect(url_for('main.login'))
    return render_template("admin_dashboard.html")

@main.route('/make_admin/<username>')
def make_admin(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user.role = 'admin'
        db.session.commit()
        return f"{username} صار أدمن بنجاح!"
    else:
        return "لا يوجد مستخدم بهذا الاسم"
@main.route('/manager_dashboard')
def manager_dashboard():
    # For a manager, fetch his clients from his own database.
    clients = g.db_session.query(Client).all()
    return render_template('manager_dashboard.html', clients=clients)
