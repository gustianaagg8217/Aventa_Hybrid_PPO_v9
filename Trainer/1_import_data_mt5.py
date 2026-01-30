import os
import pandas as pd
import MetaTrader5 as mt5
import mplfinance as mpf
from datetime import datetime, timedelta

def download_data(symbol, mt5_path, start=None, end=None):
    """Mengunduh data historis dari MetaTrader 5 dan membersihkan data."""
    # Inisialisasi koneksi ke MetaTrader 5
    if not mt5.initialize(mt5_path):
        raise RuntimeError(f"MetaTrader5 gagal diinisialisasi: {mt5.last_error()}")

    # Jika start dan end tidak diberikan, gunakan rentang 200 hari terakhir dan timeframe D1
    if start is None or end is None:
        end = datetime.now()
        start = end - timedelta(days=200)  # 200 hari

    print(f"Mengunduh data untuk simbol {symbol} dari {start} hingga {end} pada timeframe D1...")

    # Unduh data historis dari MT5 (ganti ke TIMEFRAME_D1)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_D1, start, end)
    if rates is None or len(rates) == 0:
        print(f"[INFO] Data tidak ditemukan untuk simbol {symbol} pada timeframe D1 dan rentang {start} - {end}.")
        print("Coba buka chart simbol tersebut di MT5, scroll ke kiri sejauh mungkin, lalu jalankan ulang script ini.")
        print("Atau, coba ganti timeframe ke M15 atau kurangi rentang hari.")
        raise ValueError(f"Tidak ada data untuk simbol {symbol}. Coba gunakan simbol lain atau cek data di MT5.")

    # Konversi data ke DataFrame
    data = pd.DataFrame(rates)
    data['time'] = pd.to_datetime(data['time'], unit='s')  # Konversi waktu ke format datetime
    data.rename(columns={'time': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'}, inplace=True)

    # Pastikan semua kolom yang dibutuhkan ada dalam data
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Kolom yang hilang dalam data: {missing_cols}")

    # Hapus baris yang memiliki NaN
    data = data.dropna()

    # Konversi kolom ke numerik
    for col in required_cols:
        data[col] = pd.to_numeric(data[col], errors='coerce')

    # Hapus kembali jika ada NaN setelah konversi
    data = data.dropna().reset_index(drop=True)

    # Tutup koneksi ke MT5
    mt5.shutdown()

    return data

def save_candlestick_images(data, output_dir='candlestick_images', window_sizes=[20, 50, 100], return_threshold=0.002):
    """Menyimpan gambar candlestick dari dataset dengan klasifikasi bullish dan bearish.
    Label bullish jika return > threshold & harga di atas MA20,
    bearish jika return < -threshold & harga di bawah MA20.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for window_size in window_sizes:
        bullish_folder = os.path.join(output_dir, f"bullish_{window_size}")
        bearish_folder = os.path.join(output_dir, f"bearish_{window_size}")
        os.makedirs(bullish_folder, exist_ok=True)
        os.makedirs(bearish_folder, exist_ok=True)
        # Hitung MA20 untuk filter trend
        data[f'MA20_{window_size}'] = data['Close'].rolling(window=window_size).mean()
        for i in range(len(data) - window_size):
            sample = data.iloc[i:i+window_size].set_index('Date')
            open_first = sample['Open'].iloc[0]
            close_last = sample['Close'].iloc[-1]
            ma20_last = sample[f'MA20_{window_size}'].iloc[-1]
            ret = (close_last / open_first) - 1
            # Labeling dengan return dan filter trend MA
            if ret > return_threshold and close_last > ma20_last:
                label = "bullish"
                save_folder = bullish_folder
            elif ret < -return_threshold and close_last < ma20_last:
                label = "bearish"
                save_folder = bearish_folder
            else:
                continue  # Skip jika tidak jelas
            filename = os.path.join(save_folder, f'candlestick_{window_size}_{i}.png')
            mpf.plot(sample, type='candle', style='charles', savefig=filename)
        print(f"Selesai menyimpan gambar window_size={window_size} di folder '{output_dir}'")

# Input dari pengguna
mt5_path = input("Masukkan path ke MetaTrader 5: ")
symbol = input("Masukkan simbol yang akan digunakan (contoh: XAUUSD.c): ")

# Contoh penggunaan
data = download_data(symbol, mt5_path)
save_candlestick_images(data)

# Tambahkan nama simbol ke dalam nama file CSV
csv_filename = f'data_{symbol}_mt5.csv'

# Atur ulang kolom sesuai dengan format yang diinginkan
data = data[['Date', 'Close', 'High', 'Low', 'Open', 'Volume']]

# Simpan data ke file CSV tanpa menyimpan index agar tidak muncul kolom 'Unnamed: 0'
data.to_csv(csv_filename, index=False)
print(f"Data telah disimpan sebagai {csv_filename}")

