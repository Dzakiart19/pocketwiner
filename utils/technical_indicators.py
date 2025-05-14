import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """
    Kelas untuk menghitung indikator teknikal yang digunakan dalam analisis pasar.
    """
    
    def __init__(self):
        """
        Inisialisasi TechnicalIndicators
        """
        pass
        
    def calculate_indicators(self, df):
        """
        Menghitung semua indikator teknikal dari dataframe harga
        
        Args:
            df (DataFrame): DataFrame dengan data OHLCV
            
        Returns:
            DataFrame: DataFrame dengan indikator teknikal tambahan
        """
        # Pastikan df memiliki kolom yang dibutuhkan
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"DataFrame tidak memiliki kolom yang dibutuhkan: {col}")
                raise ValueError(f"DataFrame harus memiliki kolom {required_columns}")
                
        # Buat salinan df untuk menghindari SettingWithCopyWarning
        df = df.copy()
        
        # Hitung RSI
        df = self.calculate_rsi(df)
        
        # Hitung MACD
        df = self.calculate_macd(df)
        
        # Hitung EMA50
        df = self.calculate_ema(df, period=50)
        
        # Hitung Bollinger Bands
        df = self.calculate_bollinger_bands(df)
        
        # Hitung ATR (Average True Range) untuk mengukur volatilitas
        df = self.calculate_atr(df)
        
        # Hitung Volume MA
        df = self.calculate_volume_ma(df)
        
        return df
        
    def calculate_rsi(self, df, period=14):
        """
        Menghitung indikator RSI (Relative Strength Index)
        
        Args:
            df (DataFrame): DataFrame dengan kolom 'close'
            period (int): Periode untuk RSI
            
        Returns:
            DataFrame: DataFrame dengan kolom 'rsi' tambahan
        """
        delta = df['close'].diff()
        
        # Pisahkan gain dan loss
        gain = delta.mask(delta < 0, 0.0)
        loss = -delta.mask(delta > 0, 0.0)
        
        # Hitung average gain dan loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Hitung RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # Hitung RSI
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
        
    def calculate_macd(self, df, fast_period=12, slow_period=26, signal_period=9):
        """
        Menghitung indikator MACD (Moving Average Convergence Divergence)
        
        Args:
            df (DataFrame): DataFrame dengan kolom 'close'
            fast_period (int): Periode untuk EMA cepat
            slow_period (int): Periode untuk EMA lambat
            signal_period (int): Periode untuk garis sinyal
            
        Returns:
            DataFrame: DataFrame dengan kolom 'macd', 'macd_signal', dan 'macd_hist' tambahan
        """
        # Hitung EMA cepat dan lambat
        ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # Hitung MACD line
        df['macd'] = ema_fast - ema_slow
        
        # Hitung signal line
        df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        
        # Hitung histogram
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df
        
    def calculate_ema(self, df, period=50, column='close'):
        """
        Menghitung EMA (Exponential Moving Average)
        
        Args:
            df (DataFrame): DataFrame dengan kolom yang diperlukan
            period (int): Periode untuk EMA
            column (str): Kolom yang akan dihitung EMA-nya
            
        Returns:
            DataFrame: DataFrame dengan kolom EMA tambahan
        """
        df[f'ema{period}'] = df[column].ewm(span=period, adjust=False).mean()
        
        return df
        
    def calculate_bollinger_bands(self, df, period=20, std_dev=2):
        """
        Menghitung Bollinger Bands
        
        Args:
            df (DataFrame): DataFrame dengan kolom 'close'
            period (int): Periode untuk moving average
            std_dev (int): Jumlah standard deviasi untuk bands
            
        Returns:
            DataFrame: DataFrame dengan kolom Bollinger Bands tambahan
        """
        # Hitung simple moving average
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        
        # Hitung standard deviasi
        rolling_std = df['close'].rolling(window=period).std()
        
        # Hitung upper dan lower bands
        df['bb_upper'] = df['bb_middle'] + (rolling_std * std_dev)
        df['bb_lower'] = df['bb_middle'] - (rolling_std * std_dev)
        
        return df
        
    def calculate_atr(self, df, period=14):
        """
        Menghitung ATR (Average True Range)
        
        Args:
            df (DataFrame): DataFrame dengan kolom 'high', 'low', dan 'close'
            period (int): Periode untuk ATR
            
        Returns:
            DataFrame: DataFrame dengan kolom 'atr' tambahan
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Hitung True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        
        # Hitung ATR
        df['atr'] = tr.rolling(window=period).mean()
        
        return df
        
    def calculate_volume_ma(self, df, period=20):
        """
        Menghitung Volume Moving Average
        
        Args:
            df (DataFrame): DataFrame dengan kolom 'volume'
            period (int): Periode untuk moving average
            
        Returns:
            DataFrame: DataFrame dengan kolom 'volume_ma' tambahan
        """
        df['volume_ma'] = df['volume'].rolling(window=period).mean()
        
        return df
