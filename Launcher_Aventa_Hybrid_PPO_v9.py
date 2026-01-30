import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import MetaTrader5 as mt5  # type: ignore
import json
import os
import signal
import time
import threading
import csv
import logging
from typing import Optional, Dict, List, Any
from tkinter import ttk
from plyer import notification 
import argparse
from tkinter import Tk
from dataclasses import dataclass
from enum import Enum

CONFIG_FILE = "bot_config.json"  # Nama file konfigurasi
WINDOW_STATUS_FILE = "window_status.json"  # File status window trading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("launcher_logs.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotStatus(Enum):
    """Bot status enum untuk type safety"""
    STOPPED = "Stopped"
    RUNNING = "Running"
    ERROR = "Error"
    HALTED = "Halted"

@dataclass
class BotValidation:
    """Validasi error untuk bot configuration"""
    is_valid: bool
    errors: List[str]
    
    def add_error(self, error: str) -> None:
        """Add validation error"""
        self.errors.append(error)
        self.is_valid = False

def get_suggested_target_profit(log_file="log_transaksi.csv", symbol="") -> Optional[float]:
    """
    Mengambil informasi target profit dari log transaksi.
    
    Args:
        log_file: Path ke file log transaksi
        symbol: Simbol trading yang dicari
        
    Returns:
        Target profit value atau None jika tidak ditemukan
    """
    try:
        if not os.path.exists(log_file):
            return None
            
        with open(log_file, mode='r') as file:
            reader = csv.reader(file)
            next(reader, None)  # Lewati header
            for row in reversed(list(reader)):  # Baca dari baris terakhir
                if len(row) > 3 and row[1] == symbol and "Target Profit" in row[2]:
                    return float(row[3].strip())
        return None  # Tidak ada data target profit untuk simbol
    except Exception as e:
        logger.error(f"Failed to read suggested target profit: {e}")
        return None

def get_account_info() -> Optional[Any]:
    """
    Mengambil informasi akun dari MetaTrader 5.
    
    Returns:
        Account info object atau None jika error
    """
    try:
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info from MT5")
            return None
        return account_info
    except Exception as e:
        logger.error(f"Exception while getting account info: {e}")
        return None

def validate_bot_parameters(params: Dict[str, Any]) -> BotValidation:
    """
    Validasi semua parameter bot sebelum start.
    
    Args:
        params: Dictionary berisi parameter bot
        
    Returns:
        BotValidation object dengan status dan error list
    """
    validation = BotValidation(is_valid=True, errors=[])
    
    # Validate required fields
    if not params.get('path'):
        validation.add_error("MT5 Terminal path wajib diisi")
    elif not os.path.exists(params['path']):
        validation.add_error(f"Terminal path tidak ditemukan: {params['path']}")
        
    if not params.get('symbol'):
        validation.add_error("Symbol wajib diisi")
        
    if not params.get('lot_size'):
        validation.add_error("Lot size wajib diisi")
    else:
        try:
            lot = float(params['lot_size'])
            if lot <= 0 or lot > 10:
                validation.add_error("Lot size harus antara 0.01 dan 10")
        except ValueError:
            validation.add_error("Lot size harus berupa angka")
            
    if not params.get('close_profit'):
        validation.add_error("Close profit wajib diisi")
    else:
        try:
            float(params['close_profit'])
        except ValueError:
            validation.add_error("Close profit harus berupa angka")
            
    if not params.get('max_open_trades'):
        validation.add_error("Max open trades wajib diisi")
    else:
        try:
            trades = int(params['max_open_trades'])
            if trades <= 0 or trades > 100:
                validation.add_error("Max open trades harus antara 1 dan 100")
        except ValueError:
            validation.add_error("Max open trades harus berupa angka")
    
    # Validate max_dd
    if params.get('max_dd'):
        try:
            float(params['max_dd'])
        except ValueError:
            validation.add_error("Max DD harus berupa angka")
            
    # Validate spread
    if params.get('max_spread'):
        try:
            float(params['max_spread'])
        except ValueError:
            validation.add_error("Max spread harus berupa angka")
    
    return validation

