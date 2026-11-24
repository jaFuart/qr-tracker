# QR Tracker

Flask app for generating trackable QR codes and viewing scan analytics. The local demo uses an in-memory database and runs without payment credentials.

## Что можно попробовать

- Создать аккаунт и сгенерировать цветной QR-код для HTTP(S)-ссылки.
- Перейти по ссылке QR-кода и посмотреть счётчик, график по дням и список сканов.
- Проверить доступ к статистике. Она доступна только владельцу QR-кода.

## Локальный запуск

Понадобится Python 3.12. Создайте виртуальное окружение и активируйте его:

```bash
python -m venv .venv
source .venv/bin/activate
```

В PowerShell вместо второй команды используйте `.\.venv\Scripts\Activate.ps1`.

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python -m flask --app app run
```

В PowerShell для копирования файла можно использовать `Copy-Item .env.example .env`.

Откройте [http://127.0.0.1:5000](http://127.0.0.1:5000) и создайте аккаунт. URL в QR привязан к адресу, с которого открыт сервис. Для локальной проверки перейдите по ссылке в списке «Ваши QR-коды». Данные демо сбрасываются при перезапуске.

## Конфигурация

Чтобы сохранять данные между запусками, установите `DEMO_MODE=false`, задайте собственный `SECRET_KEY` и укажите параметры MongoDB в `.env`. Определение города и страны можно включить, указав путь к своей базе GeoIP в `GEOIP_DB_PATH`. Запись IP-адресов выключена по умолчанию.

Приложение поддерживает внешний платёжный сервис. Маршруты оплаты включаются при совместной настройке `APP_URL`, `PAYMENT_API_URL`, `PAYMENT_SERVICE_SECRET` и выключенном деморежиме.
