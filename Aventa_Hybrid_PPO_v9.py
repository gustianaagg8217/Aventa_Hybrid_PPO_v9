import argparse
import MetaTrader5 as mt5 # type: ignore
import time
import numpy as np # type: ignore
from stable_baselines3 import PPO # type: ignore
import signal
import csv
from datetime import datetime, timedelta
import os  # Tambahkan ini
import pandas as pd # type: ignore
import json  # <-- ditambahkan

# Parser untuk argumen
parser = argparse.ArgumentParser(description="Aventa Hybrid PPO Trading Bot")
parser.add_argument("--mt5_path", type=str, required=True, help="Path to MetaTrader 5 terminal")
parser.add_argument("--symbol", type=str, required=True, help="Trading symbol")
parser.add_argument("--lot_size", type=float, required=True, help="Lot size")
parser.add_argument("--close_profit", type=float, required=True, help="Profit target")
parser.add_argument("--max_open_trades", type=int, required=True, help="Maximum number of open trades")
parser.add_argument("--ppo_model_path", type=str, required=True, help="Path to PPO model file")
parser.add_argument("--type_filling", type=int, required=True, choices=[1, 2, 3],
                    help="Order filling mode: 1=FOK, 2=IOC, 3=RETURN")
parser.add_argument("--max_spread", type=float, required=True, help="Maximum allowed spread")  # Tambahkan argumen ini
# Add arguments for trading hours
parser.add_argument("--start_trading_hour", type=int, default=9, help="Start trading hour (0-23, default 9)")
parser.add_argument("--end_trading_hour", type=int, default=17, help="End trading hour (0-23, default 17)")
# Add argument for daily profit target
parser.add_argument("--daily_target", type=float, default=2.0, help="Daily profit target as a percentage of account balance (default 2%)")
# Tambahkan argumen untuk max drawdown
parser.add_argument("--max_dd", type=float, default=5.0, help="Maximum drawdown allowed as a percentage of account balance (default 5%)")
parser.add_argument("--reverse", action="store_true", help="Aktifkan reverse trading (membalik sinyal)")
parser.add_argument("--window_open_limit", type=int, default=50, help="Maksimal open trade per window aktif (default 50)")  # lebih banyak untuk HFT
parser.add_argument("--window_on_seconds", type=int, default=60, help="Durasi window aktif trading dalam detik (default 60 detik = 1 menit)")  # HFT: lebih singkat
parser.add_argument("--window_pause_seconds", type=int, default=10, help="Durasi window PAUSE dalam detik (default 10 detik)")  # HFT: singkat

# Parse argumen
args = parser.parse_args()

WINDOW_ON_SECONDS = args.window_on_seconds
WINDOW_PAUSE_SECONDS = args.window_pause_seconds

# Logging untuk debugging
print("Argumen yang diterima:")
print(f"Path MT5: {args.mt5_path}")
print(f"Simbol: {args.symbol}")
print(f"Ukuran Lot: {args.lot_size}")
print(f"Close Profit: {args.close_profit}")
print(f"Maksimal Posisi Terbuka: {args.max_open_trades}")
print(f"Path Model PPO: {args.ppo_model_path}")
print(f"Tipe Pengisian: {args.type_filling}")
print(f"Spread Maksimal: {args.max_spread}")
print(f"Jam Mulai Trading: {args.start_trading_hour}")
print(f"Jam Selesai Trading: {args.end_trading_hour}")
print(f"Target Harian: {args.daily_target}%")
print(f"Max Drawdown: {args.max_dd}%")
print(f"Reverse Trading: {'Aktif' if args.reverse else 'Tidak Aktif'}")
print("-" * 50)  # Separator line

# Initialize MetaTrader 5
print("Inisialisasi MetaTrader 5...")
if not mt5.initialize(args.mt5_path):
    print("Inisialisasi MetaTrader 5 gagal")
    mt5.shutdown()
    exit()

# Fetch and display account information
account_info = mt5.account_info()
if account_info is not None:
    print(f"Nomor Akun: {account_info.login}")
    print(f"Nama Akun: {account_info.name}")
else:
    print("Gagal mendapatkan informasi akun.")
    mt5.shutdown()
    exit()
print("-" * 50)  # Separator line

# --- NEW: baseline equity file per account ---
try:
    account_number = account_info.login if account_info else "N_A"
except Exception:
    account_number = "N_A"
BASELINE_FILE = f"baseline_equity_{account_number}.json"