class BotRow:
    """Represents a single bot row in the launcher GUI with improved validation and error handling"""
    
    def __init__(self, master: tk.Widget, row: int, app: 'BotLauncherApp') -> None:
        """
        Initialize a bot row with all necessary fields and controls.
        
        Args:
            master: Parent widget (usually the main frame)
            row: Row number for grid placement
            app: Reference to the main BotLauncherApp instance
        """
        self.app = app
        self.master = master
        self.row = row
        self.process: Optional[subprocess.Popen] = None
        self._window_status_file: Optional[str] = None
        self.timer_thread: Optional[threading.Thread] = None
        self.timer_stop_event = threading.Event()
        self.window_status_stop_event = threading.Event()
        self.timer_running = False
        
        # String variables for form fields
        self.symbol_var = tk.StringVar()
        self.lot_var = tk.StringVar(value="0.01")
        self.dd_var = tk.StringVar(value="5.0")
        self.path_var = tk.StringVar()
        self.type_filling_var = tk.StringVar(value="FOK")
        self.max_spread_var = tk.StringVar(value="0.5")
        self.account_number_var = tk.StringVar(value="N/A")
        self.account_name_var = tk.StringVar(value="N/A")
        self.status_var = tk.StringVar(value="Stopped")
        self.max_open_trades_var = tk.StringVar(value="5")
        self.close_profit_var = tk.StringVar(value="0.5")
        self.ppo_model_path_var = tk.StringVar(value="")
        self.start_hour_var = tk.StringVar(value="9")
        self.end_hour_var = tk.StringVar(value="17")
        self.daily_target_var = tk.StringVar(value="10.0")
        self.reverse_var = tk.BooleanVar(value=False)
        self.window_open_limit_var = tk.StringVar(value="50")
        
        self._create_widgets(row)
        
        # Start window status update thread
        self.window_status_thread = threading.Thread(target=self.update_window_status_gui, daemon=True)
        self.window_status_thread.start()
    
    def _create_widgets(self, row: int) -> None:
        """Create and place all widgets for this bot row"""
        
        # Symbol input with validation
        self.symbol_entry = tk.Entry(self.master, textvariable=self.symbol_var, width=10)
        self.symbol_entry.grid(row=row, column=0, padx=2, pady=2)
        
        # Lot input with validation
        self.lot_entry = tk.Entry(self.master, textvariable=self.lot_var, width=5)
        self.lot_entry.grid(row=row, column=1, padx=2, pady=2)
        
        # Max DD input
        self.dd_entry = tk.Entry(self.master, textvariable=self.dd_var, width=3)
        self.dd_entry.grid(row=row, column=2, padx=2, pady=2)
        
        # Terminal path input
        self.path_entry = tk.Entry(self.master, textvariable=self.path_var, width=18)
        self.path_entry.grid(row=row, column=3, padx=2, pady=2)
        
        # Browse button for terminal path
        self.browse_button = tk.Button(
            self.master, text="Browse", 
            command=self.browse_path, 
            bg="#4CAF50", fg="white", relief=tk.FLAT
        )
        self.browse_button.grid(row=row, column=4, padx=2, pady=2)
        
        # Type Filling dropdown
        self.type_filling_dropdown = ttk.Combobox(
            self.master, textvariable=self.type_filling_var, 
            width=4, state="readonly"
        )
        self.type_filling_dropdown['values'] = ["FOK", "IOC", "RET"]
        self.type_filling_dropdown.grid(row=row, column=5, padx=2, pady=2)
        
        # Max Spread input
        self.max_spread_entry = tk.Entry(self.master, textvariable=self.max_spread_var, width=7)
        self.max_spread_entry.grid(row=row, column=6, padx=2, pady=2)
        
        # Max Open Trades input
        self.max_open_trades_entry = tk.Entry(self.master, textvariable=self.max_open_trades_var, width=3)
        self.max_open_trades_entry.grid(row=row, column=7, padx=2, pady=2)
        
        # Close Profit input
        self.close_profit_entry = tk.Entry(self.master, textvariable=self.close_profit_var, width=3)
        self.close_profit_entry.grid(row=row, column=8, padx=2, pady=2)
        
        # PPO Model Path input
        self.ppo_model_entry = tk.Entry(self.master, textvariable=self.ppo_model_path_var, width=15)
        self.ppo_model_entry.grid(row=row, column=9, padx=2, pady=2)
        
        # Browse button for PPO model
        self.browse_ppo_button = tk.Button(
            self.master, text="PPO", 
            command=self.browse_ppo_model, 
            bg="#2196F3", fg="white", relief=tk.FLAT
        )
        self.browse_ppo_button.grid(row=row, column=10, padx=2, pady=2)
        
        # Account Number label
        self.account_number_label = tk.Label(
            self.master, textvariable=self.account_number_var, 
            width=8, bg="#f0f0f0", relief=tk.SUNKEN
        )
        self.account_number_label.grid(row=row, column=11, padx=2, pady=2)
        
        # Account Name label
        self.account_name_label = tk.Label(
            self.master, textvariable=self.account_name_var, 
            width=20, bg="#f0f0f0", relief=tk.SUNKEN
        )
        self.account_name_label.grid(row=row, column=12, padx=2, pady=2)
        
        # Status label with color coding
        self.status_label = tk.Label(
            self.master, textvariable=self.status_var, 
            width=7, bg="red", fg="white", relief=tk.RAISED, font=("Arial", 9, "bold")
        )
        self.status_label.grid(row=row, column=13, padx=2, pady=2)
        
        # Start and Stop buttons
        self.start_button = tk.Button(
            self.master, text="Start", 
            command=self.start_bot, 
            bg="#4CAF50", fg="white", relief=tk.FLAT, width=6
        )
        self.start_button.grid(row=row, column=17, padx=2, pady=2)
        
        self.stop_button = tk.Button(
            self.master, text="Stop", 
            command=self.stop_bot, 
            state=tk.DISABLED, 
            bg="#f44336", fg="white", relief=tk.FLAT, width=6
        )
        self.stop_button.grid(row=row, column=18, padx=2, pady=2)
        
        # Start Trading Hour input
        self.start_hour_entry = tk.Entry(self.master, textvariable=self.start_hour_var, width=2)
        self.start_hour_entry.grid(row=row, column=14, padx=2, pady=2)
        
        # End Trading Hour input
        self.end_hour_entry = tk.Entry(self.master, textvariable=self.end_hour_var, width=2)
        self.end_hour_entry.grid(row=row, column=15, padx=2, pady=2)
        
        # Daily Target input
        self.daily_target_entry = tk.Entry(self.master, textvariable=self.daily_target_var, width=4)
        self.daily_target_entry.grid(row=row, column=16, padx=2, pady=2)
        
        # Reverse Trading checkbox
        self.reverse_checkbox = tk.Checkbutton(
            self.master, variable=self.reverse_var
        )
        self.reverse_checkbox.grid(row=row, column=19, padx=2, pady=2)
        
        # Window Status label with color indicator
        self.window_status_label = tk.Label(
            self.master, text="0/50 | 00:00", 
            bg="white", width=14, relief=tk.SUNKEN, font=("Arial", 8, "bold")
        )
        self.window_status_label.grid(row=row, column=20, padx=2, pady=2)
        
        # Window Open Limit input
        self.window_open_limit_entry = tk.Entry(
            self.master, textvariable=self.window_open_limit_var, 
            width=3
        )
        self.window_open_limit_entry.grid(row=row, column=21, padx=2, pady=2)
    
    def browse_path(self) -> None:
        """Open file dialog untuk memilih MetaTrader 5 terminal"""
        try:
            path = filedialog.askopenfilename(
                title="Pilih MetaTrader 5 Terminal (terminal64.exe)",
                filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
            )
            if path:
                self.path_var.set(path)
                logger.info(f"Terminal path selected: {path}")
        except Exception as e:
            logger.error(f"Error in browse_path: {e}")
            messagebox.showerror("Error", f"Error browsing path: {e}")
    
    def browse_ppo_model(self) -> None:
        """Open file dialog untuk memilih PPO model"""
        try:
            path = filedialog.askopenfilename(
                title="Pilih PPO Model File",
                filetypes=[("Model Files", "*.zip"), ("All Files", "*.*")]
            )
            if path:
                self.ppo_model_path_var.set(path)
                logger.info(f"PPO model selected: {path}")
        except Exception as e:
            logger.error(f"Error in browse_ppo_model: {e}")
            messagebox.showerror("Error", f"Error browsing PPO model: {e}")

    def start_bot(self) -> None:
        """Start the trading bot with comprehensive validation and error handling"""
        try:
            # Prepare parameters for validation
            params = {
                'path': self.path_var.get(),
                'symbol': self.symbol_var.get(),
                'lot_size': self.lot_var.get(),
                'close_profit': self.close_profit_var.get(),
                'max_open_trades': self.max_open_trades_var.get(),
                'max_dd': self.dd_var.get(),
                'max_spread': self.max_spread_var.get(),
            }
            
            # Validate all parameters before starting
            validation = validate_bot_parameters(params)
            if not validation.is_valid:
                error_msg = "Validation Errors:\n" + "\n".join(validation.errors)
                messagebox.showerror("Validation Error", error_msg)
                self.status_var.set("Invalid")
                self.status_label.config(bg="orange")
                logger.warning(f"Bot validation failed: {error_msg}")
                return
            
            # Type filling mapping
            type_filling_mapping = {"FOK": 1, "IOC": 2, "RET": 3}
            type_filling = type_filling_mapping.get(self.type_filling_var.get(), 1)
            
            # Initialize MetaTrader 5
            logger.info(f"Initializing MT5 at {self.path_var.get()}")
            if not mt5.initialize(self.path_var.get()):
                error = "Failed to initialize MetaTrader 5. Check if terminal.exe path is correct."
                messagebox.showerror("MT5 Error", error)
                self.status_var.set("MT5 Error")
                self.status_label.config(bg="orange")
                logger.error(error)
                return
            
            # Get account information
            account_info = get_account_info()
            if account_info:
                self.account_number_var.set(str(account_info.login))
                self.account_name_var.set(str(account_info.name))
                self._window_status_file = f"window_status_{account_info.login}.json"
                logger.info(f"Connected to account: {account_info.login} ({account_info.name})")
            else:
                self.account_number_var.set("N/A")
                self.account_name_var.set("N/A")
                self._window_status_file = None
                logger.warning("Could not get account information from MT5")
            
            mt5.shutdown()
            
            # Get window timing parameters
            try:
                window_on = self.app.window_on_seconds_var.get()
                window_pause = self.app.window_pause_seconds_var.get()
            except Exception as e:
                logger.warning(f"Error getting window timing: {e}, using defaults")
                window_on = "60"
                window_pause = "10"
            
            # Build command
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
                "--ppo_model_path", self.ppo_model_path_var.get() or "none",
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
            
            # Start bot process
            logger.info(f"Starting bot with command: {' '.join(cmd)}")
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.status_var.set("Running")
            self.status_label.config(bg="green")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Start auto-stop timer (48 hours)
            self.timer_stop_event.clear()
            self.timer_running = True
            self.timer_thread = threading.Thread(target=self._timer_auto_stop, daemon=True)
            self.timer_thread.start()
            
            # Send notification
            try:
                notification.notify(
                    title="Bot Started",
                    message=f"Bot for account {self.account_number_var.get()} is now running.",
                    app_name="Aventa Launcher v9.0",
                    timeout=5
                )
            except Exception as notify_err:
                logger.warning(f"Could not send notification: {notify_err}")
            
            logger.info(f"Bot started successfully for account {self.account_number_var.get()}")
            
        except Exception as e:
            error_msg = f"Error starting bot: {str(e)}"
            messagebox.showerror("Start Error", error_msg)
            self.status_var.set("Error")
            self.status_label.config(bg="orange")
            logger.error(error_msg, exc_info=True)

    def stop_bot(self) -> None:
        """Stop the trading bot gracefully with proper cleanup"""
        try:
            if self.process:
                try:
                    logger.info(f"Terminating process {self.process.pid}")
                    self.process.terminate()
                    # Wait for process to terminate gracefully
                    self.process.wait(timeout=5)
                    logger.info("Bot process terminated successfully")
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate, forcing kill...")
                    self.process.kill()
                    self.process.wait()
                except Exception as e:
                    logger.error(f"Error terminating process: {e}")
                finally:
                    self.process = None
            
            self.status_var.set("Stopped")
            self.status_label.config(bg="red")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # Stop timer if running
            self.timer_stop_event.set()
            self.timer_running = False
            
            # Send notification
            try:
                notification.notify(
                    title="Bot Stopped",
                    message=f"Bot for account {self.account_number_var.get()} has been stopped.",
                    app_name="Aventa Launcher v9.0",
                    timeout=5
                )
            except Exception as notify_err:
                logger.warning(f"Could not send notification: {notify_err}")
            
            logger.info(f"Bot stopped for account {self.account_number_var.get()}")
            
        except Exception as e:
            logger.error(f"Error in stop_bot: {e}", exc_info=True)
            messagebox.showerror("Stop Error", f"Error stopping bot: {str(e)}")
    
    def _timer_auto_stop(self) -> None:
        """Auto-stop bot after 48 hours of running"""
        TIMEOUT_SECONDS = 48 * 60 * 60  # 48 hours
        start_time = time.time()
        
        while not self.timer_stop_event.is_set():
            elapsed = time.time() - start_time
            if elapsed >= TIMEOUT_SECONDS:
                logger.info(f"Auto-stopping bot {self.account_number_var.get()} after 48 hours")
                self.stop_bot()
                try:
                    notification.notify(
                        title="Bot Auto-Stopped",
                        message=f"Bot for account {self.account_number_var.get()} stopped after 48 hours.",
                        app_name="Aventa Launcher v9.0",
                        timeout=5
                    )
                except Exception as e:
                    logger.warning(f"Could not send auto-stop notification: {e}")
                break
            time.sleep(5)
    
    def update_window_status_gui(self) -> None:
        """Update window status display from JSON file"""
        while not self.window_status_stop_event.is_set():
            try:
                window_status_file = self._window_status_file or WINDOW_STATUS_FILE
                
                if os.path.exists(window_status_file):
                    try:
                        with open(window_status_file, "r") as f:
                            status = json.load(f)
                        
                        count = status.get("window_open_count", 0)
                        limit = status.get("window_limit", 50)
                        seconds = status.get("window_time_left", 0)
                        is_pause = status.get("is_pause", False)
                        
                        mm, ss = divmod(max(0, seconds), 60)
                        mode = "PAUSE" if is_pause else "ON"
                        text = f"{count}/{limit} | {mm:02d}:{ss:02d} {mode}"
                        color = "#ffb347" if is_pause else "#b6ffb3"
                        
                        self.window_status_label.config(text=text, bg=color)
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON in window status file")
                        self.window_status_label.config(text="ERR", bg="red")
                else:
                    # File doesn't exist yet, show default
                    try:
                        limit = int(self.window_open_limit_var.get())
                    except ValueError:
                        limit = 50
                    
                    try:
                        on_sec = int(self.app.window_on_seconds_var.get())
                    except (ValueError, AttributeError):
                        on_sec = 60
                    
                    mm, ss = divmod(on_sec, 60)
                    text = f"0/{limit} | {mm:02d}:{ss:02d} ON"
                    self.window_status_label.config(text=text, bg="#b6ffb3")
                    
            except Exception as e:
                try:
                    self.window_status_label.config(text="ERR", bg="red")
                except:
                    # Widget might have been destroyed
                    break
                if not isinstance(e, tk.TclError):
                    logger.debug(f"Error updating window status: {e}")
            
            # Update every 200ms for responsiveness
            time.sleep(0.2)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration as dictionary"""
        return {
            "symbol": self.symbol_var.get(),
            "lot": self.lot_var.get(),
            "max_dd": self.dd_var.get(),
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
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Load configuration from dictionary"""
        self.symbol_var.set(config.get("symbol", ""))
        self.lot_var.set(config.get("lot", "0.01"))
        self.dd_var.set(config.get("max_dd", "5.0"))
        self.path_var.set(config.get("path", ""))
        self.type_filling_var.set(config.get("type_filling", "FOK"))
        self.max_spread_var.set(config.get("max_spread", "0.5"))
        self.max_open_trades_var.set(config.get("max_open_trades", "5"))
        self.close_profit_var.set(config.get("close_profit", "0.5"))
        self.ppo_model_path_var.set(config.get("ppo_model_path", ""))
        self.start_hour_var.set(config.get("start_trading_hour", "9"))
        self.end_hour_var.set(config.get("end_trading_hour", "17"))
        self.daily_target_var.set(config.get("daily_target", "10.0"))
        self.reverse_var.set(config.get("reverse", False))
        self.window_open_limit_var.set(config.get("window_open_limit", "50"))


