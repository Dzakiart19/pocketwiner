import os
import logging
import numpy as np
import pandas as pd
import pickle
from datetime import datetime

logger = logging.getLogger(__name__)

class MLPredictor:
    """
    Kelas untuk mengelola prediksi menggunakan model machine learning
    """
    
    def __init__(self, model_dir='models'):
        """
        Inisialisasi ML Predictor
        
        Args:
            model_dir (str): Direktori tempat model ML disimpan
        """
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.model_loaded = False
        
        # Coba load model jika ada
        try:
            self._load_model()
        except Exception as e:
            logger.warning(f"Tidak bisa memuat model ML: {str(e)}")
        
    def _load_model(self):
        """
        Memuat model ML dari file
        """
        # Pastikan direktori model ada
        os.makedirs(self.model_dir, exist_ok=True)
        
        model_path = os.path.join(self.model_dir, 'xgboost_model.pkl')
        scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
        
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            try:
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                    
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                    
                self.model_loaded = True
                logger.info("Model ML berhasil dimuat")
            except Exception as e:
                logger.error(f"Error saat memuat model ML: {str(e)}")
                self.model_loaded = False
        else:
            logger.warning("File model ML tidak ditemukan")
            self.model_loaded = False
    
    def predict_win_probability(self, features):
        """
        Memprediksi probabilitas kemenangan berdasarkan fitur
        
        Args:
            features (dict): Dictionary dengan fitur untuk prediksi
            
        Returns:
            tuple: (win_probability, confidence_score) keduanya dalam persentase
        """
        # Jika model belum dimuat, gunakan logika sederhana sebagai fallback
        if not self.model_loaded:
            return self._fallback_prediction(features)
        
        try:
            # Siapkan fitur untuk prediksi
            feature_df = pd.DataFrame([features])
            
            # Transformasi fitur jika diperlukan
            if self.scaler:
                feature_scaled = self.scaler.transform(feature_df)
                feature_df = pd.DataFrame(feature_scaled, columns=feature_df.columns)
            
            # Prediksi probabilitas
            win_prob = self.model.predict_proba(feature_df)[0, 1]  # Ambil probabilitas kelas positif
            
            # Tentukan confidence score berdasarkan probabilitas
            confidence = min(win_prob * 100, 100)
            win_probability = min(win_prob * 100, 100)
            
            return win_probability, confidence
            
        except Exception as e:
            logger.error(f"Error saat melakukan prediksi: {str(e)}")
            return self._fallback_prediction(features)
    
    def _fallback_prediction(self, features):
        """
        Metode fallback untuk memprediksi probabilitas kemenangan jika model tidak tersedia
        
        Args:
            features (dict): Dictionary dengan fitur untuk prediksi
            
        Returns:
            tuple: (win_probability, confidence_score) keduanya dalam persentase
        """
        # Logika sederhana berdasarkan fitur
        score = 0
        
        # Periksa RSI
        rsi = features.get('rsi', 50)
        if features.get('is_buy', 1) == 1:  # BUY signal
            if rsi < 30:  # Oversold
                score += 20
            elif rsi < 40:
                score += 10
            elif rsi > 70:  # Overbought tidak baik untuk BUY
                score -= 20
        else:  # SELL signal
            if rsi > 70:  # Overbought
                score += 20
            elif rsi > 60:
                score += 10
            elif rsi < 30:  # Oversold tidak baik untuk SELL
                score -= 20
                
        # Periksa MACD
        macd = features.get('macd', 0)
        if features.get('is_buy', 1) == 1:  # BUY signal
            if macd > 0:  # Histogram positif baik untuk BUY
                score += 15
            else:
                score -= 5
        else:  # SELL signal
            if macd < 0:  # Histogram negatif baik untuk SELL
                score += 15
            else:
                score -= 5
                
        # Periksa EMA
        ema_diff = features.get('ema_diff', 0)
        if features.get('is_buy', 1) == 1:  # BUY signal
            if ema_diff > 0:  # Harga di atas EMA baik untuk BUY
                score += 15
            else:
                score -= 10
        else:  # SELL signal
            if ema_diff < 0:  # Harga di bawah EMA baik untuk SELL
                score += 15
            else:
                score -= 10
                
        # Periksa posisi dalam Bollinger Band
        bb_pos = features.get('bb_pos', 0.5)
        if features.get('is_buy', 1) == 1:  # BUY signal
            if bb_pos < 0.2:  # Dekat lower band baik untuk BUY
                score += 15
            elif bb_pos > 0.8:  # Dekat upper band tidak baik untuk BUY
                score -= 15
        else:  # SELL signal
            if bb_pos > 0.8:  # Dekat upper band baik untuk SELL
                score += 15
            elif bb_pos < 0.2:  # Dekat lower band tidak baik untuk SELL
                score -= 15
                
        # Periksa volatilitas
        volatility = features.get('volatility', 5)
        if volatility > 7:  # Volatilitas tinggi menambah ketidakpastian
            score -= 5
        elif volatility < 3:  # Volatilitas rendah mengurangi kemungkinan pergerakan besar
            score -= 5
        else:  # Volatilitas sedang adalah baik
            score += 10
            
        # Periksa volume
        volume_ratio = features.get('volume_ratio', 1)
        if volume_ratio > 1.5:  # Volume tinggi menunjukkan konfirmasi arah
            score += 15
        elif volume_ratio < 0.7:  # Volume rendah menunjukkan kurangnya kepercayaan
            score -= 5
        
        # Konversi total skor ke probabilitas dan confidence
        base_probability = 50  # Probabilitas dasar
        max_score = 100  # Skor maksimum yang mungkin
        
        win_probability = min(max(base_probability + score, 0), 100)
        
        # Confidence sedikit lebih rendah dari probabilitas
        confidence = max(win_probability - 5, 0)
        
        return win_probability, confidence
        
    def train_model(self, historical_signals):
        """
        Melatih model ML dari historical signals
        
        Args:
            historical_signals (list): Daftar sinyal historis dengan hasil
            
        Returns:
            bool: True jika training berhasil, False jika gagal
        """
        # Fungsi ini akan diimplementasikan jika ada data historis
        # Untuk MVP, kita akan gunakan fallback prediction
        logger.info("Training model ML belum diimplementasikan untuk MVP")
        return False