def save_baseline_equity(account_number, equity):
    try:
        data = {
            "account": account_number,
            "baseline_equity": float(equity),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(f"baseline_equity_{account_number}.json", "w") as f:
            json.dump(data, f)
        # print_with_account belum terdefinisi saat import; gunakan print sederhana di sini
        print(f"[INFO] Baseline equity saved for account {account_number}: {data['baseline_equity']}")
    except Exception as e:
        # print_with_account belum terdefinisi saat import; gunakan print sederhana di sini
        print(f"[ERROR] Gagal menyimpan baseline equity: {e}")

def load_baseline_equity(account_number):
    try:
        path = f"baseline_equity_{account_number}.json"
        if not os.path.isfile(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return float(data.get("baseline_equity", 0.0))
    except Exception as e:
        # print_with_account belum terdefinisi saat import; gunakan print sederhana di sini
        print(f"[ERROR] Gagal memuat baseline equity: {e}")
        return None

# Create baseline file on start if not exists
_existing_baseline = load_baseline_equity(account_number)
if _existing_baseline is None:
    # gunakan equitas saat ini sebagai baseline
    try:
        start_equity = account_info.equity if account_info else 0.0
        save_baseline_equity(account_number, start_equity)
        baseline_equity = float(start_equity)
    except Exception as e:
        # print_with_account belum terdefinisi saat ini -> gunakan print biasa
        print(f"[WARNING] Tidak dapat menyimpan baseline equity awal: {e}")
        baseline_equity = 0.0
else:
    baseline_equity = float(_existing_baseline)
# print_with_account belum terdefinisi saat ini -> gunakan print biasa
print(f"[INFO] Baseline equity for account {account_number}: {baseline_equity}")
# --- END NEW ---

# Tetapkan nilai type_filling berdasarkan pilihan
if args.type_filling == 1:
    type_filling = mt5.ORDER_FILLING_FOK
elif args.type_filling == 2:
    type_filling = mt5.ORDER_FILLING_IOC
elif args.type_filling == 3:
    type_filling = mt5.ORDER_FILLING_RETURN
else:
    raise ValueError("Invalid type_filling value")

# Trading parameters
symbol = args.symbol
lot_size = args.lot_size
close_profit = args.close_profit
max_open_trades = args.max_open_trades
ppo_model_path = args.ppo_model_path

# Ensure the symbol is selected
print(f"Memilih simbol: {symbol}...")
if not mt5.symbol_select(symbol, True):
    print(f"Gagal memilih simbol {symbol}")
    mt5.shutdown()
    exit()

# Load PPO agent
print("Memuat agen trading PPO...")
ppo_agent = PPO.load(ppo_model_path)

# Added separator lines for debug information between accounts
print("\n-----------------------------")
print("Informasi Akun:")
print(f"Simbol: {symbol}")
print(f"Ukuran Lot: {lot_size}")
print(f"Close Profit: {close_profit}")
print(f"Maksimal Posisi Terbuka: {max_open_trades}")
print(f"Path Model PPO: {ppo_model_path}")
print(f"Tipe Pengisian: {args.type_filling}")
print(f"Spread Maksimal: {args.max_spread}")
print("-----------------------------\n")

def print_with_account(msg):
    try:
        account_info = mt5.account_info()
        account_number = account_info.login if account_info else "N/A"
    except Exception:
        account_number = "N/A"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [Account: {account_number}] {msg}")

# Function to get account information
def get_account_info():
    #print_with_account("Mengambil informasi akun...")
    account_info = mt5.account_info()
    if account_info is None:
        print_with_account("Gagal mendapatkan informasi akun")
        mt5.shutdown()
        exit()
    #print_with_account(f"Nomor Akun: {account_info.login}")
    #print_with_account(f"Nama Akun: {account_info.name}")
    return account_info

# Function to get open trades
def get_open_trades():
    print_with_account("Fetching open trades with specific magic number...")
    trades = mt5.positions_get(symbol=symbol)
    if trades is None:
        return []
    return [t for t in trades if t.magic == 810251]

# Function to calculate TP price based on $0.8 profit
def calculate_tp_price(trade_type, entry_price, lot_size, tp_amount=close_profit):
    """Menghitung harga TP berdasarkan profit $0.5."""
    point = mt5.symbol_info(symbol).point
    tp_points = (tp_amount / lot_size)
    if "BTC" in symbol:
        tp_points *= 100
        print_with_account(f"TP points untuk {symbol} dikalikan 100: {tp_points}")
    if trade_type == mt5.ORDER_TYPE_BUY:
        return entry_price + tp_points * point
    elif trade_type == mt5.ORDER_TYPE_SELL:
        return entry_price - tp_points * point
    return None

# Modify the place_trade function to include TP
def place_trade(action):
    # Debug spread aktual
    actual_spread = get_actual_spread(symbol)
    if actual_spread is not None:
        log_to_csv("Spread", "Diperiksa Sebelum Trading", f"Spread Aktual: {actual_spread:.5f}")
        if actual_spread > args.max_spread:
            print_with_account(f"[PERINGATAN] Spread terlalu tinggi: {actual_spread:.5f} > {args.max_spread:.5f}")
            log_to_csv("Spread", "Terlalu Tinggi", f"Spread Aktual: {actual_spread:.5f}, Spread Maksimal: {args.max_spread:.5f}")
            return  # Jangan lakukan trading jika spread terlalu tinggi

    print_with_account(f"Melakukan trading dengan aksi: {'BELI' if action == 2 else 'JUAL'}...")
    trade_type = mt5.ORDER_TYPE_BUY if action == 2 else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if action == 2 else mt5.symbol_info_tick(symbol).bid
    tp_price = calculate_tp_price(mt5.ORDER_TYPE_BUY if action == 2 else mt5.ORDER_TYPE_SELL, price, lot_size)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": trade_type,
        "price": price,
        "tp": tp_price,  # Add TP to the trade request
        "deviation": 5,  # lebih agresif untuk HFT (dikurangi)
        "magic": 810251,
        "comment": "AvHybrid_v9",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": type_filling,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print_with_account(f"Trade failed, retcode={result.retcode}")
        log_to_csv("Trade", "Failed", f"Action: {'BUY' if action == 2 else 'SELL'}, Retcode: {result.retcode}")
    else:
        print_with_account(f"Trade successful: {result}")
        log_to_csv("Trade", "Successful", f"Action: {'BUY' if action == 2 else 'SELL'}, Price: {price}, Volume: {lot_size}")
    # Update trading report setiap open trade
    update_trading_report()

# Function to close all trades
def close_all_trades():
    print_with_account("Menutup semua posisi terbuka...")
    for trade in get_open_trades():
        trade_type = mt5.ORDER_TYPE_SELL if trade.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if trade.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": trade.volume,
            "type": trade_type,
            "position": trade.ticket,
            "price": price,
            "deviation": 10,  # dikurangi dari 20 untuk respons lebih cepat
            "magic": 810251,
            "comment": "Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": type_filling,  # tambahkan ini
        }
        success = False
        for retry in range(5):
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print_with_account(f"Trade closed: {result}")
                log_to_csv("Close Trade", "Successful", f"Position: {trade.ticket}, Volume: {trade.volume}")
                # Update trading report setiap close trade
                update_trading_report()
                success = True
                break
            elif result.retcode == 10030:
                print_with_account(f"[Close Trade] Retcode=10030 (server busy/no connection). Percobaan ke-{retry+1}/5. Reinitializing...")
                mt5.shutdown()
                time.sleep(0.5)
                mt5.initialize(args.mt5_path)  # reinit ulang
                time.sleep(0.5)  # jeda singkat sebelum retry
            else:
                print_with_account(f"Failed to close trade, retcode={result.retcode}")
                log_to_csv("Close Trade", "Failed", f"Position: {trade.ticket}, Retcode: {result.retcode}")
                break
        if not success:
            print_with_account(f"[PERINGATAN] Posisi {trade.ticket} gagal ditutup setelah 5 percobaan. Silakan cek manual di MT5.")
            log_to_csv("Close Trade", "Failed", f"Position: {trade.ticket}, Gagal ditutup setelah 5 percobaan.")
    # Update trading report setelah semua close
    update_trading_report()

# Function to reset the program
def reset_program(signal_received, frame):
    print_with_account("\nMengatur ulang program ke kondisi awal...")
    mt5.shutdown()  # Pastikan MetaTrader 5 ditutup dengan benar
    print_with_account("Memulai ulang program...")
    exec(open(__file__).read())  # Memulai ulang skrip

# Attach signal handler for Ctrl+C
signal.signal(signal.SIGINT, reset_program)

# Fungsi untuk mencatat log ke file CSV
def log_to_csv(action, status, details=""):
    log_file = "log_transaksi.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        account_info = mt5.account_info()
        account_number = account_info.login if account_info else "N/A"
    except Exception:
        account_number = "N/A"
    log_entry = {
        "timestamp": timestamp,
        "action": action,
        "status": status,
        "details": details
    }
    # Tampilkan log di layar dengan timestamp & nomor akun
    print(f"[{timestamp}] [Account: {account_number}] [{action}] [{status}] {details}")
    # Tulis log ke file CSV
    try:
        file_exists = os.path.isfile(log_file)  # type: ignore
        with open(log_file, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["timestamp", "action", "status", "details"])
            if not file_exists:
                writer.writeheader()  # Tulis header jika file belum ada
            writer.writerow(log_entry)
    except Exception as e:
        print(f"[ERROR] Gagal mencatat log ke CSV: {e}")

# Function to get the actual spread of the symbol
def get_actual_spread(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        try:
            account_info = mt5.account_info()
            account_number = account_info.login if account_info else "N/A"
        except Exception:
            account_number = "N/A"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [Account: {account_number}] [ERROR] Failed to fetch tick data for symbol: {symbol}")
        return None
    spread = tick.ask - tick.bid
    try:
        account_info = mt5.account_info()
        account_number = account_info.login if account_info else "N/A"
    except Exception:
        account_number = "N/A"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [Account: {account_number}] [DEBUG] Actual spread for {symbol}: {spread:.5f}")
    return spread

# Added debug information for suggested lot size based on free margin

def calculate_suggested_lot(free_margin, risk_percentage=1, lot_min=0.01, lot_step=0.01, margin_per_lot=100000, lot_max=10):
    """Menghitung lot yang disarankan berdasarkan free margin dan persentase risiko."""
    # Risiko dihitung sebagai persentase dari free margin
    risk_amount = free_margin * (risk_percentage / 100)
    
    # Hitung lot berdasarkan margin yang tersedia
    suggested_lot = risk_amount / margin_per_lot
    
    # Pastikan lot sesuai dengan lot minimum, maksimum, dan kelipatan lot step
    if suggested_lot < lot_min:
        return lot_min
    elif suggested_lot > lot_max:
        return lot_max
    else:
        # Bulatkan ke kelipatan lot_step
        return round(suggested_lot // lot_step * lot_step, 2)

def get_margin_per_lot(symbol):
    """Mendeteksi margin per lot dari broker untuk simbol tertentu."""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"[ERROR] Failed to fetch symbol info for {symbol}")
        return None

    margin_per_lot = symbol_info.margin_initial
    if margin_per_lot is None or margin_per_lot < 100:  # Validasi nilai margin
        print_with_account(f"[WARNING] Margin per lot untuk {symbol} tidak valid. Menggunakan nilai default 100,000.")
        margin_per_lot = 100000  # Gunakan nilai default jika margin tidak valid

    return margin_per_lot

def analyze_entry_signal(df_m5, df_m15, df_m30, df_h1):
    """
    Analisa sinyal entry berdasarkan aturan multi-timeframe.
    df_m5, df_m15, df_m30, df_h1: DataFrame OHLCV untuk masing-masing timeframe.
    Return: 'BUY', 'SELL', atau None
    """
    # --- Hapus seluruh kode yang menggunakan ta.ema, ta.stoch, dst ---
    # Ganti dengan return None agar tidak error dan PPO agent selalu digunakan
    return None

def get_daily_closed_profit(log_file="log_transaksi.csv"):
    """
    Menghitung total profit harian dari transaksi yang sudah closed pada hari ini.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    total_profit = 0.0
    try:
        if not os.path.isfile(log_file):
            return 0.0
        with open(log_file, mode="r", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Filter hanya transaksi closed hari ini
                if row["action"] in ["Close Trade", "Profit Target", "Daily Target"] and row["status"] == "Successful":
                    if row["timestamp"].startswith(today):
                        # Ambil nilai profit dari details jika ada
                        details = row["details"]
                        # Contoh details: "Profit: $12.34" atau "Position: 123456, Volume: 0.05"
                        if "Profit:" in details:
                            try:
                                profit_str = details.split("Profit: $")[-1].split()[0]
                                profit_val = float(profit_str)
                                total_profit += profit_val
                            except:
                                continue
        return total_profit
    except Exception as e:
        print(f"[ERROR] Gagal membaca profit harian dari log: {e}")
        return 0.0

# === Windowed trading control (HFT tuning) ===
WINDOW_OPEN_LIMIT = args.window_open_limit
window_open_count = 0
window_initialized = False
is_pause_window = False
active_end_ts = 0.0
pause_end_ts = 0.0

# Get account number for per-account window status file
try:
    _account_info = mt5.account_info()
    _account_number = _account_info.login if _account_info else "N/A"
except Exception:
    _account_number = "N/A"

WINDOW_STATUS_FILE = f"window_status_{_account_number}.json"

def update_window_status(window_open_count, window_limit, window_time_left, is_pause):
    """
    Update status window trading ke file JSON agar bisa dibaca oleh GUI launcher.
    """
    status = {
        "window_open_count": window_open_count,
        "window_limit": window_limit,
        "window_time_left": window_time_left,
        "is_pause": is_pause
    }
    try:
        # Gunakan file status per akun
        with open(WINDOW_STATUS_FILE, "w") as f:
            import json
            json.dump(status, f)
    except Exception as e:
        print_with_account(f"[ERROR] Gagal update {WINDOW_STATUS_FILE}: {e}")

def update_trading_report():
    """
    Membuat/memperbarui laporan trading per akun dalam bentuk CSV.
    File: trading_report_{account_number}.csv
    Kolom: timestamp, balance, equity, margin, free_margin, open_trades, floating_profit, daily_closed_profit
    """
    try:
        account_info = mt5.account_info()
        if account_info is None:
            return
        account_number = account_info.login
        report_file = f"trading_report_{account_number}.csv"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        open_trades = get_open_trades()
        floating_profit = sum(trade.profit for trade in open_trades)
        daily_closed_profit = get_daily_closed_profit()
        row = {
            "timestamp": timestamp,
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin": account_info.margin,
            "free_margin": account_info.margin_free,
            "open_trades": len(open_trades),
            "floating_profit": floating_profit,
            "daily_closed_profit": daily_closed_profit
        }
        file_exists = os.path.isfile(report_file)
        with open(report_file, mode="a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        print(f"[ERROR] Gagal update trading report: {e}")

def trading_loop():
    print_with_account("Memulai loop trading (HFT mode)...")
    daily_profit = 0
    start_of_day = datetime.now().date()
    max_dd_hit_count = 0

    global window_initialized, is_pause_window, active_end_ts, pause_end_ts, window_open_count
    global baseline_equity  # <- gunakan baseline yang disimpan di start

    last_open_time = 0  # Tambahkan variabel untuk waktu open posisi terakhir

    pause_until_next_day = False
    pause_resume_time = None

    while True:
        now = time.time()

        # === PAUSE SAMPAI BESOK JAM 4:00 JIKA 3 KALI CUTLOSS ===
        if pause_until_next_day:
            now_dt = datetime.now()
            if now_dt >= pause_resume_time:
                print_with_account(f"Waktu tunggu selesai, trading pair {symbol} dilanjutkan.")
                pause_until_next_day = False
                max_dd_hit_count = 0
                start_of_day = datetime.now().date()
                # Reset window state
                window_initialized = False
                continue
            sisa = (pause_resume_time - now_dt).total_seconds()
            jam = int(sisa // 3600)
            menit = int((sisa % 3600) // 60)
            print_with_account(f"Trading pair {symbol} akan dilanjutkan pada {pause_resume_time.strftime('%Y-%m-%d %H:%M')}. Sisa waktu: {jam} jam {menit} menit.")
            time.sleep(60)
            continue

        # === Window state machine ===
        if not window_initialized:
            window_initialized = True
            is_pause_window = False
            active_end_ts = now + WINDOW_ON_SECONDS  # gunakan argumen (HFT kecil)
            window_open_count = 0
            last_open_time = 0  # Reset waktu open posisi terakhir saat window ON baru
            print_with_account(f"=== MODE: TRADING AKTIF ({WINDOW_ON_SECONDS}s, max {WINDOW_OPEN_LIMIT} open) ===")
        # Update status file setiap loop
        window_time_left = int(active_end_ts - now) if not is_pause_window else int(pause_end_ts - now)
        update_window_status(window_open_count, WINDOW_OPEN_LIMIT, window_time_left, is_pause_window)

        # --- CEK FLOATING PROFIT SAAT PAUSE/AKTIF ---
        open_trades = get_open_trades()
        cumulative_profit = sum(trade.profit for trade in open_trades)
        if cumulative_profit >= 0.5:
            print_with_account(f"[AUTO CLOSE] Floating profit mencapai ${cumulative_profit:.2f} (>= $0.5). Menutup semua posisi...")
            log_to_csv("Auto Close", "Floating Profit >= 0.5", f"Profit: ${cumulative_profit:.2f}")
            close_all_trades()
            time.sleep(0.05)
            continue

        if is_pause_window:
            remaining = int(pause_end_ts - now)
            if remaining > 0:
                mm, ss = divmod(max(0, remaining), 60)
                print_with_account(f"PAUSE: {mm:02d}:{ss:02d} tersisa sebelum trading aktif lagi...")
                time.sleep(0.1)
                continue
            # end pause -> switch to active window
            is_pause_window = False
            active_end_ts = time.time() + WINDOW_ON_SECONDS
            window_open_count = 0
            print_with_account(f"=== MODE: TRADING AKTIF ({WINDOW_ON_SECONDS}s, max {WINDOW_OPEN_LIMIT} open) ===")

        # if active window time elapsed or open limit reached -> switch to pause
        if (now >= active_end_ts) or (window_open_count >= WINDOW_OPEN_LIMIT):
            is_pause_window = True
            pause_end_ts = time.time() + WINDOW_PAUSE_SECONDS  # gunakan argumen (HFT singkat)
            window_time_left = int(pause_end_ts - time.time())
            update_window_status(window_open_count, WINDOW_OPEN_LIMIT, window_time_left, True)
            print_with_account(f"=== MODE: PAUSE ({WINDOW_PAUSE_SECONDS}s) ===")
            continue

        # --- Reset harian ---
        if datetime.now().date() != start_of_day:
            daily_profit = 0
            start_of_day = datetime.now().date()
            max_dd_hit_count = 0  # Reset counter setiap hari baru
            print_with_account("-" * 50)
            print_with_account(f"Memulai hari baru. Target harian dan max_dd_hit_count diatur ulang.")
            print_with_account("-" * 50)

        current_time = datetime.now()
        current_hour = current_time.hour

        # Jika max_dd tercapai 3x, hentikan trading sampai hari berikutnya jam 4:00 WIB
        if max_dd_hit_count >= 3:
            print_with_account(f"[PERINGATAN] Max drawdown tercapai 3 kali hari ini untuk pair {symbol}. Semua posisi akan ditutup dan trading dihentikan sampai besok jam 04:00.")
            close_all_trades()
            log_to_csv("Max Drawdown", "Stop Trading", f"Pair: {symbol}, Trading dihentikan sampai besok jam 04:00")
            now_dt = datetime.now()
            # Hitung waktu resume trading besok jam 4:00 WIB
            if now_dt.hour < 4:
                pause_resume_time = now_dt.replace(hour=4, minute=0, second=0, microsecond=0)
            else:
                pause_resume_time = (now_dt + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
            pause_until_next_day = True
            continue

        if current_hour < args.start_trading_hour or current_hour >= args.end_trading_hour:
            # Hitung waktu hingga jendela trading berikutnya
            if current_hour < args.start_trading_hour:
                next_trading_time = current_time.replace(hour=args.start_trading_hour, minute=0, second=0, microsecond=0)
            else:
                next_trading_time = (current_time + timedelta(days=1)).replace(hour=args.start_trading_hour, minute=0, second=0, microsecond=0)
            time_until_next_trading = next_trading_time - current_time
            hours, remainder = divmod(time_until_next_trading.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            print_with_account(f"Waktu saat ini: {current_time.strftime('%H:%M:%S')}. Di luar jam trading ({args.start_trading_hour}:00-{args.end_trading_hour}:00).")
            print_with_account(f"Menunggu hingga trading dimulai dalam {hours} jam, {minutes} menit, dan {seconds} detik...")
            time.sleep(2)
            continue

        # Mengambil informasi akun dan trading
        print_with_account("-" * 50)
        print_with_account("Mengambil informasi akun dan trading...")
        account_info = get_account_info()
        daily_closed_profit = get_daily_closed_profit()
        print_with_account(f"Total profit harian (closed): ${daily_closed_profit:.2f}")
        # Check cumulative profit
        open_trades = get_open_trades()
        cumulative_profit = sum(trade.profit for trade in open_trades)
        print_with_account(f"Total profit saat ini: ${cumulative_profit:.2f}")
        log_to_csv("Cumulative Profit", "Checked", f"Profit: ${cumulative_profit:.2f}")

        # === CLOSE ALL jika floating profit >= 2.0 ===
        if cumulative_profit >= 2.0:
            print_with_account(f"[AUTO CLOSE] Floating profit mencapai ${cumulative_profit:.2f} (>= $2.0). Menutup semua posisi...")
            log_to_csv("Auto Close", "Floating Profit >= 2.0", f"Profit: ${cumulative_profit:.2f}")
            close_all_trades()
            print_with_account("Lanjut ke iterasi berikutnya...")
            time.sleep(2)
            continue

        # Cek floating minus (cumulative_profit < 0) dan profit harian sudah melebihi floating minus minimal $5
        if cumulative_profit < 0 and daily_closed_profit > abs(cumulative_profit) and abs(cumulative_profit) >= 5:
            print_with_account(f"Profit harian sudah melebihi floating minus minimal $5. Semua posisi akan ditutup.")
            log_to_csv("Close All", "By Daily Profit", f"Profit harian: ${daily_closed_profit:.2f}, Floating minus: ${cumulative_profit:.2f}")
            close_all_trades()
            print_with_account("Lanjut ke iterasi berikutnya...")
            time.sleep(2)
            continue
        print_with_account(f"Nomor Akun: {account_info.login}")
        print_with_account(f"Nama Akun: {account_info.name}")
        print_with_account(f"Margin Bebas: {account_info.margin_free}")
        print_with_account("-" * 50)

        # --- CEK MAX DRAWDOWN ---
        equity = account_info.equity
        balance = account_info.balance
        if balance > 0:
            drawdown_pct = ((balance - equity) / balance) * 100
        else:
            drawdown_pct = 0
        print_with_account(f"Drawdown saat ini: {drawdown_pct:.2f}% dari saldo akun.")
        log_to_csv("Drawdown", "Checked", f"Drawdown: {drawdown_pct:.2f}%")

        if drawdown_pct >= args.max_dd:
            max_dd_hit_count += 1
            print_with_account(f"[PERINGATAN] Max drawdown tercapai ({drawdown_pct:.2f}% >= {args.max_dd}%). Menutup semua posisi... (Hit ke-{max_dd_hit_count}/3)")
            log_to_csv("Max Drawdown", f"Tercapai ke-{max_dd_hit_count}", f"Drawdown: {drawdown_pct:.2f}%")
            close_all_trades()
            print_with_account("Lanjut ke iterasi berikutnya...")
            time.sleep(2)
            continue

        # Check cumulative profit
        open_trades = get_open_trades()
        cumulative_profit = sum(trade.profit for trade in open_trades)
        print_with_account(f"Total profit saat ini: ${cumulative_profit:.2f}")
        log_to_csv("Cumulative Profit", "Checked", f"Profit: ${cumulative_profit:.2f}")
        if cumulative_profit >= close_profit:
            print_with_account(f"Target profit tercapai: ${cumulative_profit:.2f}. Menutup semua posisi...")
            log_to_csv("Profit Target", "Tercapai", f"Profit: ${cumulative_profit:.2f}")
            close_all_trades()
            print_with_account("Lanjut ke iterasi berikutnya...")
            time.sleep(2)
            continue

        # Calculate daily profit as a percentage of the account balance
        daily_profit += cumulative_profit
        daily_profit_percentage = (daily_profit / account_info.balance) * 100
        print_with_account(f"Profit harian saat ini: {daily_profit_percentage:.2f}% dari saldo akun.")

        # Check if daily profit target is reached
        floating_minus_pct = abs(cumulative_profit) / account_info.balance * 100 if cumulative_profit < 0 else 0
        effective_daily_profit = daily_profit_percentage - floating_minus_pct
        print_with_account(f"Effective daily profit (setelah floating minus): {effective_daily_profit:.2f}% dari saldo akun.")

        # --- NEW: close jika equity sudah mencapai baseline + daily_target% ---
        try:
            current_equity = account_info.equity
            if baseline_equity and baseline_equity > 0:
                target_equity = baseline_equity * (1 + (args.daily_target / 100.0))
                if current_equity >= target_equity:
                    print_with_account(f"[BASELINE TARGET] Equity mencapai target berdasarkan baseline: {current_equity:.2f} >= {target_equity:.2f}. Menutup semua posisi...")
                    log_to_csv("Baseline Target", "Tercapai", f"Equity: {current_equity:.2f}, Baseline: {baseline_equity:.2f}, Daily Target%: {args.daily_target}")
                    close_all_trades()
                    # Simpan baseline baru agar tidak langsung trigger lagi di sesi yang sama (opsional)
                    save_baseline_equity(account_number, baseline_equity)  # keep same baseline or update as desired
                    # PAUSE sampai besok jam 04:00 WIB (sama seperti original flow)
                    now_dt = datetime.now()
                    target_time = (now_dt + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
                    if now_dt.hour < 4:
                        target_time = now_dt.replace(hour=4, minute=0, second=0, microsecond=0)
                    print_with_account(f"Trading akan dilanjutkan pada {target_time.strftime('%Y-%m-%d %H:%M')}.")
                    while True:
                        now_dt = datetime.now()
                        if now_dt >= target_time:
                            print_with_account(f"Waktu tunggu selesai, trading dilanjutkan.")
                            break
                        sisa = (target_time - now_dt).total_seconds()
                        jam = int(sisa // 3600); menit = int((sisa % 3600) // 60)
                        print_with_account(f"Trading akan dilanjutkan pada {target_time.strftime('%Y-%m-%d %H:%M')}. Sisa waktu: {jam} jam {menit} menit.")
                        time.sleep(300)  # cek setiap 5 menit
                    daily_profit = 0
                    start_of_day = datetime.now().date()
                    continue
        except Exception as e:
            print_with_account(f"[ERROR] Pengecekan baseline equity gagal: {e}")
        # --- END NEW ---

        if effective_daily_profit >= args.daily_target:
            print_with_account(f"Target harian tercapai (setelah floating minus): {effective_daily_profit:.2f}%. Menutup semua posisi...")
            log_to_csv("Daily Target", "Tercapai", f"Profit efektif: {effective_daily_profit:.2f}")
            close_all_trades()
            # PAUSE sampai besok jam 04:00 WIB
            now_dt = datetime.now()
            target_time = (now_dt + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
            if now_dt.hour < 4:
                target_time = now_dt.replace(hour=4, minute=0, second=0, microsecond=0)
            print_with_account(f"Trading akan dilanjutkan pada {target_time.strftime('%Y-%m-%d %H:%M')}.")
            while True:
                now_dt = datetime.now()
                if now_dt >= target_time:
                    print_with_account(f"Waktu tunggu selesai, trading dilanjutkan.")
                    break
                sisa = (target_time - now_dt).total_seconds()
                jam = int(sisa // 3600); menit = int((sisa % 3600) // 60)
                print_with_account(f"Trading akan dilanjutkan pada {target_time.strftime('%Y-%m-%d %H:%M')}. Sisa waktu: {jam} jam {menit} menit.")
                time.sleep(300)  # cek setiap 5 menit
            daily_profit = 0
            start_of_day = datetime.now().date()
            continue

        # Get margin per lot
        margin_per_lot = get_margin_per_lot(symbol)
        if margin_per_lot is not None:
            print_with_account(f"Margin per lot untuk {symbol}: {margin_per_lot}")
            print_with_account("-" * 50)
            suggested_lot = calculate_suggested_lot(account_info.margin_free, risk_percentage=1, lot_min=0.01, lot_step=0.01, margin_per_lot=margin_per_lot, lot_max=10)
            print_with_account(f"Ukuran Lot yang Disarankan: {suggested_lot}")
            log_to_csv("Suggested Lot", "Calculated", f"Account: {account_info.login}, Suggested Lot: {suggested_lot}, Margin per Lot: {margin_per_lot}")
        else:
            print_with_account(f"[ERROR] Unable to calculate suggested lot size for {symbol}")
            print_with_account("-" * 50)

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is not None:
            margin_per_lot = symbol_info.margin_initial
            print_with_account(f"Margin per lot untuk {symbol}: {margin_per_lot}")
        else:
            print_with_account(f"Failed to fetch symbol info for {symbol}")

        open_trades = get_open_trades()

        log_to_csv("Account Info", "Fetched", f"Account Number: {account_info.login}, Account Name: {account_info.name}, Free Margin: {account_info.margin_free}")

        actual_spread = get_actual_spread(symbol)
        if actual_spread is not None:
            log_to_csv("Spread", "Checked", f"Actual Spread: {actual_spread:.5f}")

        cumulative_profit = sum(trade.profit for trade in open_trades)
        print_with_account(f"Total profit: ${cumulative_profit:.2f}")
        log_to_csv("Cumulative Profit", "Checked", f"Profit: ${cumulative_profit:.2f}")
        if cumulative_profit >= close_profit:
            print_with_account(f"Target profit tercapai: ${cumulative_profit:.2f}")
            log_to_csv("Profit Target", "Reached", f"Profit: ${cumulative_profit:.2f}")
            close_all_trades()
            continue

        print_with_account(f"Jumlah posisi terbuka: {len(open_trades)}")
        log_to_csv("Open Trades", "Checked", f"Count: {len(open_trades)}")
        if len(open_trades) >= max_open_trades:
            print_with_account(f"Batas maksimal posisi terbuka tercapai: {len(open_trades)}")
            log_to_csv("Max Open Trades", "Reached", f"Count: {len(open_trades)}")
            time.sleep(2)
            continue

        print_with_account("Mengambil data pasar multi-timeframe...")
        rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 120)
        rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 120)
        rates_m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 120)
        rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 120)
        if (rates_m5 is None or len(rates_m5) < 10 or
            rates_m15 is None or len(rates_m15) < 100 or
            rates_m30 is None or len(rates_m30) < 55 or
            rates_h1 is None or len(rates_h1) < 55):
            print_with_account("Data pasar multi-timeframe tidak mencukupi")
            log_to_csv("Market Data", "Insufficient", "Multi-timeframe rates not enough")
            time.sleep(2)
            continue

        df_m5 = pd.DataFrame(rates_m5)
        df_m15 = pd.DataFrame(rates_m15)
        df_m30 = pd.DataFrame(rates_m30)
        df_h1 = pd.DataFrame(rates_h1)

        signal = analyze_entry_signal(df_m5, df_m15, df_m30, df_h1)
        print_with_account(f"Sinyal analisa manual: {signal}")

        # Tentukan action dari sinyal manual
        if signal == 'BUY':
            action = 2 #reverse
        elif signal == 'SELL':
            action = 1 #reverse
        else:
            action = None

        # Jika tidak ada sinyal manual, gunakan PPO agent
        if action is None:
            print_with_account("Tidak ada sinyal manual, menggunakan PPO agent...")
            close_prices = np.array([rate['close'] for rate in rates_m5], dtype=np.float32)
            obs = close_prices[-4:].reshape(1, -1)
            action, _ = ppo_agent.predict(obs)
            print_with_account(f"Aksi agen PPO: {action}")
            log_to_csv("PPO Action", "Predicted", f"Action: {action}")

        # Reverse Trading jika argumen aktif
        if args.reverse:
            if action == 2:
                action = 1
            elif action == 1:
                action = 2
            print_with_account("[INFO] Reverse Trading Aktif: Aksi dibalik.")

        # === Apply per-window open trade limit & 1s interval (HFT) ===
        if action == 2 or action == 1:
            if window_open_count >= WINDOW_OPEN_LIMIT:
                print_with_account(f"[INFO] Batas {WINDOW_OPEN_LIMIT} transaksi pada jendela aktif tercapai. Menunggu ke PAUSE.")
            else:
                # Cek jeda 1 detik antar open posisi (HFT)
                if last_open_time == 0 or (time.time() - last_open_time) >= 1:
                    if action == 2:
                        place_trade(2)
                    elif action == 1:
                        place_trade(1)
                    window_open_count += 1
                    last_open_time = time.time()
                    # Update status file setiap kali open trade
                    window_time_left = int(active_end_ts - time.time())
                    update_window_status(window_open_count, WINDOW_OPEN_LIMIT, window_time_left, False)
                    print_with_account(f"[INFO] Transaksi dibuka pada jendela ini: {window_open_count}/{WINDOW_OPEN_LIMIT}")
                else:
                    sisa = 1 - (time.time() - last_open_time)
                    print_with_account(f"[INFO] Menunggu jeda {max(0,int(sisa))} detik sebelum open posisi berikutnya.")
        else:
            print_with_account("Aksi tahan terdeteksi, tidak ada trading yang dilakukan.")
            log_to_csv("PPO Action", "Hold", "No trade placed")

        # Update trading report setiap iterasi utama
        update_trading_report()

        print_with_account("Menunggu singkat sebelum iterasi berikutnya...")
        time.sleep(0.05)  # HFT: loop cepat

# Start trading loop
try:
    trading_loop()
except KeyboardInterrupt:
    print("Loop trading dihentikan")
finally:
    print("Menutup MetaTrader 5...")
    mt5.shutdown()

def trading_loop_with_timer():
    print_with_account("Memulai loop trading dengan timer siklikal (HFT mode)...")
    daily_profit = 0
    start_of_day = datetime.now().date()
    max_dd_hit_count = 0  # Tambahkan penghitung max_dd tercapai

    global baseline_equity  # gunakan baseline juga di sini

    while True:
        # === ON: Trading aktif selama window ON (HFT) ===
        print_with_account(f"=== MODE: TRADING AKTIF ({WINDOW_ON_SECONDS}s) ===")
        on_start = time.time()
        trade_executed = False  # Tambahkan flag untuk mendeteksi transaksi
        while (time.time() - on_start) < WINDOW_ON_SECONDS:
            # Reset daily profit dan max_dd_hit_count di hari baru
            if datetime.now().date() != start_of_day:
                daily_profit = 0
                start_of_day = datetime.now().date()
                max_dd_hit_count = 0
                print_with_account("-" * 50)
                print_with_account(f"Memulai hari baru. Target harian dan max_dd_hit_count diatur ulang.")
                print_with_account("-" * 50)

            current_time = datetime.now()
            current_hour = current_time.hour

            if max_dd_hit_count >= 3:
                print_with_account(f"[PERINGATAN] Max drawdown tercapai 3 kali hari ini untuk pair {symbol}. Semua posisi akan ditutup dan trading dihentikan sampai besok jam 04:00.")
                close_all_trades()
                log_to_csv("Max Drawdown", "Stop Trading", f"Pair: {symbol}, Trading dihentikan sampai besok jam 04:00")
                now_dt = datetime.now()
                # Hitung waktu resume trading besok jam 4:00 WIB
                if now_dt.hour < 4:
                    pause_resume_time = now_dt.replace(hour=4, minute=0, second=0, microsecond=0)
                else:
                    pause_resume_time = (now_dt + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
                pause_until_next_day = True
                continue

            if current_hour < args.start_trading_hour or current_hour >= args.end_trading_hour:
                # Hitung waktu hingga jendela trading berikutnya
                if current_hour < args.start_trading_hour:
                    next_trading_time = current_time.replace(hour=args.start_trading_hour, minute=0, second=0, microsecond=0)
                else:
                    next_trading_time = (current_time + timedelta(days=1)).replace(hour=args.start_trading_hour, minute=0, second=0, microsecond=0)
                time_until_next_trading = next_trading_time - current_time
                hours, remainder = divmod(time_until_next_trading.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                print_with_account(f"Waktu saat ini: {current_time.strftime('%H:%M:%S')}. Di luar jam trading ({args.start_trading_hour}:00-{args.end_trading_hour}:00).")
                print_with_account(f"Menunggu hingga trading dimulai dalam {hours} jam, {minutes} menit, dan {seconds} detik...")
                time.sleep(2)
                continue

            # Mengambil informasi akun dan trading
            print_with_account("-" * 50)
            print_with_account("Mengambil informasi akun dan trading...")
            account_info = get_account_info()
            daily_closed_profit = get_daily_closed_profit()
            print_with_account(f"Total profit harian (closed): ${daily_closed_profit:.2f}")
            # Check cumulative profit
            open_trades = get_open_trades()
            cumulative_profit = sum(trade.profit for trade in open_trades)
            print_with_account(f"Total profit saat ini: ${cumulative_profit:.2f}")
            log_to_csv("Cumulative Profit", "Checked", f"Profit: ${cumulative_profit:.2f}")

            # === CLOSE ALL jika floating profit >= 0.5 ===
            if cumulative_profit >= 0.5:
                print_with_account(f"[AUTO CLOSE] Floating profit mencapai ${cumulative_profit:.2f} (>= $0.5). Menutup semua posisi...")
                log_to_csv("Auto Close", "Floating Profit >= 0.5", f"Profit: ${cumulative_profit:.2f}")
                close_all_trades()
                print_with_account("Lanjut ke iterasi berikutnya...")
                time.sleep(2)
                continue

            # Cek floating minus (cumulative_profit < 0) dan profit harian sudah melebihi floating minus minimal $5
            if cumulative_profit < 0 and daily_closed_profit > abs(cumulative_profit) and abs(cumulative_profit) >= 5:
                print_with_account(f"Profit harian sudah melebihi floating minus minimal $5. Semua posisi akan ditutup.")
                log_to_csv("Close All", "By Daily Profit", f"Profit harian: ${daily_closed_profit:.2f}, Floating minus: ${cumulative_profit:.2f}")
                close_all_trades()
                print_with_account("Lanjut ke iterasi berikutnya...")
                time.sleep(2)
                continue
            print_with_account(f"Nomor Akun: {account_info.login}")
            print_with_account(f"Nama Akun: {account_info.name}")
            print_with_account(f"Margin Bebas: {account_info.margin_free}")
            print_with_account("-" * 50)

            # --- CEK MAX DRAWDOWN ---
            equity = account_info.equity
            balance = account_info.balance
            if balance > 0:
                drawdown_pct = ((balance - equity) / balance) * 100
            else:
                drawdown_pct = 0
            print_with_account(f"Drawdown saat ini: {drawdown_pct:.2f}% dari saldo akun.")
            log_to_csv("Drawdown", "Checked", f"Drawdown: {drawdown_pct:.2f}%")

            if drawdown_pct >= args.max_dd:
                max_dd_hit_count += 1
                print_with_account(f"[PERINGATAN] Max drawdown tercapai ({drawdown_pct:.2f}% >= {args.max_dd}%). Menutup semua posisi... (Hit ke-{max_dd_hit_count}/3)")
                log_to_csv("Max Drawdown", f"Tercapai ke-{max_dd_hit_count}", f"Drawdown: {drawdown_pct:.2f}%")
                close_all_trades()
                print_with_account("Lanjut ke iterasi berikutnya...")
                time.sleep(2)
                continue

            # Check cumulative profit
            open_trades = get_open_trades()
            cumulative_profit = sum(trade.profit for trade in open_trades)
            print_with_account(f"Total profit saat ini: ${cumulative_profit:.2f}")
            log_to_csv("Cumulative Profit", "Checked", f"Profit: ${cumulative_profit:.2f}")
            if cumulative_profit >= close_profit:
                print_with_account(f"Target profit tercapai: ${cumulative_profit:.2f}. Menutup semua posisi...")
                log_to_csv("Profit Target", "Tercapai", f"Profit: ${cumulative_profit:.2f}")
                close_all_trades()
                print_with_account("Lanjut ke iterasi berikutnya...")
                time.sleep(2)
                continue

            # Calculate daily profit as a percentage of the account balance
            daily_profit += cumulative_profit
            daily_profit_percentage = (daily_profit / account_info.balance) * 100
            print_with_account(f"Profit harian saat ini: {daily_profit_percentage:.2f}% dari saldo akun.")

            # Check if daily profit target is reached
            floating_minus_pct = abs(cumulative_profit) / account_info.balance * 100 if cumulative_profit < 0 else 0
            effective_daily_profit = daily_profit_percentage - floating_minus_pct
            print_with_account(f"Effective daily profit (setelah floating minus): {effective_daily_profit:.2f}% dari saldo akun.")

            # --- NEW: close jika equity sudah mencapai baseline + daily_target% (timer loop) ---
            try:
                current_equity = account_info.equity
                if baseline_equity and baseline_equity > 0:
                    target_equity = baseline_equity * (1 + (args.daily_target / 100.0))
                    if current_equity >= target_equity:
                        print_with_account(f"[BASELINE TARGET] Equity mencapai target berdasarkan baseline: {current_equity:.2f} >= {target_equity:.2f}. Menutup semua posisi...")
                        log_to_csv("Baseline Target", "Tercapai", f"Equity: {current_equity:.2f}, Baseline: {baseline_equity:.2f}, Daily Target%: {args.daily_target}")
                        close_all_trades()
                        save_baseline_equity(account_number, baseline_equity)
                        now_dt = datetime.now()
                        target_time = (now_dt + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
                        if now_dt.hour < 4:
                            target_time = now_dt.replace(hour=4, minute=0, second=0, microsecond=0)
                        print_with_account(f"Trading akan dilanjutkan pada {target_time.strftime('%Y-%m-%d %H:%M')}.")
                        while True:
                            now_dt = datetime.now()
                            if now_dt >= target_time:
                                print_with_account(f"Waktu tunggu selesai, trading dilanjutkan.")
                                break
                            sisa = (target_time - now_dt).total_seconds()
                            jam = int(sisa // 3600); menit = int((sisa % 3600) // 60)
                            print_with_account(f"Trading akan dilanjutkan pada {target_time.strftime('%Y-%m-%d %H:%M')}. Sisa waktu: {jam} jam {menit} menit.")
                            time.sleep(300)  # cek setiap 5 menit
                        daily_profit = 0
                        start_of_day = datetime.now().date()
                        continue
            except Exception as e:
                print_with_account(f"[ERROR] Pengecekan baseline equity gagal (timer loop): {e}")
            # --- END NEW ---

            if effective_daily_profit >= args.daily_target:
                print_with_account(f"Target harian tercapai (setelah floating minus): {effective_daily_profit:.2f}%. Menutup semua posisi...")
                log_to_csv("Daily Target", "Tercapai", f"Profit efektif: {effective_daily_profit:.2f}")
                close_all_trades()
                # PAUSE sampai besok jam 04:00 WIB
                now_dt = datetime.now()
                target_time = (now_dt + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
                if now_dt.hour < 4:
                    target_time = now_dt.replace(hour=4, minute=0, second=0, microsecond=0)
                print_with_account(f"Trading akan dilanjutkan pada {target_time.strftime('%Y-%m-%d %H:%M')}.")
                while True:
                    now_dt = datetime.now()
                    if now_dt >= target_time:
                        print_with_account(f"Waktu tunggu selesai, trading dilanjutkan.")
                        break
                    sisa = (target_time - now_dt).total_seconds()
                    jam = int(sisa // 3600); menit = int((sisa % 3600) // 60)
                    print_with_account(f"Trading akan dilanjutkan pada {target_time.strftime('%Y-%m-%d %H:%M')}. Sisa waktu: {jam} jam {menit} menit.")
                    time.sleep(300)  # cek setiap 5 menit
                daily_profit = 0
                start_of_day = datetime.now().date()
                continue
        # === END window ON ===

        # === MODIFIKASI: hanya masuk PAUSE jika ada transaksi ===
        if trade_executed:
            print_with_account(f"=== MODE: PAUSE ({WINDOW_PAUSE_SECONDS}s) ===")
            pause_start = time.time()
            while (time.time() - pause_start) < WINDOW_PAUSE_SECONDS:
                open_trades = get_open_trades()
                floating_profit = sum(trade.profit for trade in open_trades)
                if floating_profit >= 1.5:
                    print_with_account(f"[AUTO CLOSE] Floating profit mencapai ${floating_profit:.2f} (>= $1.5) saat PAUSE. Menutup semua posisi...")
                    close_all_trades()
                print_with_account("PAUSE: Tidak ada open trade baru. Menunggu...")
                time.sleep(0.5)
            # Setelah PAUSE, loop kembali ke window ON berikutnya
        else:
            print_with_account("Tidak ada transaksi selama window ON. Mengulangi mode ON berikutnya tanpa masuk PAUSE.")