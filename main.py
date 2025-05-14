import logging
from app import app, db, market_analyzer, telegram_bot
from models import Setting
import os

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Fungsi untuk memastikan bot dijalankan pada startup
def ensure_bot_active():
    with app.app_context():
        # Inisialisasi setting jika belum ada
        settings = Setting.query.first()
        if not settings:
            # Buat setting baru dengan nilai default dan status aktif
            settings = Setting(
                telegram_token=os.environ.get('TELEGRAM_TOKEN', ''),
                telegram_chat_id=os.environ.get('TELEGRAM_CHAT_ID', ''),
                active_status=True,
                trading_timeframe="M1",  # Fokus pada timeframe M1
                active_symbols="AUD/JPY,EUR/USD,GBP/USD,USD/JPY,USD/CAD"
            )
            db.session.add(settings)
            db.session.commit()
            logging.info("Setting baru dibuat dengan status aktif")
        else:
            # Selalu set status ke aktif
            settings.active_status = True
            db.session.commit()
            logging.info("Setting diperbarui dengan status aktif")
        
        # Mulai bot market analyzer jika belum berjalan
        try:
            if not market_analyzer.running:
                market_analyzer.start_analysis(settings)
                logging.info("Bot analisis pasar dimulai pada startup aplikasi")
            
            # Mulai bot Telegram listener untuk menanggapi perintah
            telegram_bot.set_token(settings.telegram_token)
            telegram_bot.start_listening()
            logging.info("Bot Telegram listener dimulai")
        except Exception as e:
            logging.error(f"Error saat memulai bot: {str(e)}")

# Jalankan fungsi untuk memastikan bot aktif
ensure_bot_active()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
