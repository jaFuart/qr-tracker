# config.py
import os
from secrets import token_hex

from dotenv import load_dotenv

load_dotenv()

class Config:
    DEMO_MODE = os.getenv('DEMO_MODE', 'false').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY') or (token_hex(32) if DEMO_MODE else None)

    # базовый URI (только хосты + опции replicaSet/authSource)
    MONGODB_URI  = os.getenv('MONGODB_URI') or 'mongodb://127.0.0.1:27017'
    # логическая база для этого сервиса
    MONGODB_DB   = os.getenv('MONGODB_DB') or 'qr_tracker'
    # учётка, созданная для этой базы
    MONGODB_USER = os.getenv('MONGODB_USER') or None
    MONGODB_PASS = os.getenv('MONGODB_PASS') or None

    MONGODB_SETTINGS = {
        'db':                  MONGODB_DB,
        'host':                MONGODB_URI,
        'username':            MONGODB_USER,
        'password':            MONGODB_PASS,
        'authentication_source': MONGODB_DB,
    }

    APP_URL               = os.getenv('APP_URL')
    PAYMENT_API_URL       = os.getenv('PAYMENT_API_URL')
    PAYMENT_SERVICE_SECRET= os.getenv('PAYMENT_SERVICE_SECRET')
    GEOIP_DB_PATH = os.getenv('GEOIP_DB_PATH')
    STORE_SCAN_IP = os.getenv('STORE_SCAN_IP', 'false').lower() == 'true'
