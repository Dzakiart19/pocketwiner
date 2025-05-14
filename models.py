from datetime import datetime
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Signal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(32), nullable=False)  # Misalnya: AUD/JPY OTC
    timeframe = db.Column(db.String(8), nullable=False)  # Misalnya: M1
    direction = db.Column(db.String(8), nullable=False)  # BUY atau SELL
    executed_at = db.Column(db.DateTime, nullable=False)  # Waktu eksekusi (open candle)
    sent_at = db.Column(db.DateTime, nullable=False)  # Waktu sinyal dikirim
    
    # Market snapshot data
    volatility = db.Column(db.Float)  # Volatilitas (MPI)
    strength_by_volume = db.Column(db.Float)  # Dalam persentase
    price_pressure = db.Column(db.Float)  # Dalam persentase
    microtrend_structure = db.Column(db.String(64))  # Higher low, Lower high, dll
    
    # Technical analysis data
    rsi = db.Column(db.Float)  # Nilai RSI
    rsi_analysis = db.Column(db.String(128))  # Analisis RSI
    macd = db.Column(db.String(128))  # Informasi MACD
    ema50 = db.Column(db.String(128))  # Analisis EMA50
    bollinger_bands = db.Column(db.String(128))  # Analisis Bollinger Bands
    volume_analysis = db.Column(db.String(128))  # Analisis Volume
    candle_pattern = db.Column(db.String(64))  # Pola candle yang terdeteksi
    
    # AI data
    confidence = db.Column(db.Float)  # Nilai kepercayaan (dalam persentase)
    win_rate_prediction = db.Column(db.Float)  # Prediksi win rate (dalam persentase)
    risk_level = db.Column(db.String(16))  # Sangat Rendah, Rendah, Sedang, Tinggi, Sangat Tinggi
    
    # Chart data
    chart_url = db.Column(db.String(256))  # URL ke gambar grafik analisis
    
    # Result data
    result = db.Column(db.String(8), nullable=True)  # WIN, LOSS, DRAW, atau None jika belum ada hasil
    open_price = db.Column(db.Float, nullable=True)  # Harga saat open
    close_price = db.Column(db.Float, nullable=True)  # Harga saat close
    post_analysis = db.Column(db.Text, nullable=True)  # Analisis pasca-eksekusi
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Signal {self.symbol} {self.direction} at {self.executed_at}>'

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_token = db.Column(db.String(128))
    telegram_chat_id = db.Column(db.String(64))
    pocket_option_api_key = db.Column(db.String(128))
    signal_time_before_candle = db.Column(db.Integer, default=10)  # Waktu dalam detik sebelum candle
    min_confidence_threshold = db.Column(db.Integer, default=75)  # Nilai minimum kepercayaan dalam persentase
    trading_timeframe = db.Column(db.String(8), default="M1")  # Default timeframe M1
    active_symbols = db.Column(db.Text, default="AUD/JPY,EUR/USD,GBP/USD,USD/JPY,USD/CAD")
    active_status = db.Column(db.Boolean, default=False)  # Status aktif bot
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Setting {self.id}>'

    def get_symbols_list(self):
        """Mengembalikan daftar simbol aktif sebagai list."""
        return [symbol.strip() for symbol in self.active_symbols.split(",")]
