from mongoengine import connect
from config import Config

if __name__ == '__main__':
    # Подключаемся к Mongo
    cfg = Config()
    connect(**cfg.MONGODB_SETTINGS)

    # Если нужны индексы — можно вызвать ensure_indexes для каждой модели:
    from models import User, QRCode, PaymentRecord
    User.ensure_indexes()
    QRCode.ensure_indexes()
    PaymentRecord.ensure_indexes()

    print("✅ MongoDB подключена и индексы созданы.")
