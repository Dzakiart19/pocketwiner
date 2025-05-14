import os
import logging
import requests
import io
import threading
import time
from PIL import Image
import aiohttp
import asyncio
from datetime import datetime, timedelta

class TelegramBot:
    """
    Kelas untuk mengelola interaksi dengan Telegram Bot API
    """
    
    def __init__(self, token=None):
        """
        Inisialisasi bot Telegram
        
        Args:
            token (str, optional): Token API Telegram. Jika None, akan mencoba mengambil dari env var TELEGRAM_TOKEN
        """
        self.token = token or os.environ.get("TELEGRAM_TOKEN", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.logger = logging.getLogger(__name__)
        self.update_offset = 0
        self.listening = False
        self.listener_thread = None
        
    def start_listening(self):
        """Mulai thread untuk menerima dan merespon pesan dari pengguna."""
        if self.listening:
            return False
            
        if not self.token:
            self.logger.error("Token Telegram tidak diatur, tidak dapat memulai listener")
            return False
            
        self.listening = True
        self.listener_thread = threading.Thread(target=self._listen_for_messages)
        self.listener_thread.daemon = True
        self.listener_thread.start()
        self.logger.info("Bot Telegram mulai mendengarkan pesan")
        return True
        
    def stop_listening(self):
        """Hentikan thread listener."""
        self.listening = False
        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
            self.logger.info("Bot Telegram berhenti mendengarkan pesan")
            
    def _listen_for_messages(self):
        """Thread worker yang mendengarkan dan merespon pesan."""
        while self.listening:
            try:
                updates = self._get_updates()
                if updates.get("ok") and updates.get("result"):
                    for update in updates["result"]:
                        if self.update_offset <= update["update_id"]:
                            self.update_offset = update["update_id"] + 1
                            
                        # Proses pesan atau callback
                        if "message" in update:
                            self._process_message(update["message"])
                            
                # Tunggu sebelum polling lagi        
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error dalam listener Telegram: {str(e)}")
                time.sleep(5)  # Pause sebelum mencoba lagi
                
    def _get_updates(self):
        """Mengambil updates dari Telegram API."""
        url = f"{self.base_url}/getUpdates"
        params = {"offset": self.update_offset, "timeout": 30}
        
        try:
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            self.logger.error(f"Error saat mengambil updates: {str(e)}")
            return {"ok": False, "error": str(e)}
            
    def _process_message(self, message):
        """
        Memproses pesan masuk dan mengirim respons yang sesuai
        
        Args:
            message (dict): Pesan dari update Telegram
        """
        if "text" not in message:
            return
            
        chat_id = message["chat"]["id"]
        text = message["text"]
        
        # Cek apakah pesan adalah perintah
        if text.startswith("/"):
            command = text.split()[0].lower()
            
            if command == "/start":
                self._send_welcome_message(chat_id)
            elif command == "/help":
                self._send_help_message(chat_id)
            elif command == "/status":
                self._send_status_message(chat_id)
            elif command == "/about":
                self._send_about_message(chat_id)
                
    def _send_welcome_message(self, chat_id):
        """Kirim pesan selamat datang."""
        message = """
<b>🌟 Selamat Datang di HermesQuantum AI Bot! 🌟</b>

Bot ini akan memberikan sinyal trading presisi menggunakan teknologi AI untuk pasar Pocket Option OTC.

Tekan /help untuk melihat perintah yang tersedia.
        """
        self.send_message(chat_id, message.strip())
        
    def _send_help_message(self, chat_id):
        """Kirim pesan bantuan dengan daftar perintah."""
        message = """
<b>📚 Perintah HermesQuantum AI Bot:</b>

/start - Memulai bot dan menerima pesan sambutan
/help - Menampilkan daftar perintah yang tersedia
/status - Melihat status bot dan statistik sinyal
/about - Informasi tentang HermesQuantum AI

Bot ini akan otomatis mengirimkan sinyal trading dengan timeframe M1 ketika peluang trading terdeteksi.
        """
        self.send_message(chat_id, message.strip())
        
    def _send_status_message(self, chat_id):
        """Kirim pesan status bot."""
        message = """
<b>📊 Status HermesQuantum AI Bot:</b>

✅ Bot Status: <b>Aktif</b>
📈 Trading Timeframe: <b>M1 (1 menit)</b>
🔍 Simbol yang Dianalisis: <b>AUD/JPY, EUR/USD, GBP/USD, USD/JPY, USD/CAD</b>
⚙️ Akurasi Model: <b>High Precision</b>
        """
        self.send_message(chat_id, message.strip())
        
    def _send_about_message(self, chat_id):
        """Kirim pesan tentang bot."""
        message = """
<b>ℹ️ Tentang HermesQuantum AI Bot:</b>

HermesQuantum AI adalah sistem sinyal trading canggih yang menggabungkan analisis teknikal dan machine learning untuk menghasilkan sinyal trading presisi tinggi.

Bot ini dirancang untuk pasar OTC Pocket Option dengan fokus pada timeframe M1, dan menggunakan algoritma khusus untuk mendeteksi momentum pasar terbaik.

<b>Fitur utama:</b>
• Analisis otomatis 5 pasangan mata uang utama
• Analisis konfluensi teknikal komprehensif
• Skor kekuatan sinyal berbasis AI
• Grafik analisis dengan anotasi otomatis
        """
        self.send_message(chat_id, message.strip())
        
    def set_token(self, token):
        """
        Mengatur token Telegram
        
        Args:
            token (str): Token API Telegram baru
        """
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
    def send_message(self, chat_id, text, parse_mode="HTML"):
        """
        Mengirim pesan teks ke chat Telegram
        
        Args:
            chat_id (str): ID chat tujuan
            text (str): Isi pesan yang akan dikirim
            parse_mode (str, optional): Mode parsing pesan. Default ke HTML
            
        Returns:
            dict: Respons dari API Telegram
        """
        if not self.token:
            self.logger.error("Token Telegram tidak diatur")
            return {"ok": False, "error": "Token Telegram tidak diatur"}
            
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, data=data)
            response_json = response.json()
            
            if not response_json.get("ok"):
                self.logger.error(f"Gagal mengirim pesan: {response_json}")
            
            return response_json
        except Exception as e:
            self.logger.error(f"Error saat mengirim pesan: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def send_photo(self, chat_id, photo_path, caption="", parse_mode="HTML"):
        """
        Mengirim foto ke chat Telegram
        
        Args:
            chat_id (str): ID chat tujuan
            photo_path (str): Path ke file foto yang akan dikirim
            caption (str, optional): Teks caption untuk foto
            parse_mode (str, optional): Mode parsing caption. Default ke HTML
            
        Returns:
            dict: Respons dari API Telegram
        """
        if not self.token:
            self.logger.error("Token Telegram tidak diatur")
            return {"ok": False, "error": "Token Telegram tidak diatur"}
            
        url = f"{self.base_url}/sendPhoto"
        
        try:
            with open(photo_path, "rb") as photo_file:
                files = {"photo": photo_file}
                data = {
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": parse_mode
                }
                
                response = requests.post(url, data=data, files=files)
                response_json = response.json()
                
                if not response_json.get("ok"):
                    self.logger.error(f"Gagal mengirim foto: {response_json}")
                
                return response_json
        except Exception as e:
            self.logger.error(f"Error saat mengirim foto: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def send_chart_with_signal(self, chat_id, signal, chart_image):
        """
        Mengirim sinyal trading dengan chart ke Telegram
        
        Args:
            chat_id (str): ID chat tujuan
            signal (Signal): Objek sinyal trading
            chart_image (bytes/str): Gambar chart dalam bentuk bytes atau path ke file
            
        Returns:
            dict: Respons dari API Telegram
        """
        # Format pesan sinyal
        message = self._format_signal_message(signal)
        
        # Kirim gambar chart dengan caption
        if isinstance(chart_image, str):
            # Jika chart_image adalah path file
            return self.send_photo(chat_id, chart_image, caption=message)
        else:
            # Jika chart_image adalah bytes
            if not self.token:
                self.logger.error("Token Telegram tidak diatur")
                return {"ok": False, "error": "Token Telegram tidak diatur"}
                
            url = f"{self.base_url}/sendPhoto"
            
            try:
                # Buat file-like object dari bytes
                photo_data = io.BytesIO(chart_image)
                photo_data.name = "chart.png"
                
                files = {"photo": photo_data}
                data = {
                    "chat_id": chat_id,
                    "caption": message,
                    "parse_mode": "HTML"
                }
                
                response = requests.post(url, data=data, files=files)
                response_json = response.json()
                
                if not response_json.get("ok"):
                    self.logger.error(f"Gagal mengirim foto: {response_json}")
                
                return response_json
            except Exception as e:
                self.logger.error(f"Error saat mengirim foto: {str(e)}")
                return {"ok": False, "error": str(e)}
    
    def send_trade_result(self, chat_id, signal):
        """
        Mengirim hasil trade ke Telegram
        
        Args:
            chat_id (str): ID chat tujuan
            signal (Signal): Objek sinyal trading yang sudah memiliki hasil
            
        Returns:
            dict: Respons dari API Telegram
        """
        # Format pesan hasil trade
        message = self._format_result_message(signal)
        
        # Kirim pesan hasil
        return self.send_message(chat_id, message)
    
    def _format_signal_message(self, signal):
        """
        Format pesan sinyal trading sesuai format yang diinginkan
        
        Args:
            signal (Signal): Objek sinyal trading
            
        Returns:
            str: Pesan terformat
        """
        # Convert datetime objects to Indonesia time
        exec_time = signal.executed_at.strftime("%H:%M:%S")
        sent_time = signal.sent_at.strftime("%H:%M:%S")
        
        # Format arah trading dengan emoji modern
        direction_emoji = "🚀" if signal.direction == "BUY" else "🔻"
        
        message = f"""
🤖 <b>[HERMES QUANTUM AI MASTER]</b> 🤖
━━━━━━━━━━━━━━━━━━
🎯 {signal.symbol} OTC | ⏱ {signal.timeframe} | 📍 {signal.direction} {direction_emoji}
⚡️ Eksekusi: {exec_time} WIB
🔄 Update: {sent_time} WIB (presisi adaptif)

📊 <b>MARKET SNAPSHOT</b> 🎯
🌋 Volatilitas: {signal.volatility}/10
💪 Volume Power: {signal.strength_by_volume}% {"🟢" if signal.direction == "BUY" else "🔴"}
💫 Price Momentum: {signal.price_pressure}% (3m)
📈 Microtrend: {signal.microtrend_structure}
⚡️ Latency: Real-time Execution

🔬 <b>SUPER TEKNIKAL</b> 📈
🎯 RSI: {signal.rsi} ({signal.rsi_analysis})
💫 MACD: {signal.macd}
📊 EMA50: {signal.ema50}
🎯 BB: {signal.bollinger_bands}
📈 Volume: {signal.volume_analysis}
🕯 Pattern: "{signal.candle_pattern}"
🎯 Sentimen: {"🟢 STRONG BUY" if signal.direction == "BUY" else "🔴 STRONG SELL"}

🤖 <b>AI POWER SCORE: {signal.confidence}%</b> 🎯
💫 Engine: XGBoost HyperQuantum
🎯 WinRate: {signal.win_rate_prediction}%
⚠️ Risk Level: {signal.risk_level}

📊 <b>MASTER CHART</b> 📈
• 🎯 Multi-Indikator Overlay
• 📊 Smart Pattern Detection
• 💫 Entry Zone Mapping
━━━━━━━━━━━━━━━━━━
        """
        
        return message.strip()
    
    def _format_result_message(self, signal):
        """
        Format pesan hasil trade
        
        Args:
            signal (Signal): Objek sinyal trading dengan hasil
            
        Returns:
            str: Pesan terformat
        """
        # Emoji hasil
        result_emoji = "✅" if signal.result == "WIN" else "❌" if signal.result == "LOSS" else "⚠️"
        
        # Format waktu trade
        trade_time = signal.executed_at.strftime('%H:%M')
        
        message = f"""
<b>HASIL: {result_emoji} {signal.result}</b>
PAIR: {signal.symbol}
WAKTU TRADE: {trade_time} WIB
OPEN PRICE: {signal.open_price}
CLOSE PRICE: {signal.close_price}

<b>ANALISIS PASCA-EKSEKUSI:</b>
{signal.post_analysis}
        """
        
        return message.strip()