class BotLauncherApp:
    """Main application class for managing multiple trading bot instances"""
    
    def __init__(self, master: tk.Tk) -> None:
        """
        Initialize the bot launcher application.
        
        Args:
            master: Root Tkinter window
        """
        self.master = master
        self.master.title("Aventa HFT Hybrid PPO v9.0")
        self.master.attributes("-topmost", True)
        self.master.resizable(True, True)
        
        self.bot_rows: List[BotRow] = []
        
        # Window timing controls
        self.window_on_seconds_var = tk.StringVar(value="60")
        self.window_pause_seconds_var = tk.StringVar(value="10")
        
        # Create header row
        self._create_header()
        
        # Add initial bot row
        self.add_row()
        
        # Create button frame
        self._create_button_frame()
        
        # Set initial window size
        self._update_window_height()
        
        logger.info("Bot Launcher initialized successfully")
    
    def _create_header(self) -> None:
        """Create header row with column labels"""
        headers = [
            "Symbol", "Lot", "Max DD", "Terminal Path", "Browse", "Filling", "Max Spread", "Max OP", "Close $",
            "PPO Path", "PPO", "Acc Number", "Acc Name", "Status", "SH", "EH",
            "Daily Target", "Start", "Stop", "Reverse", "WinStat", "Open Limit"
        ]
        
        for idx, title in enumerate(headers):
            label = tk.Label(
                self.master, text=title, font=("Segoe UI", 9, "bold"),
                bg="#e0e0e0", relief=tk.RAISED, padx=2, pady=2
            )
            label.grid(row=0, column=idx, sticky="nsew", padx=1, pady=1)
            self.master.grid_columnconfigure(idx, weight=1, minsize=50)
    
    def _create_button_frame(self) -> None:
        """Create control button frame"""
        self.button_frame = tk.Frame(self.master, bg="#f5f5f5", relief=tk.SUNKEN, padx=10, pady=10)
        self.button_frame.grid(row=100, column=0, columnspan=22, sticky="ew", padx=2, pady=2)
        
        # Button style
        button_style = {"font": ("Arial", 9), "relief": tk.RAISED, "width": 12}
        
        # Add/Remove buttons
        self.add_button = tk.Button(
            self.button_frame, text="➕ Add Bot", command=self.add_row,
            bg="#4CAF50", fg="white", **button_style
        )
        self.add_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.remove_button = tk.Button(
            self.button_frame, text="➖ Remove Bot", command=self.remove_row,
            bg="#f44336", fg="white", **button_style
        )
        self.remove_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Config buttons
        self.save_button = tk.Button(
            self.button_frame, text="💾 Save Config", command=self.save_config,
            bg="#2196F3", fg="white", **button_style
        )
        self.save_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.load_button = tk.Button(
            self.button_frame, text="📂 Load Config", command=self.load_config,
            bg="#2196F3", fg="white", **button_style
        )
        self.load_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Control buttons
        self.start_all_button = tk.Button(
            self.button_frame, text="▶️  Start All", command=self.start_all,
            bg="#8BC34A", fg="white", **button_style
        )
        self.start_all_button.grid(row=0, column=4, padx=5, pady=5)
        
        self.stop_all_button = tk.Button(
            self.button_frame, text="⏹️  Stop All", command=self.stop_all,
            bg="#FF6F00", fg="white", **button_style
        )
        self.stop_all_button.grid(row=0, column=5, padx=5, pady=5)
        
        # Window timing controls
        tk.Label(self.button_frame, text="⏱️ ON (s):", bg="#f5f5f5", font=("Arial", 9)).grid(
            row=0, column=10, padx=(20, 2), pady=5
        )
        self.window_on_entry = tk.Entry(
            self.button_frame, textvariable=self.window_on_seconds_var, width=5
        )
        self.window_on_entry.grid(row=0, column=11, padx=2, pady=5)
        
        tk.Label(self.button_frame, text="⏸️ PAUSE (s):", bg="#f5f5f5", font=("Arial", 9)).grid(
            row=0, column=12, padx=(10, 2), pady=5
        )
        self.window_pause_entry = tk.Entry(
            self.button_frame, textvariable=self.window_pause_seconds_var, width=5
        )
        self.window_pause_entry.grid(row=0, column=13, padx=2, pady=5)
    
    def add_row(self) -> None:
        """Add a new bot row"""
        try:
            row_index = len(self.bot_rows) + 1
            bot_row = BotRow(self.master, row_index, app=self)
            self.bot_rows.append(bot_row)
            self._update_window_height()
            logger.info(f"Added new bot row {row_index}")
        except Exception as e:
            logger.error(f"Error adding bot row: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error adding bot row: {str(e)}")
    
    def remove_row(self) -> None:
        """Remove the last bot row"""
        try:
            if not self.bot_rows:
                messagebox.showwarning("Warning", "No bots to remove")
                return
            
            bot_row = self.bot_rows[-1]
            
            # Prevent removal if bot is running
            if bot_row.status_var.get() == "Running":
                messagebox.showwarning("Warning", "Cannot remove a running bot. Stop it first.")
                return
            
            # Clean up threads
            bot_row.window_status_stop_event.set()
            if bot_row.timer_thread and bot_row.timer_thread.is_alive():
                bot_row.timer_stop_event.set()
            
            # Remove widgets
            for attr_name in dir(bot_row):
                attr = getattr(bot_row, attr_name)
                if isinstance(attr, tk.Widget):
                    try:
                        attr.destroy()
                    except tk.TclError:
                        pass  # Widget already destroyed
            
            self.bot_rows.pop()
            self._update_window_height()
            logger.info(f"Removed bot row, {len(self.bot_rows)} rows remaining")
            
        except Exception as e:
            logger.error(f"Error removing bot row: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error removing bot row: {str(e)}")
    
    def save_config(self) -> None:
        """Save all bot configurations to JSON file"""
        try:
            config = [bot.get_config() for bot in self.bot_rows]
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Success", f"Configuration saved to {CONFIG_FILE}")
            logger.info(f"Configuration saved: {len(config)} bots")
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
            messagebox.showerror("Save Error", f"Error saving configuration: {str(e)}")
    
    def load_config(self) -> None:
        """Load bot configurations from JSON file"""
        try:
            if not os.path.exists(CONFIG_FILE):
                messagebox.showwarning("Warning", f"Configuration file '{CONFIG_FILE}' not found")
                logger.warning(f"Configuration file not found: {CONFIG_FILE}")
                return
            
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            
            # Adjust number of rows to match config
            while len(self.bot_rows) < len(config):
                self.add_row()
            
            # Load configuration into each row
            for idx, bot_config in enumerate(config):
                self.bot_rows[idx].set_config(bot_config)
            
            messagebox.showinfo("Success", f"Configuration loaded: {len(config)} bots")
            logger.info(f"Configuration loaded: {len(config)} bots")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            messagebox.showerror("Load Error", f"Invalid JSON in configuration file: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            messagebox.showerror("Load Error", f"Error loading configuration: {str(e)}")
    
    def start_all(self) -> None:
        """Start all bot rows with a short delay between each"""
        try:
            if not self.bot_rows:
                messagebox.showwarning("Warning", "No bots configured")
                return
            
            logger.info(f"Starting all {len(self.bot_rows)} bots...")
            for idx, bot in enumerate(self.bot_rows):
                if bot.status_var.get() != "Running":
                    bot.start_bot()
                    # Short delay between starts for stability
                    if idx < len(self.bot_rows) - 1:
                        time.sleep(0.5)
            
            logger.info("Start all command completed")
        except Exception as e:
            logger.error(f"Error starting all bots: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error starting bots: {str(e)}")
    
    def stop_all(self) -> None:
        """Stop all bot rows with a short delay between each"""
        try:
            logger.info(f"Stopping all {len(self.bot_rows)} bots...")
            for idx, bot in enumerate(self.bot_rows):
                if bot.status_var.get() == "Running":
                    bot.stop_bot()
                    # Short delay between stops for stability
                    if idx < len(self.bot_rows) - 1:
                        time.sleep(0.5)
            
            logger.info("Stop all command completed")
        except Exception as e:
            logger.error(f"Error stopping all bots: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error stopping bots: {str(e)}")
    
    def _update_window_height(self) -> None:
        """Calculate and update window size based on number of rows"""
        ROW_HEIGHT = 30
        MIN_HEIGHT = 300
        MAX_HEIGHT = 1200
        
        n_rows = len(self.bot_rows)
        total_height = 50 + (n_rows * ROW_HEIGHT) + 100  # header + rows + button frame
        total_height = max(MIN_HEIGHT, min(total_height, MAX_HEIGHT))
        
        self.master.geometry(f"2200x{total_height}")
        logger.debug(f"Window height updated: {total_height}px for {n_rows} bots")
    
    def on_close(self) -> None:
        """Handle application closing - stop all bots gracefully"""
        try:
            logger.info("Application closing, stopping all bots...")
            self.stop_all()
            
            # Stop all window status threads
            for bot in self.bot_rows:
                bot.window_status_stop_event.set()
            
            # Wait a moment for cleanup
            time.sleep(1)
            
            self.master.destroy()
            logger.info("Application closed successfully")
        except Exception as e:
            logger.error(f"Error during application close: {e}", exc_info=True)
            self.master.destroy()


if __name__ == "__main__":
    logger.info("Aventa HFT Hybrid PPO v9.0 Launcher starting...")
    
    try:
        root = tk.Tk()
        app = BotLauncherApp(root)
        
        # Load saved configuration on startup
        app.load_config()
        
        # Handle window close event
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        
        logger.info("Launcher ready for trading")
        root.mainloop()
        
    except Exception as e:
        logger.critical(f"Fatal error in launcher: {e}", exc_info=True)
        raise


def browse_file() -> str:
    """Helper function to browse for files"""
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select PPO Model File",
        filetypes=[("Model Files", "*.zip"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path
