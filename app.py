import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Konfigurasi logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Definisi base class untuk SQLAlchemy
class Base(DeclarativeBase):
    pass

# Inisialisasi database
db = SQLAlchemy(model_class=Base)

# Membuat aplikasi Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "hermes_quantum_ai_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Diperlukan untuk url_for dengan https

# Konfigurasi database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///hermes_quantum.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inisialisasi database dengan aplikasi
db.init_app(app)

# Konfigurasi login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import model setelah definisi database
from models import User, Signal, Setting

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Import utilitas setelah setup aplikasi
from utils.telegram_bot import TelegramBot
from utils.market_analyzer import MarketAnalyzer
from utils.technical_indicators import TechnicalIndicators
from utils.chart_generator import ChartGenerator
from utils.ml_predictor import MLPredictor
from api.pocket_option import PocketOptionAPI

# Membuat objek telegram bot
telegram_bot = TelegramBot()

# Membuat objek market analyzer
market_analyzer = MarketAnalyzer()

# Membuat instance untuk Pocket Option API
pocket_option_api = PocketOptionAPI()

# Memastikan semua tabel database terbuat
with app.app_context():
    db.create_all()
    
    # Membuat admin default jika belum ada
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@hermesquantum.ai',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        logger.info("Admin default telah dibuat")
    
    # Membuat pengaturan default jika belum ada
    setting = Setting.query.first()
    if not setting:
        default_settings = Setting(
            telegram_token=os.environ.get("TELEGRAM_TOKEN", ""),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
            pocket_option_api_key=os.environ.get("POCKET_OPTION_API_KEY", ""),
            signal_time_before_candle=10,  # 10 detik sebelum candle
            min_confidence_threshold=75,   # minimal confidence 75%
            trading_timeframe="M1",        # default timeframe M1
            active_symbols="AUD/JPY,EUR/USD,GBP/USD,USD/JPY,USD/CAD",  # Simbol default
            active_status=True             # Aktif secara default
        )
        db.session.add(default_settings)
        db.session.commit()
        logger.info("Pengaturan default telah dibuat")
    else:
        # Update settings dengan environment variables jika ada
        if os.environ.get("TELEGRAM_TOKEN"):
            setting.telegram_token = os.environ.get("TELEGRAM_TOKEN")
        if os.environ.get("TELEGRAM_CHAT_ID"):
            setting.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        # Pastikan bot selalu aktif saat startup
        setting.active_status = True
        
        db.session.commit()
        logger.info("Pengaturan telah diperbarui dengan environment variables")
        
    # Inisialisasi market analyzer untuk keseluruhan aplikasi
    from utils.market_analyzer import MarketAnalyzer
    import flask
    
    # Menggunakan g untuk menyimpan market_analyzer
    market_analyzer = MarketAnalyzer()
    
    # Mulai analisis market jika bot aktif
    if setting and setting.active_status:
        try:
            market_analyzer.start_analysis(setting)
            logger.info("Bot analisis pasar dimulai secara otomatis")
        except Exception as e:
            logger.error(f"Error saat memulai bot analisis pasar: {str(e)}")

# Route untuk halaman utama
@app.route('/')
def index():
    return render_template('index.html')

# Route untuk login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Berhasil login!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Username atau password salah!', 'danger')
    
    return render_template('index.html')

# Route untuk logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Berhasil logout!', 'success')
    return redirect(url_for('index'))

# Route untuk dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    from datetime import datetime
    signals = Signal.query.order_by(Signal.created_at.desc()).limit(10).all()
    settings = Setting.query.first()
    
    # Pastikan status selalu aktif karena bot memang berjalan otomatis
    settings.active_status = True
    db.session.commit()
    
    # Jika bot belum dijalankan, jalankan sekarang
    try:
        if not market_analyzer.running:
            market_analyzer.start_analysis(settings)
            logger.info("Bot analisis pasar dimulai dari dashboard")
    except Exception as e:
        logger.error(f"Error saat memulai bot analisis pasar: {str(e)}")
        
    return render_template('dashboard.html', signals=signals, settings=settings, now=datetime.now())

# Route untuk pengaturan
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings = Setting.query.first()
    
    if request.method == 'POST':
        settings.telegram_token = request.form.get('telegram_token')
        settings.telegram_chat_id = request.form.get('telegram_chat_id')
        settings.pocket_option_api_key = request.form.get('pocket_option_api_key')
        settings.signal_time_before_candle = int(request.form.get('signal_time_before_candle'))
        settings.min_confidence_threshold = int(request.form.get('min_confidence_threshold'))
        settings.trading_timeframe = request.form.get('trading_timeframe')
        settings.active_symbols = request.form.get('active_symbols')
        settings.active_status = 'active_status' in request.form
        
        db.session.commit()
        
        # Memperbarui token telegram bot
        telegram_bot.set_token(settings.telegram_token)
        
        # Memperbarui API key untuk Pocket Option
        pocket_option_api.set_api_key(settings.pocket_option_api_key)
        
        flash('Pengaturan berhasil disimpan!', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', settings=settings)

# Route untuk start/stop bot
@app.route('/bot/toggle', methods=['POST'])
@login_required
def toggle_bot():
    settings = Setting.query.first()
    
    # Force status ke active jika kita ingin nonaktifkan (sehingga selalu aktif)
    if settings.active_status:
        # User mencoba untuk menonaktifkan tapi kita tetap aktifkan
        flash('Bot akan selalu aktif secara otomatis!', 'info')
    else:
        # User mencoba untuk mengaktifkan (memang selalu aktif)
        settings.active_status = True
        db.session.commit()
        
        # Jalankan market analyzer jika belum berjalan
        if not market_analyzer.running:
            market_analyzer.start_analysis(settings)
        
        flash('Bot telah aktif!', 'success')
    
    return redirect(url_for('dashboard'))

# Route untuk melihat detail sinyal
@app.route('/signal/<int:signal_id>')
@login_required
def signal_detail(signal_id):
    signal = Signal.query.get_or_404(signal_id)
    return render_template('signal_detail.html', signal=signal)

# Route API untuk mendapatkan sinyal terakhir
@app.route('/api/signals/latest', methods=['GET'])
@login_required
def get_latest_signals():
    signals = Signal.query.order_by(Signal.created_at.desc()).limit(5).all()
    signals_data = [{
        'id': signal.id,
        'symbol': signal.symbol,
        'direction': signal.direction,
        'confidence': signal.confidence,
        'executed_at': signal.executed_at,
        'created_at': signal.created_at,
        'result': signal.result
    } for signal in signals]
    
    return jsonify(signals_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
