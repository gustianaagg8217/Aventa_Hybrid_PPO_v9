import tkinter as tk
from tkinter import filedialog
import subprocess
import MetaTrader5 as mt5  # type: ignore
import json  # Tambahkan import untuk JSON
import os
import signal
import time  # Tambahkan import untuk time
import threading
import csv  # Tambahkan import untuk CSV
from tkinter import ttk  # Tambahkan import ttk
from plyer import notification 
import argparse
from tkinter import Tk, filedialog

CONFIG_FILE = "bot_config.json"  # Nama file konfigurasi
WINDOW_STATUS_FILE = "window_status.json"

def get_suggested_target_profit(log_file="log_transaksi.csv", symbol=""):
    try:
        with open(log_file, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Lewati header
            for row in reversed(list(reader)):  # Baca dari baris terakhir
                if len(row) > 3 and row[1] == symbol and "Target Profit" in row[2]:
                    return float(row[3].strip())
        return None  # Tidak ada data target profit untuk simbol
    except Exception as e:
        print(f"[ERROR] Failed to read suggested target profit: {e}")
        return None

def get_account_info():
    """Mengambil informasi akun dari MetaTrader 5."""
    account_info = mt5.account_info()
    if account_info is None:
        print("[ERROR] Gagal mendapatkan informasi akun dari MT5.")
        return None
    return account_info

class BotRow:
    def __init__(self, master, row, app):
        self.app = app  # simpan referensi ke BotLauncherApp
        self.symbol_var = tk.StringVar()
        self.lot_var = tk.StringVar()
        self.dd_var = tk.StringVar()
        self.path_var = tk.StringVar()
        self.type_filling_var = tk.StringVar(value="ORDER_FILLING_IOC")  # Default tipe pengisian
        self.max_spread_var = tk.StringVar()  # Tambahkan variabel untuk Max Spread
        self.account_number_var = tk.StringVar(value="N/A")  # Variabel untuk Nomor Akun
        self.account_name_var = tk.StringVar(value="N/A")  # Variabel untuk Nama Akun
        self.status_var = tk.StringVar(value="Stopped")
        self.process = None
        self.max_open_trades_var = tk.StringVar()  # Variabel untuk Max Open Trades
        self.close_profit_var = tk.StringVar()  # Variabel untuk Close Profit
        self.ppo_model_path_var = tk.StringVar(value="")  # Tambahkan variabel untuk PPO model path
        self.start_hour_var = tk.StringVar(value="9")  # Default start trading hour
        self.end_hour_var = tk.StringVar(value="17")  # Default end trading hour
        self.daily_target_var = tk.StringVar(value="10.0")  # Default daily target 2%
        # HFT: lebih banyak open per window default
        self.window_open_limit_var = tk.StringVar(value="50")  # Default 50 untuk HFT

        # Input Symbol
        self.symbol_entry = tk.Entry(master, textvariable=self.symbol_var, width=10)
        self.symbol_entry.grid(row=row, column=0)

        # Input Lot
        self.lot_entry = tk.Entry(master, textvariable=self.lot_var, width=5)
        self.lot_entry.grid(row=row, column=1)

        # Input Max DD
        self.dd_entry = tk.Entry(master, textvariable=self.dd_var, width=3)
        self.dd_entry.grid(row=row, column=2)

        # Terminal path input
        self.path_entry = tk.Entry(master, textvariable=self.path_var, width=18)
        self.path_entry.grid(row=row, column=3)

        # Browse button for terminal path
        self.browse_button = tk.Button(master, text="Browse", command=self.browse_path)
        self.browse_button.grid(row=row, column=4)

        # Dropdown untuk Type Filling
        self.type_filling_dropdown = ttk.Combobox(
            master, textvariable=self.type_filling_var, width=4, state="readonly"
        )
        self.type_filling_dropdown['values'] = [
            "FOK",  # Fill or Kill
            "IOC",  # Immediate or Cancel
            "RET"   # Return
        ]
        self.type_filling_dropdown.grid(row=row, column=5)

        # Max Spread input
        self.max_spread_entry = tk.Entry(master, textvariable=self.max_spread_var, width=7)
        self.max_spread_entry.grid(row=row, column=6)

        # Input Max Open Trades
        self.max_open_trades_entry = tk.Entry(master, textvariable=self.max_open_trades_var, width=3)
        self.max_open_trades_entry.grid(row=row, column=7)

        # Input Close Profit
        self.close_profit_entry = tk.Entry(master, textvariable=self.close_profit_var, width=3)
        self.close_profit_entry.grid(row=row, column=8)

        # PPO Model Path input
        self.ppo_model_entry = tk.Entry(master, textvariable=self.ppo_model_path_var, width=15)
        self.ppo_model_entry.grid(row=row, column=9)

        # Browse button for PPO model path
        self.browse_ppo_button = tk.Button(master, text="Browse PPO", command=self.browse_ppo_model)
        self.browse_ppo_button.grid(row=row, column=10)

        # Account Number label
        self.account_number_label = tk.Label(master, textvariable=self.account_number_var, width=8)
        self.account_number_label.grid(row=row, column=11)

        # Account Name label
        self.account_name_label = tk.Label(master, textvariable=self.account_name_var, width=20)
        self.account_name_label.grid(row=row, column=12)

        # Status label
        self.status_label = tk.Label(master, textvariable=self.status_var, width=7, bg="red", fg="white")
        self.status_label.grid(row=row, column=13)

        # Start and Stop buttons
        self.start_button = tk.Button(master, text="Start", command=self.start_bot)
        self.start_button.grid(row=row, column=17)

        self.stop_button = tk.Button(master, text="Stop", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.grid(row=row, column=18)

        # Input Start Trading Hour
        self.start_hour_entry = tk.Entry(master, textvariable=self.start_hour_var, width=2)
        self.start_hour_entry.grid(row=row, column=14)

        # Input End Trading Hour
        self.end_hour_entry = tk.Entry(master, textvariable=self.end_hour_var, width=2)
        self.end_hour_entry.grid(row=row, column=15)

        # Input Daily Target
        self.daily_target_entry = tk.Entry(master, textvariable=self.daily_target_var, width=4)
        self.daily_target_entry.grid(row=row, column=16)

        # Reverse Trading checkbox
        self.reverse_var = tk.BooleanVar(value=False)
        self.reverse_checkbox = tk.Checkbutton(master, variable=self.reverse_var)
        self.reverse_checkbox.grid(row=row, column=19)

        # Tambahkan label status window trading (5 posisi/5 menit)
        # Tampilkan default yang sesuai HFT (limit 50)
        self.window_status_label = tk.Label(master, text="0/50 | 00:00", bg="white", width=14)
        self.window_status_label.grid(row=row, column=20)

        # Input Window Open Limit
        self.window_open_limit_entry = tk.Entry(master, textvariable=self.window_open_limit_var, width=3)
        self.window_open_limit_entry.grid(row=row, column=21)

        # Timer thread and event for auto stop
        self.timer_thread = None
        self.timer_stop_event = threading.Event()
        self.timer_running = False

        # Thread untuk update status window trading
        self.window_status_stop_event = threading.Event()
        self.window_status_thread = threading.Thread(target=self.update_window_status_gui, daemon=True)
        self.window_status_thread.start()

    def browse_path(self):
        path = filedialog.askopenfilename()
        if path:
            self.path_var.set(path)

    def browse_ppo_model(self):
        """Buka file dialog untuk memilih PPO model."""
        path = filedialog.askopenfilename(
            title="Pilih PPO Model File",
            filetypes=[("Model Files", "*.zip"), ("All Files", "*.*")]
        )
        if path:
            self.ppo_model_path_var.set(path)

    def browse_model_path(self):
        path = filedialog.askopenfilename()
        if path:
            self.model_path_var.set(path)

    def start_bot(self):
        if not self.path_var.get():
            self.status_var.set("No Path")
            self.status_label.config(bg="yellow")
            return

        if not self.close_profit_var.get():
            self.status_var.set("No Close Profit")
            self.status_label.config(bg="yellow")
            return

        if not self.max_open_trades_var.get():
            self.status_var.set("No Max Open Trades")
            self.status_label.config(bg="yellow")
            return

        # Update the mapping logic for type_filling
        type_filling_mapping = {
            "FOK": 1,
            "IOC": 2,
            "RET": 3
        }
        type_filling = type_filling_mapping.get(self.type_filling_var.get(), 1)  # Default to 1 if invalid

        # Inisialisasi MetaTrader 5 untuk mendapatkan informasi akun
        if not mt5.initialize(self.path_var.get()):
            self.status_var.set("MT5 Error")
            self.status_label.config(bg="yellow")
            return

        account_info = get_account_info()
        if account_info:
            self.account_number_var.set(account_info.login)
            self.account_name_var.set(account_info.name)
            # Set file status window per akun
            self._window_status_file = f"window_status_{account_info.login}.json"
        else:
            self.account_number_var.set("N/A")
            self.account_name_var.set("N/A")
            self._window_status_file = None

        mt5.shutdown()  # Tutup koneksi MT5 setelah mendapatkan informasi akun

        # Ambil nilai ON/PAUSE dari instance app (dijamin ada)
        window_on = self.app.window_on_seconds_var.get()
        window_pause = self.app.window_pause_seconds_var.get()

        # Kirim parameter ke Aventa_Hybrid_PPO_v9.py
        cmd = [
            "python",
            "Aventa_Hybrid_PPO_v9.py",
            "--mt5_path", self.path_var.get(),
            "--symbol", self.symbol_var.get(),
            "--lot_size", self.lot_var.get(),
            "--close_profit", self.close_profit_var.get(),
            "--max_open_trades", self.max_open_trades_var.get(),
            "--type_filling", str(type_filling),
            "--max_spread", self.max_spread_var.get(),
            "--ppo_model_path", self.ppo_model_path_var.get(),
            "--start_trading_hour", self.start_hour_var.get(),
            "--end_trading_hour", self.end_hour_var.get(),
            "--daily_target", self.daily_target_var.get(),
            "--max_dd", self.dd_var.get(),
            "--window_open_limit", self.window_open_limit_var.get(),
            "--window_on_seconds", window_on,
            "--window_pause_seconds", window_pause
        ]
        if self.reverse_var.get():
            cmd.append("--reverse")

        try:
            self.process = subprocess.Popen(cmd)
            self.status_var.set("Running")
            self.status_label.config(bg="green")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            # Mulai timer 2 jam (7200 detik)
            self.timer_stop_event.clear()
            self.timer_running = True
            self.timer_thread = threading.Thread(target=self._timer_auto_stop, daemon=True)
            self.timer_thread.start()

            # Tampilkan notifikasi
            notification.notify(
                title="Bot Dimulai",
                message=f"Bot untuk akun {self.account_number_var.get()} telah dimulai.",
                app_name="Launcher v9.0",
                timeout=5
            )
        except Exception as e:
            self.status_var.set("Halted")
            self.status_label.config(bg="yellow")
            print(f"[WARNING] Gagal menjalankan bot: {e}")

    def stop_bot(self):
        if self.process:
            try:
                # Hentikan proses dengan terminate()
                self.process.terminate()
                self.process.wait(timeout=5)  # Tunggu hingga proses benar-benar berhenti
            except Exception as e:
                print(f"[ERROR] Gagal menghentikan proses: {e}")
                # Jika terminate gagal, gunakan kill sebagai alternatif
                try:
                    os.kill(self.process.pid, signal.SIGTERM)
                except Exception as kill_error:
                    print(f"[ERROR] Gagal memaksa menghentikan proses: {kill_error}")
                finally:
                    self.status_var.set("Halted")
                    self.status_label.config(bg="yellow")  # Status warna kuning untuk warning
            finally:
                self.process = None

        # Perbarui status bot di GUI
        self.status_var.set("Stopped")
        self.status_label.config(bg="red")  # Status warna merah untuk berhenti
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

        # Stop timer jika ada
        self.timer_stop_event.set()
        self.timer_running = False

        # Tampilkan notifikasi
        notification.notify(
            title="Bot Dihentikan",
            message=f"Bot untuk akun {self.account_number_var.get()} telah dihentikan.",
            app_name="Launcher v9.0",
            timeout=5
        )

    def _timer_auto_stop(self):
        # Timer 48 jam (172800 detik)
        timeout = 48 * 60 * 60
        start_time = time.time()
        while not self.timer_stop_event.is_set():
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                print(f"[INFO] Bot {self.account_number_var.get()} otomatis dihentikan setelah 48 jam.")
                self.stop_bot()
                # Tampilkan notifikasi
                notification.notify(
                    title="Bot Auto-Stop",
                    message=f"Bot untuk akun {self.account_number_var.get()} dihentikan otomatis setelah 48 jam.",
                    app_name="Launcher v9.0",
                    timeout=5
                )
                break
            time.sleep(5)

    def update_window_status_gui(self):
        while not self.window_status_stop_event.is_set():
            try:
                # Pilih file status window per akun jika sudah diketahui
                window_status_file = self._window_status_file or WINDOW_STATUS_FILE
                if os.path.exists(window_status_file):
                    with open(window_status_file, "r") as f:
                        status = json.load(f)
                    count = status.get("window_open_count", 0)
                    # HFT default limit fallback
                    limit = status.get("window_limit", 50)
                    seconds = status.get("window_time_left", 0)
                    is_pause = status.get("is_pause", False)
                    mm, ss = divmod(max(0, seconds), 60)
                    mode = "PAUSE" if is_pause else "ON"
                    text = f"{count}/{limit} | {mm:02d}:{ss:02d} {mode}"
                    color = "#ffb347" if is_pause else "#b6ffb3"
                    self.window_status_label.config(text=text, bg=color)
                else:
                    try:
                        limit = int(self.window_open_limit_var.get())
                    except Exception:
                        # fallback to HFT default if invalid
                        limit = 50
                    try:
                        on_sec = int(self.app.window_on_seconds_var.get())
                    except Exception:
                        on_sec = 60
                    mm, ss = divmod(on_sec, 60)
                    text = f"0/{limit} | {mm:02d}:{ss:02d} ON"
                    self.window_status_label.config(text=text, bg="#b6ffb3")
            except Exception:
                try:
                    self.window_status_label.config(text="ERR", bg="red")
                except Exception:
                    break  # Widget sudah di-destroy, keluar dari loop
            # HFT: refresh sering agar UI responsif
            time.sleep(0.2)

    def get_config(self):
        return {
            "symbol": self.symbol_var.get(),
            "lot": self.lot_var.get(),
            "max_dd": self.dd_var.get(),  # Pastikan max_dd tersimpan
            "path": self.path_var.get(),
            "type_filling": self.type_filling_var.get(),
            "max_spread": self.max_spread_var.get(),
            "max_open_trades": self.max_open_trades_var.get(),
            "close_profit": self.close_profit_var.get(),
            "ppo_model_path": self.ppo_model_path_var.get(),
            "start_trading_hour": self.start_hour_var.get(),
            "end_trading_hour": self.end_hour_var.get(),
            "daily_target": self.daily_target_var.get(),
            "reverse": self.reverse_var.get(),
            "window_open_limit": self.window_open_limit_var.get(),
        }

    def set_config(self, config):
        self.symbol_var.set(config.get("symbol", ""))
        self.lot_var.set(config.get("lot", ""))
        self.dd_var.set(config.get("max_dd", ""))  # Pastikan max_dd termuat
        self.path_var.set(config.get("path", ""))
        self.type_filling_var.set(config.get("type_filling", "ORDER_FILLING_IOC"))
        self.max_spread_var.set(config.get("max_spread", ""))
        self.max_open_trades_var.set(config.get("max_open_trades", ""))
        self.close_profit_var.set(config.get("close_profit", ""))  # Tambahkan Close Profit
        self.ppo_model_path_var.set(config.get("ppo_model_path", ""))  # Tambahkan PPO Model Path
        self.start_hour_var.set(config.get("start_trading_hour", "9"))
        self.end_hour_var.set(config.get("end_trading_hour", "17"))
        self.daily_target_var.set(config.get("daily_target", "10.0"))  # Tambahkan Daily Target
        self.reverse_var.set(config.get("reverse", False))  # Tambahkan reverse trading
        self.window_open_limit_var.set(config.get("window_open_limit", "5"))  # Tambahkan window open limit


class BotLauncherApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Aventa HFT Hybrid_v9.0")
        self.master.attributes("-topmost", True)
        self.bot_rows = []

        # === Tambahkan variabel global window ON dan PAUSE ===
        # HFT defaults: ON singkat, PAUSE singkat
        self.window_on_seconds_var = tk.StringVar(value="60")    # Default 60 detik (1 menit)
        self.window_pause_seconds_var = tk.StringVar(value="10") # Default 10 detik

        # Agar window bisa di-resize
        self.master.resizable(True, True)

        # Header
        headers = [
            "Symbol", "Lot", "Max DD", "Terminal Path", "Browse", "Filling", "Mx Spread", "Mx OP", "Close $",
            "PPO Path", "PPO", "Acc Number", "Acc Name", "Status", "SH", "EH",
            "Dy target", "Start", "Stop", "Rv", "WinStat", "OpenLimit"  # Header untuk kolom window open limit
        ]
        for idx, title in enumerate(headers):
            label = tk.Label(master, text=title, font=("Segoe UI", 8, "bold"))
            label.grid(row=0, column=idx)
            self.master.grid_columnconfigure(idx, weight=1, minsize=40)  # Kolom bisa melebar

        # Button frame
        self.add_row()
        self.button_frame = tk.Frame(master)
        self.button_frame.grid(row=100, column=0, columnspan=16, pady=10)

        self.add_button = tk.Button(self.button_frame, text="Tambah Bot", command=self.add_row)
        self.add_button.grid(row=0, column=0, padx=5)

        self.remove_button = tk.Button(self.button_frame, text="Kurangi Bot", command=self.remove_row)
        self.remove_button.grid(row=0, column=1, padx=5)

        self.save_button = tk.Button(self.button_frame, text="Simpan Konfigurasi", command=self.save_config)
        self.save_button.grid(row=0, column=2, padx=5)

        self.load_button = tk.Button(self.button_frame, text="Muat Konfigurasi", command=self.load_config)
        self.load_button.grid(row=0, column=3, padx=5)

        self.start_all_button = tk.Button(self.button_frame, text="Start Semua", command=self.start_all)
        self.start_all_button.grid(row=0, column=4, padx=5)

        self.stop_all_button = tk.Button(self.button_frame, text="Stop Semua", command=self.stop_all)
        self.stop_all_button.grid(row=0, column=5, padx=5)

        # Hapus tombol Import Data, Pre-Processing Data, dan Train Model
        # self.import_data_button = tk.Button(self.button_frame, text="Import Data", command=self.import_data)
        # self.import_data_button.grid(row=0, column=8, padx=5)

        # self.preprocess_data_button = tk.Button(self.button_frame, text="Pre-Processing Data", command=self.preprocess_data)
        # self.preprocess_data_button.grid(row=0, column=9, padx=5)

        # self.train_model_button = tk.Button(self.button_frame, text="Train Model", command=self.train_model)
        # self.train_model_button.grid(row=0, column=14, padx=5)

        # === Tambahkan input WINDOW_ON_SECONDS dan WINDOW_PAUSE_SECONDS di kanan tombol Train Model ===
        tk.Label(self.button_frame, text="ON (detik):").grid(row=0, column=10, padx=(15,2))
        self.window_on_entry = tk.Entry(self.button_frame, textvariable=self.window_on_seconds_var, width=7)
        self.window_on_entry.grid(row=0, column=11)

        tk.Label(self.button_frame, text="PAUSE (detik):").grid(row=0, column=12, padx=(8,2))
        self.window_pause_entry = tk.Entry(self.button_frame, textvariable=self.window_pause_seconds_var, width=7)
        self.window_pause_entry.grid(row=0, column=13)

        # Tambahkan scroll horizontal jika header sangat banyak
        self.canvas = tk.Canvas(master)
        self.scroll_x = tk.Scrollbar(master, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.scroll_x.set)
        self.canvas.grid(row=101, column=0, columnspan=len(headers), sticky="ew")
        self.scroll_x.grid(row=102, column=0, columnspan=len(headers), sticky="ew")
        self.master.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def add_row(self):
        row_index = len(self.bot_rows) + 1
        bot_row = BotRow(self.master, row_index, app=self)
        self.bot_rows.append(bot_row)

    def remove_row(self):
        if self.bot_rows:
            bot_row = self.bot_rows[-1]  # Ambil bot terakhir
            if bot_row.status_var.get() == "Running":
                print("[WARNING] Tidak dapat menghapus bot yang sedang aktif.")
                return  # Jangan hapus jika bot sedang aktif

            # Stop window status thread
            if hasattr(bot_row, "window_status_stop_event"):
                bot_row.window_status_stop_event.set()
            # Hapus bot jika tidak aktif
            self.bot_rows.pop()
            for widget in bot_row.__dict__.values():
                if isinstance(widget, tk.Widget):
                    widget.destroy()

    def save_config(self):
        config = [bot.get_config() for bot in self.bot_rows]
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        print("[INFO] Konfigurasi disimpan.")

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            for idx, bot_config in enumerate(config):
                if idx >= len(self.bot_rows):
                    self.add_row()
                self.bot_rows[idx].set_config(bot_config)
            print("[INFO] Konfigurasi dimuat.")
        except FileNotFoundError:
            print("[WARNING] File konfigurasi tidak ditemukan.")

    def start_all(self):
        for idx, bot in enumerate(self.bot_rows):
            bot.start_bot()
            # HFT: jeda singkat antar start untuk lebih cepat
            if idx < len(self.bot_rows) - 1:
                time.sleep(0.5)

    def stop_all(self):
        """Hentikan semua bot dengan jeda 3 detik antara setiap bot."""
        for idx, bot in enumerate(self.bot_rows):
            bot.stop_bot()
            # HFT: jeda singkat antar stop
            if idx < len(self.bot_rows) - 1:
                time.sleep(0.5)

    def on_close(self):
        """Event handler untuk menangani penutupan aplikasi."""
        print("[INFO] Menutup aplikasi, menghentikan semua bot...")
        self.stop_all()  # Hentikan semua bot
        self.master.destroy()  # Tutup aplikasi


if __name__ == "__main__":
    root = tk.Tk()
    app = BotLauncherApp(root)
    app.load_config()  # Muat konfigurasi saat aplikasi dibuka

    def update_window_height():
        # Hitung tinggi window berdasarkan jumlah baris bot + header + button frame
        row_height = 28  # Perkiraan tinggi satu baris (px)
        min_height = 120
        max_height = 800
        n_rows = len(app.bot_rows)
        total_height = (n_rows + 3) * row_height  # +3 untuk header dan tombol
        total_height = max(min_height, min(total_height, max_height))
        root.geometry(f"1800x{total_height}")

    # Update ukuran window setiap kali baris ditambah/kurang
    orig_add_row = app.add_row
    orig_remove_row = app.remove_row
    def add_row_and_resize():
        orig_add_row()
        update_window_height()
    def remove_row_and_resize():
        orig_remove_row()
        update_window_height()
    app.add_row = add_row_and_resize
    app.remove_row = remove_row_and_resize

    update_window_height()  # Set ukuran awal
    root.mainloop()

# Bersihkan duplikat dan sediakan satu fungsi browse_file bersih
def browse_file():
    root = Tk()
    root.withdraw()  # Sembunyikan jendela utama
    file_path = filedialog.askopenfilename(title="Select PPO Model File", filetypes=[("Model Files", "*.zip"), ("All Files", "*.*")])
    root.destroy()
    return file_path
