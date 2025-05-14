import os
import matplotlib
matplotlib.use('Agg')  # Use Agg backend to avoid GUI dependencies
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ChartGenerator:
    """
    Kelas untuk menghasilkan dan menyimpan grafik analisis teknikal
    """
    
    def __init__(self):
        """
        Inisialisasi ChartGenerator
        """
        # Konfigurasi style plot
        plt.style.use('dark_background')
        self.fig_size = (12, 8)
        self.dpi = 100
        
    def generate_chart(self, df, signal, save_dir='static/charts', filename=None):
        """
        Menghasilkan dan menyimpan grafik analisis teknikal
        
        Args:
            df (DataFrame): DataFrame dengan data OHLCV dan indikator teknikal
            signal (Signal): Objek sinyal trading
            save_dir (str): Direktori untuk menyimpan grafik
            filename (str, optional): Nama file untuk menyimpan grafik. Jika None, akan dibuat otomatis.
            
        Returns:
            str: Path ke file grafik yang disimpan
        """
        # Pastikan df memiliki kolom yang dibutuhkan
        required_columns = ['open', 'high', 'low', 'close', 'volume', 'rsi', 'macd', 'macd_signal', 'ema50', 'bb_upper', 'bb_middle', 'bb_lower']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"DataFrame tidak memiliki kolom yang dibutuhkan: {missing_columns}")
            raise ValueError(f"DataFrame harus memiliki kolom {required_columns}")
            
        # Siapkan nama file jika belum ada
        if filename is None:
            symbol_safe = signal.symbol.replace('/', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"signal_{symbol_safe}_{timestamp}.png"
            
        # Pastikan direktori save_dir ada
        os.makedirs(save_dir, exist_ok=True)
        
        # Path lengkap untuk menyimpan file
        save_path = os.path.join(save_dir, filename)
        
        # Buat salinan df terakhir untuk plot
        df_plot = df.tail(60).copy()  # Tampilkan 60 candle terakhir
        
        # Tambahkan index datetime jika belum ada
        if not isinstance(df_plot.index, pd.DatetimeIndex):
            df_plot.reset_index(inplace=True)
            df_plot['datetime'] = pd.to_datetime(df_plot['datetime'])
            df_plot.set_index('datetime', inplace=True)
        
        # Buat figure dan grid untuk subplot
        fig = plt.figure(figsize=self.fig_size, dpi=self.dpi)
        
        # Definisikan grid untuk subplot
        gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1])
        
        # Plot candlestick (ax1)
        ax1 = fig.add_subplot(gs[0])
        self._plot_candlestick(ax1, df_plot)
        
        # Plot volume (ax2)
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        self._plot_volume(ax2, df_plot)
        
        # Plot MACD (ax3)
        ax3 = fig.add_subplot(gs[2], sharex=ax1)
        self._plot_macd(ax3, df_plot)
        
        # Plot RSI (ax4)
        ax4 = fig.add_subplot(gs[3], sharex=ax1)
        self._plot_rsi(ax4, df_plot)
        
        # Tambahkan informasi signal
        self._annotate_signal(ax1, signal, df_plot)
        
        # Sempurnakan tata letak
        plt.tight_layout()
        plt.subplots_adjust(hspace=0)
        
        # Simpan gambar
        plt.savefig(save_path, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Chart berhasil disimpan di {save_path}")
        
        # Return path ke file
        return save_path
        
    def _plot_candlestick(self, ax, df):
        """
        Plot candlestick chart
        
        Args:
            ax (Axes): Matplotlib axes untuk plot
            df (DataFrame): DataFrame dengan data OHLCV
        """
        # Plot candlestick
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        
        # Plot candle body dengan warna yang lebih terang
        width = 0.6  # Kurangi lebar candle
        ax.bar(up.index, up.close - up.open, width, bottom=up.open, color='#00E676', zorder=3)
        ax.bar(down.index, down.close - down.open, width, bottom=down.open, color='#FF1744', zorder=3)
        
        # Plot wick dengan warna yang sama
        ax.vlines(up.index, up.low, up.high, color='#00E676', zorder=2, linewidth=1)
        ax.vlines(down.index, down.low, down.high, color='#FF1744', zorder=2, linewidth=1)
        
        # Tambahkan grid yang lebih jelas
        ax.grid(True, color='#2A2E39', linestyle='--', alpha=0.3, zorder=1)
        
        # Set background color
        ax.set_facecolor('#131722')
        ax.figure.patch.set_facecolor('#131722')
        
        # Plot EMA50
        ax.plot(df.index, df.ema50, color='#3d5afe', linewidth=1.5, label='EMA50')
        
        # Plot Bollinger Bands
        ax.plot(df.index, df.bb_upper, color='#7b1fa2', linewidth=1.0, linestyle='--', label='BB Upper')
        ax.plot(df.index, df.bb_middle, color='#7b1fa2', linewidth=1.0, linestyle='-', alpha=0.5, label='BB Middle')
        ax.plot(df.index, df.bb_lower, color='#7b1fa2', linewidth=1.0, linestyle='--', label='BB Lower')
        
        # Konfigurasi axes
        ax.set_title(f"{df.index[-1].strftime('%Y-%m-%d %H:%M')} - HermesQuantum AI Analysis", fontsize=16)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_ylabel('Price', fontsize=12)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.setp(ax.get_xticklabels(), visible=False)
        
    def _plot_volume(self, ax, df):
        """
        Plot volume
        
        Args:
            ax (Axes): Matplotlib axes untuk plot
            df (DataFrame): DataFrame dengan data volume
        """
        # Plot volume bars
        up = df[df.close >= df.open]
        down = df[df.close < df.open]
        
        # Color volume bars based on price movement
        ax.bar(up.index, up.volume, color='#26a69a', alpha=0.7, width=0.8)
        ax.bar(down.index, down.volume, color='#ef5350', alpha=0.7, width=0.8)
        
        # Plot volume MA
        if 'volume_ma' in df.columns:
            ax.plot(df.index, df.volume_ma, color='#ba68c8', linewidth=1.5)
        
        # Konfigurasi axes
        ax.grid(True, alpha=0.3)
        ax.set_ylabel('Volume', fontsize=10)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        plt.setp(ax.get_xticklabels(), visible=False)
        
    def _plot_macd(self, ax, df):
        """
        Plot MACD indicator
        
        Args:
            ax (Axes): Matplotlib axes untuk plot
            df (DataFrame): DataFrame dengan data MACD
        """
        # Plot MACD line
        ax.plot(df.index, df.macd, color='#2196f3', linewidth=1.5, label='MACD')
        
        # Plot signal line
        ax.plot(df.index, df.macd_signal, color='#ff9800', linewidth=1.5, label='Signal')
        
        # Plot histogram
        positive = df[df.macd >= df.macd_signal]
        negative = df[df.macd < df.macd_signal]
        
        ax.bar(positive.index, positive.macd - positive.macd_signal, color='#26a69a', alpha=0.7, width=0.8)
        ax.bar(negative.index, negative.macd - negative.macd_signal, color='#ef5350', alpha=0.7, width=0.8)
        
        # Plot zero line
        ax.axhline(y=0, color='#b0bec5', linestyle='-', alpha=0.5)
        
        # Konfigurasi axes
        ax.grid(True, alpha=0.3)
        ax.set_ylabel('MACD', fontsize=10)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.legend(loc='upper left', fontsize=8)
        plt.setp(ax.get_xticklabels(), visible=False)
        
    def _plot_rsi(self, ax, df):
        """
        Plot RSI indicator
        
        Args:
            ax (Axes): Matplotlib axes untuk plot
            df (DataFrame): DataFrame dengan data RSI
        """
        # Plot RSI line
        ax.plot(df.index, df.rsi, color='#9c27b0', linewidth=1.5)
        
        # Plot overbought/oversold levels
        ax.axhline(y=70, color='#ef5350', linestyle='--', alpha=0.5)
        ax.axhline(y=30, color='#26a69a', linestyle='--', alpha=0.5)
        ax.axhline(y=50, color='#b0bec5', linestyle='-', alpha=0.3)
        
        # Fill overbought/oversold areas
        ax.fill_between(df.index, df.rsi, 70, where=(df.rsi >= 70), color='#ef5350', alpha=0.3)
        ax.fill_between(df.index, df.rsi, 30, where=(df.rsi <= 30), color='#26a69a', alpha=0.3)
        
        # Konfigurasi axes
        ax.grid(True, alpha=0.3)
        ax.set_ylabel('RSI', fontsize=10)
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        
    def _annotate_signal(self, ax, signal, df):
        """
        Tambahkan anotasi signal ke chart
        
        Args:
            ax (Axes): Matplotlib axes untuk plot
            signal (Signal): Objek sinyal trading
            df (DataFrame): DataFrame dengan data price
        """
        # Tentukan posisi dan warna berdasarkan arah signal
        is_buy = signal.direction == "BUY"
        arrow_color = '#00E676' if is_buy else '#FF1744'  # Warna yang lebih terang
        text_color = '#FFFFFF'  # Teks putih untuk keterbacaan lebih baik
        arrow_dir = 1 if is_buy else -1
        
        # Set font untuk semua teks
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.weight'] = 'bold'
        
        # Tentukan posisi anotasi di candle terakhir
        last_idx = df.index[-1]
        x_pos = df.index[-1]
        
        if is_buy:
            y_pos = df.loc[last_idx, 'low'] * 0.998  # Sedikit di bawah low
            arrow_start = y_pos * 0.997
            arrow_end = y_pos * 1.003
        else:
            y_pos = df.loc[last_idx, 'high'] * 1.002  # Sedikit di atas high
            arrow_start = y_pos * 1.003
            arrow_end = y_pos * 0.997
        
        # Tambahkan arrow
        ax.annotate(
            '',
            xy=(x_pos, arrow_end),
            xytext=(x_pos, arrow_start),
            arrowprops=dict(facecolor=arrow_color, edgecolor=arrow_color, width=2, headwidth=8, alpha=0.8)
        )
        
        # Tambahkan teks signal
        ax.text(
            x_pos, y_pos * (1.01 if is_buy else 0.99),
            f"{signal.direction} SIGNAL\nConf: {signal.confidence}%",
            color=text_color,
            fontsize=10,
            fontweight='bold',
            ha='right',
            va='top' if not is_buy else 'bottom',
            bbox=dict(facecolor='black', edgecolor=arrow_color, alpha=0.7, boxstyle='round,pad=0.5')
        )
        
        # Tambahkan label hasil jika sudah ada
        if signal.result:
            result_color = '#26a69a' if signal.result == 'WIN' else '#ef5350'
            result_emoji = '✅' if signal.result == 'WIN' else '❌'
            
            ax.text(
                df.index[0], df.loc[df.index[0], 'high'] * 1.01,
                f"{result_emoji} {signal.result}",
                color=result_color,
                fontsize=14,
                fontweight='bold',
                ha='left',
                va='bottom',
                bbox=dict(facecolor='black', edgecolor=result_color, alpha=0.7, boxstyle='round,pad=0.5')
            )
            
        # Tambahkan watermark HermesQuantum AI
        fig = ax.figure
        fig.text(
            0.99, 0.01,
            "HermesQuantum AI",
            color='#9e9e9e',
            fontsize=10,
            alpha=0.7,
            ha='right',
            va='bottom',
            transform=fig.transFigure
        )
