import os
import io
import re
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from hmac import compare_digest
from urllib.parse import urlsplit

import requests
from flask import (
    Flask, render_template, request, redirect,
    url_for, send_file, abort
)
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import geoip2.database
from geoip2.errors import AddressNotFoundError
from mongoengine import connect

from config import Config
from models import (
    User, Subscription, PaymentRecord,
    QRCode as QRModel, ScanEvent
)

# ——— Настройка Flask ————————————————————————————————————————
app = Flask(__name__)
app.config.from_object(Config())
cfg = app.config

# Подключаем MongoDB
if not cfg['SECRET_KEY']:
    raise RuntimeError('Set SECRET_KEY or enable DEMO_MODE in .env.')

if cfg['DEMO_MODE']:
    from mongomock import MongoClient

    connect('qr_tracker_demo', host='mongodb://localhost', mongo_client_class=MongoClient)
else:
    connect(**cfg['MONGODB_SETTINGS'])

payments_enabled = bool(
    not cfg['DEMO_MODE']
    and cfg['APP_URL']
    and cfg['PAYMENT_API_URL']
    and cfg['PAYMENT_SERVICE_SECRET']
)

# Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# GeoIP
reader = None
if cfg.get('GEOIP_DB_PATH') and os.path.exists(cfg['GEOIP_DB_PATH']):
    reader = geoip2.database.Reader(cfg['GEOIP_DB_PATH'])

@login_manager.user_loader
def load_user(user_id):
    return User.objects(id=int(user_id)).first()

# ——— РЕГИСТРАЦИЯ / АУТЕНТИФИКАЦИЯ ——————————————————————————————
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        raw_pw   = request.form['password']
        if not 1 <= len(username) <= 64 or not 1 <= len(raw_pw) <= 1024:
            abort(400)

        if User.objects(username=username).first():
            return 'Пользователь уже существует', 400

        password_hash = generate_password_hash(raw_pw)
        user = User(username=username, password_hash=password_hash).save()
        login_user(user)
        return redirect(url_for('create_form'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user     = User.objects(username=request.form['username']).first()
        raw_pw   = request.form['password']

        if user and check_password_hash(user.password_hash, raw_pw):
            login_user(user)
            return redirect(url_for('create_form'))

        return 'Неверные имя или пароль', 400

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# ——— ОПЛАТА через внешний микросервис —————————————————————————————
@app.route('/subscribe', methods=['GET', 'POST'])
@login_required
def subscribe():
    if not payments_enabled:
        abort(404)
    if request.method == 'GET':
        return render_template('subscribe.html')

    payload = {
        "service":  "track-qr",
        "user_id":  str(current_user.id),
        "amount":   "200.00",
        "return_url": cfg['APP_URL'] + "/subscribe"
    }
    resp = requests.post(
        f"{cfg['PAYMENT_API_URL']}/payments/create",
        json=payload,
        timeout=15
    )
    resp.raise_for_status()
    data = resp.json()

    PaymentRecord(
        user=current_user,
        payment_id=data['payment_id'],
        status=data['status'],
        amount=Decimal('200.00')
    ).save()

    return redirect(data['confirmation_url'])


@app.route('/payment/notification', methods=['POST'])
def payment_notification():
    if not payments_enabled:
        abort(404)
    token = request.headers.get('X-Service-Secret', '')
    if not compare_digest(token.encode(), cfg['PAYMENT_SERVICE_SECRET'].encode()):
        abort(403)

    data   = request.get_json()
    record = PaymentRecord.objects(payment_id=data['payment_id']).first()
    if not record:
        return '', 404

    record.status = data['status']
    record.save()

    if data['status'] == 'succeeded':
        user = record.user
        now  = datetime.utcnow()
        end  = datetime(now.year, now.month, 1) + timedelta(days=32)
        exp  = datetime(end.year, end.month, 1)

        sub = Subscription.objects(user=user).first()
        if sub and sub.expires_at > now:
            sub.update(expires_at=exp)
        else:
            Subscription(
                user=user,
                plan='basic',
                limit=10,
                expires_at=exp
            ).save()

    return '', 200

# ——— Основной функционал QR ——————————————————————————————————————
@app.route('/', methods=['GET'])
def create_form():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    codes = QRModel.objects(user=current_user).order_by('-created_at')
    return render_template('create.html', codes=codes)


@app.route('/create', methods=['POST'])
@login_required
def create_qr():
    sub = Subscription.objects(user=current_user).first()
    if payments_enabled and (not sub or sub.expires_at < datetime.utcnow()):
        return redirect(url_for('subscribe'))

    start = datetime(datetime.utcnow().year, datetime.utcnow().month, 1)
    count = QRModel.objects(
        user=current_user, created_at__gte=start
    ).count()
    limit = sub.limit if payments_enabled else 10
    if count >= limit:
        return 'Лимит QR-кодов исчерпан', 403

    target = request.form['target_url'].strip()
    fg     = request.form.get('fill_color', '#000000')
    bg     = request.form.get('back_color', '#ffffff')
    try:
        parsed = urlsplit(target)
        valid_url = parsed.scheme in {'http', 'https'} and parsed.hostname and not parsed.username
    except ValueError:
        valid_url = False
    if not valid_url or len(target) > 2048 or any(char.isspace() for char in target):
        abort(400, 'Укажите корректный HTTP(S)-адрес.')
    if not all(re.fullmatch(r'#[0-9a-fA-F]{6}', color) for color in (fg, bg)):
        abort(400, 'Укажите цвета в формате HEX.')

    qr = QRModel(
        target_url=target,
        fill_color=fg,
        back_color=bg,
        user=current_user
    ).save()

    qr_img = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    base_url = (cfg['APP_URL'] or request.host_url).rstrip('/')
    qr_img.add_data(base_url + url_for('track', code=qr.code))
    qr_img.make(fit=True)
    pil = qr_img.make_image(fill_color=fg, back_color=bg).convert('RGB')

    buf = io.BytesIO()
    pil.save(buf, 'PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png',
                     download_name=f'{qr.code}.png')


@app.route('/<code>', methods=['GET'])
def track(code):
    qr = QRModel.objects(code=code).first() or abort(404)
    ip = request.remote_addr
    city = country = None
    if reader and ip and not cfg['DEMO_MODE']:
        try:
            geo = reader.city(ip)
            city    = geo.city.name
            country = geo.country.name
        except (AddressNotFoundError, ValueError):
            pass

    ScanEvent(
        qr=qr,
        ip_address=ip if cfg['STORE_SCAN_IP'] and not cfg['DEMO_MODE'] else None,
        city=city,
        country=country
    ).save()

    return redirect(qr.target_url)


@app.route('/stats/<code>', methods=['GET'])
@login_required
def stats(code):
    qr     = QRModel.objects(code=code, user=current_user).first() or abort(404)
    events = list(ScanEvent.objects(qr=qr).order_by('timestamp'))
    daily_counts = Counter(event.timestamp.strftime('%Y-%m-%d') for event in events)
    return render_template(
        'stats.html', qr=qr, events=events, total=len(events), daily_counts=daily_counts
    )


if __name__ == '__main__':
    app.run()
