import pandas as pd
import numpy as np
import ta  # Library untuk indikator teknikal
from sklearn.preprocessing import MinMaxScaler, StandardScaler

def preprocess_data(data, timesteps):
    """Melakukan preprocessing data dengan menambahkan indikator teknikal dan normalisasi."""
    
    # Pastikan 'Date' menjadi index jika tersedia
    if 'Date' in data.columns:
        data.set_index('Date', inplace=True)
    
    # Konversi index ke datetime jika belum
    data.index = pd.to_datetime(data.index)
    
    # Moving Averages untuk HFT rule: MA_fast (3) dan MA_slow (15)
    data['MA_3'] = data['Close'].rolling(window=3).mean()
    data['MA_15'] = data['Close'].rolling(window=15).mean()

    # Stochastic Oscillator (%K, %D). Thresholds: <20 oversold, >80 overbought
    stoch = ta.momentum.StochasticOscillator(high=data['High'], low=data['Low'], close=data['Close'], window=14, smooth_window=3)
    data['stoch_k'] = stoch.stoch()
    data['stoch_d'] = stoch.stoch_signal()

    # RSI 14
    data['RSI_14'] = ta.momentum.RSIIndicator(close=data['Close'], window=14).rsi()

    # ATR 14
    data['ATR_14'] = ta.volatility.AverageTrueRange(high=data['High'], low=data['Low'], close=data['Close'], window=14).average_true_range()

    # Support / Resistance detection (simple): rolling extrema + touch-count strength
    sr_window = 50  # window untuk level SR
    touch_thresh = 0.002  # 0.2% threshold untuk "touch" level
    data['SR_min'] = data['Close'].rolling(window=sr_window).min()
    data['SR_max'] = data['Close'].rolling(window=sr_window).max()
    # distance to SR levels
    data['dist_to_support'] = (data['Close'] - data['SR_min']).abs() / data['SR_min']
    data['dist_to_resistance'] = (data['Close'] - data['SR_max']).abs() / data['SR_max']
    # hitungan "touch" dalam lookback window (200 bars) untuk menilai kekuatan
    lookback = 200
    def count_touches(series_close, level_series):
        touches = []
        for i in range(len(series_close)):
            start = max(0, i - lookback + 1)
            lvl = level_series.iloc[i]
            if np.isnan(lvl):
                touches.append(0)
                continue
            window_close = series_close.iloc[start:i+1]
            cnt = (np.abs(window_close - lvl) / lvl <= touch_thresh).sum()
            touches.append(int(cnt))
        return pd.Series(touches, index=series_close.index)
    data['support_touches'] = count_touches(data['Close'], data['SR_min'])
    data['resistance_touches'] = count_touches(data['Close'], data['SR_max'])
    # flags: strong support/resistance if touches >= 3 within lookback
    data['strong_support'] = data['support_touches'] >= 3
    data['strong_resistance'] = data['resistance_touches'] >= 3
    # SR zone labels
    data['sr_zone'] = np.where(data['strong_support'], 'SUPPORT', np.where(data['strong_resistance'], 'RESISTANCE', 'NONE'))

    # MA crossover signal: 1=BUY when MA_3 crosses above MA_15, -1=SELL when opposite
    data['ma_cross'] = 0
    ma3 = data['MA_3']; ma15 = data['MA_15']
    cross_up = (ma3 > ma15) & (ma3.shift(1) <= ma15.shift(1))
    cross_down = (ma3 < ma15) & (ma3.shift(1) >= ma15.shift(1))
    data.loc[cross_up, 'ma_cross'] = 1
    data.loc[cross_down, 'ma_cross'] = -1
    # RSI zone label: oversold/overbought/sideway/neutral
    data['rsi_zone'] = 'neutral'
    data.loc[data['RSI_14'] < 30, 'rsi_zone'] = 'oversold'
    data.loc[data['RSI_14'] > 70, 'rsi_zone'] = 'overbought'
    data.loc[(data['RSI_14'] >= 40) & (data['RSI_14'] <= 60), 'rsi_zone'] = 'sideway'
    
    # Momentum (log return)
    data['log_return'] = np.log(data['Close'] / data['Close'].shift(1))
    
    # Hapus baris yang memiliki NaN setelah perhitungan indikator
    required_cols = ['MA_15', 'stoch_k', 'stoch_d', 'RSI_14', 'ATR_14', 'log_return', 'SR_min', 'SR_max']
    data.dropna(subset=required_cols, inplace=True)
    
    # Tambahkan pengecekan data kosong sebelum normalisasi
    if data.empty:
        print(f"Jumlah data setelah dropna: {len(data)}")
        print("Beberapa baris awal data:")
        print(data.head(10))
        raise ValueError(
            "Data kosong setelah dropna pada indikator yang baru (MA_15, RSI_14, Stochastic, ATR, SR). "
            "Cek apakah data Anda cukup panjang dan tidak ada missing value di kolom Close/High/Low.\n"
            "Minimal panjang data sebaiknya >= 200 bar untuk deteksi support/resistance dan rolling yang digunakan."
        )
    
    # Scaling harga dan indikator dengan StandardScaler, Volume tetap MinMaxScaler
    price_cols = ['Open', 'High', 'Low', 'Close', 'MA_3', 'MA_15', 'stoch_k', 'stoch_d', 'RSI_14', 'ATR_14', 'log_return']
    scaler_price = StandardScaler()
    data[price_cols] = scaler_price.fit_transform(data[price_cols])
    if 'Volume' in data.columns:
        scaler_vol = MinMaxScaler()
        data[['Volume']] = scaler_vol.fit_transform(data[['Volume']])
    
    # Validasi jumlah data setelah preprocessing
    if len(data) < timesteps:
        raise ValueError("Jumlah data valid setelah preprocessing tidak cukup untuk timesteps yang ditentukan.")
    
    return data

# Allow user to specify symbol and data file at runtime
symbol = input("Masukkan simbol (default: BTCUSDm): ") or 'BTCUSDm'
data_file = input(f"Masukkan nama file data untuk {symbol} (default: data_{symbol}_mt5.csv): ") or f"data_{symbol}_mt5.csv"

# Load data
data = pd.read_csv(data_file, parse_dates=['Date'])
print("Data sebelum preprocessing:")
print(data.head())

# Proses data
timesteps = 20  # Contoh nilai timesteps
processed_data = preprocess_data(data, timesteps)

# Ubah label target menjadi log return (arah harga)
processed_data['target'] = processed_data['log_return'].shift(-1)
processed_data.dropna(subset=['target'], inplace=True)

# Tampilkan hasil preprocessing
print("\nData setelah preprocessing:")
print(processed_data.head())

# Simpan hasil preprocessing dengan nama file yang mencantumkan simbol
processed_filename = f'processed_data_{symbol}.csv'
# Simpan data hasil preprocessing tanpa menyimpan index agar tidak muncul kolom 'Unnamed: 0'
processed_data.to_csv(processed_filename, index=False)
print(f"Data setelah preprocessing telah disimpan sebagai {processed_filename}")
