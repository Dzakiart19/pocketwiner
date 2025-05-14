
import os
from datetime import timedelta

class Config:
    """Konfigurasi dasar untuk aplikasi."""
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'default_secret_key_change_this')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hermes_quantum.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Telegram Bot
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
    
    # Pocket Option API
    TWELVE_DATA_KEY = os.environ.get('TWELVE_DATA_KEY', '')
    
    # AI Model Settings
    MODEL_DIR = 'models'
    MIN_CONFIDENCE_THRESHOLD = 75
    
    # Trading Settings
    SIGNAL_TIME_BEFORE_CANDLE = 10
    DEFAULT_TIMEFRAME = 'M1'
    DEFAULT_SYMBOLS = 'AUD/JPY,EUR/USD,GBP/USD,USD/JPY,USD/CAD'
    
    # Chart Generation
    CHART_SAVE_PATH = 'static/charts'

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

config = config_by_name[os.environ.get('FLASK_ENV', 'production')]
