from mongoengine import (
    Document, StringField, DateTimeField, ReferenceField,
    IntField, DecimalField, SequenceField, CASCADE
)
from flask_login import UserMixin
from datetime import datetime
import uuid

class User(UserMixin, Document):
    meta = {'collection': 'users'}
    id = SequenceField(primary_key=True)
    username = StringField(max_length=64, unique=True, required=True)
    password_hash = StringField(max_length=255, required=True)

class Subscription(Document):
    meta = {'collection': 'subscriptions'}
    user = ReferenceField(User, reverse_delete_rule=CASCADE)
    plan = StringField(max_length=32, required=True)
    limit = IntField(default=10)
    expires_at = DateTimeField(required=True)

class PaymentRecord(Document):
    meta = {'collection': 'payments'}
    user = ReferenceField(User, reverse_delete_rule=CASCADE)
    payment_id = StringField(max_length=64, unique=True, required=True)
    status = StringField(max_length=32, required=True)
    amount = DecimalField(precision=2, required=True)
    created_at = DateTimeField(default=datetime.utcnow)

class QRCode(Document):
    meta = {'collection': 'qrcodes'}
    code = StringField(max_length=36, unique=True, default=lambda: str(uuid.uuid4()))
    target_url = StringField(max_length=2048, required=True)
    fill_color = StringField(max_length=7, default='#000000')
    back_color = StringField(max_length=7, default='#ffffff')
    created_at = DateTimeField(default=datetime.utcnow)
    user = ReferenceField(User, reverse_delete_rule=CASCADE)

class ScanEvent(Document):
    meta = {'collection': 'scanevents'}
    qr = ReferenceField(QRCode, reverse_delete_rule=CASCADE)
    timestamp = DateTimeField(default=datetime.utcnow)
    ip_address = StringField(max_length=45)
    city = StringField(max_length=128)
    country = StringField(max_length=128)
