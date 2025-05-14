import logging
import time
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import os

from utils.technical_indicators import TechnicalIndicators
from utils.chart_generator import ChartGenerator
from utils.ml_predictor import MLPredictor
from api.pocket_option import PocketOptionAPI

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """
    Kelas utama untuk menganalisis pasar OTC dan menghasilkan sinyal trading.
    """
    
    def __init__(self):
        """
        Inisialisasi Market Analyzer
        """
        self.running = False
        self.analysis_thread = None
        self.technical_indicators = TechnicalIndicators()
        self.chart_generator = ChartGenerator()
        self.ml_predictor = MLPredictor()
        self.pocket_option_api = PocketOptionAPI()
        self.db = None  # Akan diset saat start_analysis
        
    def start_analysis(self, settings):
        """
        Memulai analisis pasar dalam thread terpisah
        
        Args:
            settings (Setting): Pengaturan untuk analisis
        """
        if self.running:
            logger.warning("Analisis pasar sudah berjalan")
            return
            
        # Import db di sini untuk menghindari circular import
        from app import db
        self.db = db
        
        # Set API key untuk Pocket Option
        self.pocket_option_api.set_api_key(settings.pocket_option_api_key)
        
        # Mulai thread analisis
        self.running = True
        self.analysis_thread = threading.Thread(target=self._analyze_markets, args=(settings,))
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        
        logger.info("Analisis pasar dimulai")
        
    def stop_analysis(self):
        """
        Menghentikan analisis pasar
        """
        self.running = False
        if self.analysis_thread and self.analysis_thread.is_alive():
            # Tunggu thread berhenti (max 5 detik)
            self.analysis_thread.join(timeout=5)
            
        logger.info("Analisis pasar dihentikan")
        
    def _analyze_markets(self, settings):
        """
        Metode untuk menganalisis pasar secara terus-menerus
        
        Args:
            settings (Setting): Pengaturan untuk analisis
        """
        # Import Flask app untuk menggunakan app context
        from app import app
        
        # Import models di sini untuk menghindari circular import
        from models import Signal
        
        # Dapatkan daftar simbol yang akan dianalisis
        symbols = settings.get_symbols_list()
        
        logger.info(f"Mulai menganalisis {len(symbols)} simbol: {', '.join(symbols)}")
        
        # Persiapkan struktur data untuk menyimpan waktu sinyal terakhir
        last_signal_time = {}
        for symbol in symbols:
            last_signal_time[symbol] = datetime.now() - timedelta(hours=1)
        
        # Loop utama analisis
        while self.running:
            try:
                # Gunakan app context untuk operasi database
                with app.app_context():
                    # Periksa waktu saat ini
                    current_time = datetime.now()
                    current_minute = current_time.minute
                    current_second = current_time.second
                    
                    # Pemeriksaan waktu untuk mengirim sinyal
                    time_to_send_signal = current_second >= (60 - settings.signal_time_before_candle)
                    
                    # Analisis setiap simbol
                    for symbol in symbols:
                        try:
                            # Hindari mengirim sinyal terlalu sering untuk simbol yang sama
                            if (current_time - last_signal_time[symbol]).total_seconds() < 60:
                                continue
                                
                            # Dapatkan data historis dari Pocket Option - Selalu gunakan M1 (paksa)
                            historical_data = self.pocket_option_api.get_historical_data(
                                symbol,
                                "M1",  # Paksa timeframe ke M1 sesuai permintaan
                                limit=100  # Ambil 100 candle terakhir
                            )
                            
                            if not historical_data or len(historical_data) < 50:
                                logger.warning(f"Data historis tidak cukup untuk {symbol}")
                                continue
                                
                            # Konversi ke DataFrame pandas
                            df = pd.DataFrame(historical_data)
                            
                            # Hitung indikator teknikal
                            df = self.technical_indicators.calculate_indicators(df)
                            
                            # Analisis pasar dan deteksi sinyal
                            signal_data = self._detect_signal(df, symbol, settings)
                            
                            # Jika sinyal terdeteksi dan waktunya tepat untuk mengirim
                            if signal_data and time_to_send_signal:
                                # Perbarui waktu sinyal terakhir
                                last_signal_time[symbol] = current_time
                                
                                # Buat objek sinyal - selalu gunakan timeframe M1
                                signal = Signal(
                                    symbol=symbol,
                                    timeframe="M1",  # Paksa timeframe ke M1 sesuai permintaan
                                    direction=signal_data['direction'],
                                    executed_at=signal_data['executed_at'],
                                    sent_at=current_time,
                                    
                                    # Market snapshot
                                    volatility=signal_data['volatility'],
                                    strength_by_volume=signal_data['strength_by_volume'],
                                    price_pressure=signal_data['price_pressure'],
                                    microtrend_structure=signal_data['microtrend_structure'],
                                    
                                    # Technical analysis
                                    rsi=signal_data['rsi'],
                                    rsi_analysis=signal_data['rsi_analysis'],
                                    macd=signal_data['macd'],
                                    ema50=signal_data['ema50'],
                                    bollinger_bands=signal_data['bollinger_bands'],
                                    volume_analysis=signal_data['volume_analysis'],
                                    candle_pattern=signal_data['candle_pattern'],
                                    
                                    # AI data
                                    confidence=signal_data['confidence'],
                                    win_rate_prediction=signal_data['win_rate_prediction'],
                                    risk_level=signal_data['risk_level'],
                                    
                                    # Chart data dibuat nanti
                                    chart_url=''
                                )
                                
                                # Simpan signal ke database
                                self.db.session.add(signal)
                                self.db.session.commit()
                                
                                # Buat chart untuk sinyal
                                chart_path = self.chart_generator.generate_chart(
                                    df,
                                    signal,
                                    save_dir=os.path.join('static', 'charts'),
                                    filename=f"signal_{signal.id}_{symbol.replace('/', '_')}.png"
                                )
                                
                                # Update chart_url dalam database
                                signal.chart_url = chart_path
                                self.db.session.commit()
                                
                                # Kirim sinyal ke Telegram
                                from utils.telegram_bot import TelegramBot
                                telegram_bot = TelegramBot(settings.telegram_token)
                                telegram_bot.send_chart_with_signal(
                                    settings.telegram_chat_id,
                                    signal,
                                    chart_path
                                )
                                
                                logger.info(f"Sinyal {signal.direction} untuk {symbol} berhasil dikirim")
                                
                        except Exception as e:
                            logger.error(f"Error saat menganalisis {symbol}: {str(e)}")
                    
                    # Periksa hasil dari sinyal yang sudah dikirim
                    self._check_signal_results()
                
                # Tidur selama 1 detik sebelum iterasi berikutnya
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error dalam loop analisis utama: {str(e)}")
                time.sleep(5)  # Tunggu lebih lama jika terjadi error
                
        logger.info("Loop analisis pasar berhenti")
        
    def _detect_signal(self, df, symbol, settings):
        """
        Mendeteksi sinyal trading berdasarkan analisis teknikal dan ML
        
        Args:
            df (DataFrame): DataFrame dengan data historis dan indikator teknikal
            symbol (str): Simbol trading yang dianalisis
            settings (Setting): Pengaturan untuk analisis
            
        Returns:
            dict: Data sinyal jika terdeteksi, None jika tidak ada sinyal
        """
        if len(df) < 5:
            return None
            
        # Ambil candle terakhir
        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        # Hitung waktu eksekusi (candle berikutnya)
        next_candle_time = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # Variabel untuk menyimpan hasil analisis
        direction = None
        reason = []
        
        # === ANALISIS TEKNIKAL ===
        
        # 1. Periksa RSI
        rsi = last_candle['rsi']
        rsi_prev = prev_candle['rsi']
        
        rsi_analysis = ""
        if rsi < 30:
            rsi_analysis = "Oversold, potensi reversal naik"
            if rsi > rsi_prev:
                reason.append("RSI oversold dengan divergence positif")
                direction_bias = "BUY"
            else:
                reason.append("RSI oversold tapi masih turun")
                direction_bias = None
        elif rsi > 70:
            rsi_analysis = "Overbought, potensi reversal turun"
            if rsi < rsi_prev:
                reason.append("RSI overbought dengan divergence negatif")
                direction_bias = "SELL"
            else:
                reason.append("RSI overbought tapi masih naik")
                direction_bias = None
        else:
            if rsi > 50:
                rsi_analysis = "Bullish momentum"
                if rsi > rsi_prev:
                    reason.append("RSI bullish dan menguat")
                    direction_bias = "BUY"
                else:
                    reason.append("RSI bullish tapi melemah")
                    direction_bias = None
            else:
                rsi_analysis = "Bearish momentum"
                if rsi < rsi_prev:
                    reason.append("RSI bearish dan menguat")
                    direction_bias = "SELL"
                else:
                    reason.append("RSI bearish tapi melemah")
                    direction_bias = None
        
        # 2. Periksa MACD
        macd = last_candle['macd']
        macd_signal = last_candle['macd_signal']
        macd_prev = prev_candle['macd']
        macd_signal_prev = prev_candle['macd_signal']
        
        macd_analysis = ""
        if macd > macd_signal and macd_prev <= macd_signal_prev:
            macd_analysis = "Cross Up + Histogram positif"
            reason.append("MACD golden cross (bullish)")
            if direction_bias == "BUY" or direction is None:
                direction = "BUY"
        elif macd < macd_signal and macd_prev >= macd_signal_prev:
            macd_analysis = "Cross Down + Histogram negatif"
            reason.append("MACD death cross (bearish)")
            if direction_bias == "SELL" or direction is None:
                direction = "SELL"
        elif macd > macd_signal:
            macd_analysis = "Histogram positif " + ("dan membesar" if (macd - macd_signal) > (macd_prev - macd_signal_prev) else "tapi mengecil")
            reason.append("MACD histogram positif" + (" dan momentum menguat" if (macd - macd_signal) > (macd_prev - macd_signal_prev) else ""))
            if direction_bias == "BUY" or direction is None:
                direction = "BUY"
        elif macd < macd_signal:
            macd_analysis = "Histogram negatif " + ("dan membesar" if (macd_signal - macd) > (macd_signal_prev - macd_prev) else "tapi mengecil")
            reason.append("MACD histogram negatif" + (" dan momentum menguat" if (macd_signal - macd) > (macd_signal_prev - macd_prev) else ""))
            if direction_bias == "SELL" or direction is None:
                direction = "SELL"
        else:
            macd_analysis = "Histogram netral"
        
        # 3. Periksa EMA50
        price = last_candle['close']
        ema50 = last_candle['ema50']
        price_prev = prev_candle['close']
        ema50_prev = prev_candle['ema50']
        
        ema_analysis = ""
        if price > ema50 and price_prev <= ema50_prev:
            ema_analysis = "Harga break ke atas EMA50"
            reason.append("Breakout di atas EMA50 (bullish)")
            if direction_bias == "BUY" or direction is None:
                direction = "BUY"
        elif price < ema50 and price_prev >= ema50_prev:
            ema_analysis = "Harga break ke bawah EMA50"
            reason.append("Breakdown di bawah EMA50 (bearish)")
            if direction_bias == "SELL" or direction is None:
                direction = "SELL"
        elif price > ema50:
            ema_analysis = "Harga di atas EMA50, uptrend"
            if price - ema50 > price_prev - ema50_prev:
                reason.append("Uptrend menguat di atas EMA50")
                if direction_bias == "BUY" or direction is None:
                    direction = "BUY"
        elif price < ema50:
            ema_analysis = "Harga di bawah EMA50, downtrend"
            if ema50 - price > ema50_prev - price_prev:
                reason.append("Downtrend menguat di bawah EMA50")
                if direction_bias == "SELL" or direction is None:
                    direction = "SELL"
        
        # 4. Periksa Bollinger Bands
        bb_upper = last_candle['bb_upper']
        bb_lower = last_candle['bb_lower']
        bb_middle = last_candle['bb_middle']
        
        bb_analysis = ""
        if price <= bb_lower:
            bb_analysis = "Break bawah + potensi reversal naik"
            reason.append("Harga di bawah BB lower (potensi oversold)")
            if direction_bias != "SELL":
                direction = "BUY"
        elif price >= bb_upper:
            bb_analysis = "Break atas + potensi reversal turun"
            reason.append("Harga di atas BB upper (potensi overbought)")
            if direction_bias != "BUY":
                direction = "SELL"
        else:
            # Periksa squeeze BB (volatilitas rendah)
            bb_width = (bb_upper - bb_lower) / bb_middle
            bb_width_prev = (prev_candle['bb_upper'] - prev_candle['bb_lower']) / prev_candle['bb_middle']
            
            if bb_width < 0.02:  # Volatilitas sangat rendah
                bb_analysis = "Squeeze kuat, bersiap untuk breakout"
                reason.append("Bollinger Band Squeeze (potensi breakout)")
                # Arah ditentukan oleh indikator lain
            elif bb_width < bb_width_prev:
                bb_analysis = "Volatilitas menurun"
            else:
                bb_analysis = "Volatilitas meningkat"
                
                if price > bb_middle and price_prev <= bb_middle:
                    bb_analysis += ", break ke atas BB middle"
                    reason.append("Break ke atas BB middle (bullish)")
                    if direction_bias == "BUY" or direction is None:
                        direction = "BUY"
                elif price < bb_middle and price_prev >= bb_middle:
                    bb_analysis += ", break ke bawah BB middle"
                    reason.append("Break ke bawah BB middle (bearish)")
                    if direction_bias == "SELL" or direction is None:
                        direction = "SELL"
        
        # Jika belum ada arah yang jelas, tentukan berdasarkan momentum
        if direction is None:
            # Cek momentum dari beberapa candle terakhir
            last_3_candles = df.iloc[-3:]['close'].values
            if last_3_candles[2] > last_3_candles[1] > last_3_candles[0]:
                direction = "BUY"
                reason.append("Momentum naik dari 3 candle terakhir")
            elif last_3_candles[2] < last_3_candles[1] < last_3_candles[0]:
                direction = "SELL"
                reason.append("Momentum turun dari 3 candle terakhir")
            else:
                # Tidak ada tren yang jelas, skip sinyal
                return None
        
        # === KALKULASI PARAMETER LAINNYA ===
        
        # Hitung volatilitas (MPI)
        atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].rolling(window=14).mean().iloc[-1]
        volatility = min(round((atr / avg_atr) * 5, 1), 10)  # Scale to 0-10
        
        # Strength by volume
        volume = df['volume'].iloc[-5:].values
        avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
        
        volume_ratio = sum(volume) / (5 * avg_volume)
        strength_by_volume = min(round(volume_ratio * 100, 1), 100)
        
        # Tentukan arah volume berdasarkan arah sinyal
        if direction == "BUY":
            volume_direction = "bullish" 
        else:
            volume_direction = "bearish"
        
        volume_analysis = f"Surge {round(volume_ratio * 100)}% dari MA-20 volume"
        
        # Price pressure dalam 3 menit terakhir
        price_3m_ago = df['close'].iloc[-3]
        price_change_pct = ((price - price_3m_ago) / price_3m_ago) * 100
        price_pressure = round(price_change_pct, 2)
        
        # Microtrend structure
        if direction == "BUY":
            if df['low'].iloc[-1] > df['low'].iloc[-2]:
                microtrend = "Higher low confirmed"
            else:
                microtrend = "Potential reversal point"
        else:
            if df['high'].iloc[-1] < df['high'].iloc[-2]:
                microtrend = "Lower high confirmed"
            else:
                microtrend = "Potential reversal point"
        
        # Candle pattern detection (simplified)
        candle_pattern = self._detect_candle_pattern(df)
        
        # === PERHITUNGAN AI ===
        
        # Gunakan model ML untuk prediksi confidence dan win rate
        prediction_data = {
            'rsi': rsi,
            'macd': macd - macd_signal,  # MACD histogram
            'ema_diff': (price - ema50) / price * 100,  # EMA difference in percent
            'bb_pos': (price - bb_lower) / (bb_upper - bb_lower),  # Position within BB (0-1)
            'volatility': volatility,
            'volume_ratio': volume_ratio,
            'price_pressure': price_pressure,
            'is_buy': 1 if direction == "BUY" else 0
        }
        
        # Dalam aplikasi sesungguhnya, ini menggunakan model ML yang telah dilatih
        # Tapi untuk contoh, kita akan gunakan logika sederhana untuk mendemonstrasikan
        
        # Hitung confidence score (0-100)
        confidence_factors = [
            1 if ("oversold" in rsi_analysis and direction == "BUY") or ("overbought" in rsi_analysis and direction == "SELL") else 0.5,
            1 if "cross" in macd_analysis.lower() else 0.7,
            1 if "break" in ema_analysis.lower() else 0.7,
            1 if "break" in bb_analysis.lower() else 0.7,
            0.8 if volume_ratio > 1.2 else 0.5
        ]
        
        # Konversi faktor ke skor confidence 0-100%
        confidence_score = (sum(confidence_factors) / len(confidence_factors)) * 100
        confidence_score = min(round(confidence_score, 1), 100)
        
        # Jika confidence di bawah threshold, skip sinyal
        if confidence_score < settings.min_confidence_threshold:
            return None
        
        # Predict win rate (menggunakan logika sederhana untuk contoh)
        win_factors = [
            confidence_score / 100,
            0.9 if volatility > 6 else 0.7,  # Volatilitas tinggi lebih baik untuk sinyal
            0.9 if strength_by_volume > 80 else 0.7,
            0.9 if abs(price_pressure) > 0.5 else 0.7,
            0.9 if "confirmed" in microtrend else 0.7
        ]
        
        win_rate_prediction = (sum(win_factors) / len(win_factors)) * 100
        win_rate_prediction = min(round(win_rate_prediction, 1), 100)
        
        # Tentukan level risiko
        if win_rate_prediction > 90:
            risk_level = "Sangat Rendah"
        elif win_rate_prediction > 80:
            risk_level = "Rendah"
        elif win_rate_prediction > 70:
            risk_level = "Sedang"
        elif win_rate_prediction > 60:
            risk_level = "Tinggi"
        else:
            risk_level = "Sangat Tinggi"
        
        # Buat data sinyal
        signal_data = {
            'direction': direction,
            'executed_at': next_candle_time,
            
            # Market snapshot
            'volatility': volatility,
            'strength_by_volume': strength_by_volume,
            'price_pressure': price_pressure,
            'microtrend_structure': microtrend,
            
            # Technical analysis
            'rsi': round(rsi, 1),
            'rsi_analysis': rsi_analysis,
            'macd': macd_analysis,
            'ema50': ema_analysis,
            'bollinger_bands': bb_analysis,
            'volume_analysis': volume_analysis,
            'candle_pattern': candle_pattern,
            
            # AI data
            'confidence': confidence_score,
            'win_rate_prediction': win_rate_prediction,
            'risk_level': risk_level,
            
            # Reasoning
            'reason': ", ".join(reason)
        }
        
        return signal_data
        
    def _detect_candle_pattern(self, df):
        """
        Deteksi pola candlestick
        
        Args:
            df (DataFrame): DataFrame dengan data OHLC
            
        Returns:
            str: Pola candlestick yang terdeteksi
        """
        if len(df) < 3:
            return "Unknown Pattern"
            
        # Ambil 3 candle terakhir
        last_candles = df.iloc[-3:].copy()
        
        # Hitung panjang body dan shadow untuk setiap candle
        for i in range(len(last_candles)):
            candle = last_candles.iloc[i]
            body_size = abs(candle['close'] - candle['open'])
            candle_range = candle['high'] - candle['low']
            
            # Tambahkan kolom baru
            last_candles.loc[last_candles.index[i], 'body_size'] = body_size
            last_candles.loc[last_candles.index[i], 'candle_range'] = candle_range
            last_candles.loc[last_candles.index[i], 'is_bullish'] = candle['close'] > candle['open']
        
        # Candle terakhir
        last_candle = last_candles.iloc[-1]
        prev_candle = last_candles.iloc[-2]
        
        # Deteksi berbagai pola candlestick
        
        # Pola Hammer (bullish reversal)
        if (last_candle['is_bullish'] and 
            last_candle['body_size'] < 0.3 * last_candle['candle_range'] and 
            (last_candle['high'] - max(last_candle['open'], last_candle['close'])) < 0.2 * last_candle['candle_range'] and
            (min(last_candle['open'], last_candle['close']) - last_candle['low']) > 0.6 * last_candle['candle_range']):
            return "Hammer Rebound AI-classified"
        
        # Pola Shooting Star (bearish reversal)
        if (not last_candle['is_bullish'] and 
            last_candle['body_size'] < 0.3 * last_candle['candle_range'] and 
            (last_candle['high'] - max(last_candle['open'], last_candle['close'])) > 0.6 * last_candle['candle_range'] and
            (min(last_candle['open'], last_candle['close']) - last_candle['low']) < 0.2 * last_candle['candle_range']):
            return "Shooting Star Pattern"
        
        # Pola Engulfing (reversal)
        if (last_candle['is_bullish'] and not prev_candle['is_bullish'] and 
            last_candle['body_size'] > prev_candle['body_size'] and 
            last_candle['open'] < prev_candle['close'] and 
            last_candle['close'] > prev_candle['open']):
            return "Bullish Engulfing Pattern"
        
        if (not last_candle['is_bullish'] and prev_candle['is_bullish'] and 
            last_candle['body_size'] > prev_candle['body_size'] and 
            last_candle['open'] > prev_candle['close'] and 
            last_candle['close'] < prev_candle['open']):
            return "Bearish Engulfing Pattern"
        
        # Pola Doji (indecision)
        if last_candle['body_size'] < 0.1 * last_candle['candle_range']:
            return "Doji Pattern (indecision)"
        
        # Pola Marubozu (strong trend)
        if (last_candle['body_size'] > 0.8 * last_candle['candle_range']):
            if last_candle['is_bullish']:
                return "Bullish Marubozu (strong buyers)"
            else:
                return "Bearish Marubozu (strong sellers)"
        
        # Pola Inside Bar (consolidation)
        if (last_candle['high'] < prev_candle['high'] and last_candle['low'] > prev_candle['low']):
            return "Inside Bar Pattern"
        
        # Pola Three White Soldiers (bullish continuation)
        if (len(last_candles) >= 3 and 
            all(last_candles.iloc[i]['is_bullish'] for i in range(-3, 0)) and 
            last_candles.iloc[-1]['close'] > last_candles.iloc[-2]['close'] > last_candles.iloc[-3]['close'] and
            last_candles.iloc[-1]['open'] > last_candles.iloc[-2]['open'] > last_candles.iloc[-3]['open']):
            return "Three White Soldiers Pattern"
        
        # Tidak ada pola spesifik yang terdeteksi
        if last_candle['is_bullish']:
            return "Bullish Candle"
        else:
            return "Bearish Candle"
            
    def _check_signal_results(self):
        """
        Memeriksa hasil dari sinyal yang telah dikirim dan memperbarui database
        """
        # Import Flask app untuk menggunakan app context
        from app import app
        
        # Gunakan app context untuk operasi database
        with app.app_context():
            # Import model di sini untuk menghindari circular import
            from models import Signal, Setting
            from app import db
            from utils.telegram_bot import TelegramBot
            
            # Cari sinyal tanpa hasil dengan waktu eksekusi yang sudah berlalu + 1 menit
            signals_to_check = Signal.query.filter(
                Signal.result.is_(None),
                Signal.executed_at < (datetime.now() - timedelta(minutes=1))
            ).all()
            
            if not signals_to_check:
                return
                
            # Dapatkan pengaturan untuk Telegram
            settings = Setting.query.first()
            
            for signal in signals_to_check:
                try:
                    # Dapatkan data candle untuk periode eksekusi
                    candle_data = self.pocket_option_api.get_candle_by_time(
                        signal.symbol,
                        signal.timeframe,
                        signal.executed_at
                    )
                    
                    if not candle_data:
                        logger.warning(f"Tidak bisa mendapatkan data candle untuk signal {signal.id}")
                        continue
                        
                    # Simpan harga open dan close
                    signal.open_price = candle_data['open']
                    signal.close_price = candle_data['close']
                    
                    # Tentukan hasil berdasarkan arah sinyal dan pergerakan harga
                    if signal.direction == "BUY":
                        if candle_data['close'] > candle_data['open']:
                            signal.result = "WIN"
                        elif candle_data['close'] < candle_data['open']:
                            signal.result = "LOSS"
                        else:
                            signal.result = "DRAW"
                    else:  # SELL
                        if candle_data['close'] < candle_data['open']:
                            signal.result = "WIN"
                        elif candle_data['close'] > candle_data['open']:
                            signal.result = "LOSS"
                        else:
                            signal.result = "DRAW"
                    
                    # Buat analisis pasca-eksekusi
                    if signal.result == "WIN":
                        if signal.direction == "BUY":
                            signal.post_analysis = f"Harga bergerak naik sesuai prediksi, dari {signal.open_price} ke {signal.close_price}, memanfaatkan momentum {signal.rsi_analysis.lower()} dan {signal.microtrend_structure.lower()}."
                        else:
                            signal.post_analysis = f"Harga bergerak turun sesuai prediksi, dari {signal.open_price} ke {signal.close_price}, memanfaatkan momentum {signal.rsi_analysis.lower()} dan {signal.microtrend_structure.lower()}."
                    else:
                        if signal.direction == "BUY":
                            signal.post_analysis = f"Prediksi tidak terwujud, harga bergerak turun dari {signal.open_price} ke {signal.close_price}, kemungkinan karena tekanan jual mendadak atau berita negatif."
                        else:
                            signal.post_analysis = f"Prediksi tidak terwujud, harga bergerak naik dari {signal.open_price} ke {signal.close_price}, kemungkinan karena tekanan beli mendadak atau berita positif."
                    
                    # Simpan ke database
                    db.session.commit()
                    
                    # Kirim hasil ke Telegram
                    telegram_bot = TelegramBot(settings.telegram_token)
                    telegram_bot.send_trade_result(
                        settings.telegram_chat_id,
                        signal
                    )
                    
                    logger.info(f"Hasil sinyal {signal.id} untuk {signal.symbol}: {signal.result}")
                    
                except Exception as e:
                    logger.error(f"Error saat memeriksa hasil signal {signal.id}: {str(e)}")
