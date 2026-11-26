"""Configuration centralisée. Tout se règle par variables d'environnement."""
import os

# Sécurité
API_KEY = os.getenv("SMS_API_KEY", "change-me")

# Serveur
HOST = os.getenv("SMS_HOST", "0.0.0.0")
PORT = int(os.getenv("SMS_PORT", "8000"))

# Envoyeur : "termux" | "modem" | "mock" (mock = test sans envoi réel)
SENDER_MODE = os.getenv("SMS_SENDER", "mock")

# Modem GSM (mode "modem")
SERIAL_PORT = os.getenv("SMS_SERIAL_PORT", "/dev/ttyUSB0")  # COM3 sous Windows
BAUDRATE = int(os.getenv("SMS_BAUDRATE", "115200"))

# Protection de la SIM
RATE_LIMIT_PER_MIN = int(os.getenv("SMS_RATE_LIMIT", "10"))  # SMS max / minute
MAX_RETRIES = int(os.getenv("SMS_MAX_RETRIES", "3"))
RETRY_DELAY_SEC = int(os.getenv("SMS_RETRY_DELAY", "30"))

# Base de données
DB_PATH = os.getenv("SMS_DB_PATH", "sms.db")
