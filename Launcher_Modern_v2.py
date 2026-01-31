#!/usr/bin/env python3
"""
Aventa HFT Hybrid PPO v9.0 - Modern Launcher GUI
A professional, feature-rich trading bot launcher with modern UI design
Author: Aventa AI Team
Date: 31 January 2026
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import MetaTrader5 as mt5
import json
import os
import time
import threading
import logging
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# ==================== CONFIGURATION & LOGGING ====================

CONFIG_FILE = "bot_config.json"
WINDOW_STATUS_FILE = "window_status.json"
LOG_FILE = "launcher.log"

# Setup logging with file and console
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Color scheme for modern UI
COLOR_SCHEME = {
    'primary': '#2196F3',      # Blue
    'success': '#4CAF50',      # Green
    'danger': '#f44336',       # Red
    'warning': '#FF9800',      # Orange
    'info': '#00BCD4',         # Cyan
    'light': '#f5f5f5',        # Light gray
    'dark': '#212121',         # Dark gray
    'bg': '#fafafa',           # Background
    'fg': '#212121',           # Text
}

# ==================== DATA CLASSES ====================

class BotStatus(Enum):
    """Bot status enumeration"""
    STOPPED = "Stopped"
    RUNNING = "Running"
    ERROR = "Error"
    WARNING = "Warning"

@dataclass
class BotValidation:
    """Configuration validation result"""
    is_valid: bool
    errors: List[str]
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.is_valid = False

@dataclass
class BotConfig:
    """Complete bot configuration"""
    symbol: str
    lot_size: float
    max_dd: float
    mt5_path: str
    type_filling: str
    max_spread: float
    max_open_trades: int
    close_profit: float
    ppo_model_path: str
    start_hour: int
    end_hour: int
    daily_target: float
    reverse: bool
    window_open_limit: int

# ==================== UTILITY FUNCTIONS ====================

def validate_bot_parameters(config: Dict[str, Any]) -> BotValidation:
    """Validate bot configuration with detailed error messages"""
    validation = BotValidation(is_valid=True, errors=[])
    
    # Check required fields
    if not config.get('symbol'):
        validation.add_error("✗ Symbol wajib diisi")
    
    if not config.get('mt5_path'):
        validation.add_error("✗ Terminal path wajib diisi")
    elif not os.path.exists(config['mt5_path']):
        validation.add_error(f"✗ Terminal path tidak ditemukan: {config['mt5_path']}")
    
    # Validate numeric fields
    try:
        lot = float(config.get('lot_size', 0))
        if lot <= 0 or lot > 10:
            validation.add_error("✗ Lot size harus antara 0.01 dan 10")
    except (ValueError, TypeError):
        validation.add_error("✗ Lot size harus berupa angka")
    
    try:
        trades = int(config.get('max_open_trades', 0))
        if trades <= 0 or trades > 100:
            validation.add_error("✗ Max open trades harus antara 1 dan 100")
    except (ValueError, TypeError):
        validation.add_error("✗ Max open trades harus berupa angka")
    
    try:
        float(config.get('close_profit', 0))
    except (ValueError, TypeError):
        validation.add_error("✗ Close profit harus berupa angka")
    
    return validation

def get_mt5_account_info() -> Optional[Dict[str, Any]]:
    """Get account information from MetaTrader 5"""
    try:
        account = mt5.account_info()
        if account:
            return {
                'login': account.login,
                'name': account.name,
                'balance': account.balance,
                'equity': account.equity,
                'margin': account.margin,
                'margin_free': account.margin_free,
                'margin_level': account.margin_level if account.margin > 0 else 0
            }
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
    return None

# ==================== MODERN BOT CARD WIDGET ====================

class BotCard(tk.Frame):
    """Modern card widget for displaying bot information"""
    
    def __init__(self, parent, bot_index: int, config: Optional[Dict] = None, parent_app=None):
        super().__init__(parent, relief=tk.RIDGE, borderwidth=1, bg='#f5f5f5')
        self.bot_index = bot_index
        self.process: Optional[subprocess.Popen] = None
        self.config_data = config or {}
        self.status_var = tk.StringVar(value="Stopped")
        self.window_status_thread = None
        self.window_status_stop = threading.Event()
        self.parent_app = parent_app
        
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """Create card UI components"""
        # Header with bot number and status
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=10)
        
        self.title_label = ttk.Label(
            header, text=f"Bot #{self.bot_index}", 
            font=("Segoe UI", 12, "bold")
        )
        self.title_label.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(
            header, textvariable=self.status_var,
            font=("Segoe UI", 9, "bold")
        )
        self.status_label.pack(side=tk.RIGHT)
        
        # Main content frame
        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create two columns
        left_col = ttk.Frame(content)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_col = ttk.Frame(content)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Left column fields
        self._create_field(left_col, "Symbol", "symbol", 0)
        self._create_field(left_col, "Lot Size", "lot_size", 1)
        self._create_field(left_col, "Max DD (%)", "max_dd", 2)
        self._create_field(left_col, "Max Spread", "max_spread", 3)
        
        # Right column fields
        self._create_field(right_col, "Max Open Trades", "max_open_trades", 0)
        self._create_field(right_col, "Close Profit ($)", "close_profit", 1)
        self._create_field(right_col, "Daily Target (%)", "daily_target", 2)
        
        # Terminal path and buttons frame
        path_frame = ttk.LabelFrame(self, text="MetaTrader 5", padding=10)
        path_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        path_container = ttk.Frame(path_frame)
        path_container.pack(fill=tk.X)
        
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(path_container, textvariable=self.path_var, width=50)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(
            path_container, text="📁 Browse",
            command=self._browse_terminal
        )
        browse_btn.pack(side=tk.LEFT)
        
        # Control buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.start_btn = ttk.Button(
            btn_frame, text="▶️ Start",
            command=self._start_bot
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            btn_frame, text="⏹️ Stop",
            command=self._stop_bot, state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        config_btn = ttk.Button(
            btn_frame, text="⚙️ Advanced",
            command=self._show_advanced
        )
        config_btn.pack(side=tk.LEFT, padx=5)
        
        delete_btn = ttk.Button(
            btn_frame, text="🗑️ Remove",
            command=self._delete_bot
        )
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Window status
        status_frame = ttk.LabelFrame(self, text="Window Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.window_status_label = ttk.Label(
            status_frame, text="Waiting...",
            font=("Courier", 10)
        )
        self.window_status_label.pack()
    
    def _create_field(self, parent: tk.Widget, label: str, key: str, row: int) -> None:
        """Create a labeled input field"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame, text=label, width=15).pack(side=tk.LEFT)
        
        var = tk.StringVar(value=str(self.config_data.get(key, "")))
        entry = ttk.Entry(frame, textvariable=var, width=20)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        setattr(self, f"{key}_var", var)
    
    def _browse_terminal(self) -> None:
        """Browse for MetaTrader 5 terminal"""
        path = filedialog.askopenfilename(
            title="Select MetaTrader 5 Terminal",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if path:
            self.path_var.set(path)
    
    def _start_bot(self) -> None:
        """Start the trading bot"""
        config = self._get_config()
        validation = validate_bot_parameters(config)
        
        if not validation.is_valid:
            messagebox.showerror(
                "Configuration Error",
                "Please fix the following errors:\n" + "\n".join(validation.errors)
            )
            return
        
        try:
            # Initialize MT5
            if not mt5.initialize(self.path_var.get()):
                messagebox.showerror("MT5 Error", "Failed to initialize MetaTrader 5")
                return
            
            account = get_mt5_account_info()
            if account:
                logger.info(f"Connected to account: {account['login']} ({account['name']})")
            mt5.shutdown()
            
            # Start bot process
            cmd = self._build_command(config)
            self.process = subprocess.Popen(cmd)
            
            self.status_var.set("Running ▶️")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            logger.info(f"Bot #{self.bot_index} started")
            
            # Start window status monitor
            self.window_status_stop.clear()
            self.window_status_thread = threading.Thread(
                target=self._monitor_window_status,
                daemon=True
            )
            self.window_status_thread.start()
            
        except Exception as e:
            messagebox.showerror("Start Error", str(e))
            self.status_var.set("Error ❌")
            logger.error(f"Error starting bot: {e}", exc_info=True)
    
    def _stop_bot(self) -> None:
        """Stop the trading bot"""
        try:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            
            self.window_status_stop.set()
            self.status_var.set("Stopped ⏹️")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            logger.info(f"Bot #{self.bot_index} stopped")
            
        except Exception as e:
            messagebox.showerror("Stop Error", str(e))
            logger.error(f"Error stopping bot: {e}")
    
    def _show_advanced(self) -> None:
        """Show advanced configuration dialog"""
        dialog = tk.Toplevel()
        dialog.title(f"Advanced Settings - Bot #{self.bot_index}")
        dialog.geometry("400x300")
        
        # Add advanced options here
        ttk.Label(dialog, text="Coming in next update", font=("Segoe UI", 12)).pack(pady=20)
    
    def _build_command(self, config: Dict[str, Any]) -> List[str]:
        """Build command to start bot subprocess"""
        return [
            "python", "Aventa_Hybrid_PPO_v9.py",
            "--mt5_path", self.path_var.get(),
            "--symbol", config.get('symbol', ''),
            "--lot_size", config.get('lot_size', '0.01'),
            "--close_profit", config.get('close_profit', '0.5'),
            "--max_open_trades", config.get('max_open_trades', '5'),
            "--max_spread", config.get('max_spread', '0.5'),
        ]
    
    def _monitor_window_status(self) -> None:
        """Monitor bot window status"""
        while not self.window_status_stop.is_set():
            try:
                status_file = f"window_status_{self.bot_index}.json"
                if os.path.exists(status_file):
                    with open(status_file) as f:
                        data = json.load(f)
                    
                    count = data.get('window_open_count', 0)
                    limit = data.get('window_limit', 50)
                    elapsed = data.get('window_time_left', 0)
                    is_pause = data.get('is_pause', False)
                    
                    mode = "PAUSE ⏸️" if is_pause else "ACTIVE ✓"
                    status_text = f"{count}/{limit} | {elapsed}s | {mode}"
                    self.window_status_label.config(text=status_text)
                    
            except Exception as e:
                logger.debug(f"Error reading window status: {e}")
            
            time.sleep(0.5)
    
    def _get_config(self) -> Dict[str, Any]:
        """Get current configuration from widgets"""
        return {
            'symbol': getattr(self, 'symbol_var', tk.StringVar()).get(),
            'lot_size': getattr(self, 'lot_size_var', tk.StringVar()).get(),
            'max_dd': getattr(self, 'max_dd_var', tk.StringVar()).get(),
            'mt5_path': self.path_var.get(),
            'close_profit': getattr(self, 'close_profit_var', tk.StringVar()).get(),
            'max_open_trades': getattr(self, 'max_open_trades_var', tk.StringVar()).get(),
            'max_spread': getattr(self, 'max_spread_var', tk.StringVar()).get(),
        }
    
    def _delete_bot(self) -> None:
        """Remove this bot from the launcher"""
        response = messagebox.askyesno(
            "Remove Bot",
            f"Are you sure you want to remove Bot #{self.bot_index}?"
        )
        
        if response:
            self._stop_bot()
            time.sleep(0.5)
            
            if hasattr(self.parent_app, 'bots'):
                try:
                    self.parent_app.bots.remove(self)
                    self.destroy()
                    logger.info(f"Bot #{self.bot_index} removed successfully")
                    
                    # Renumber remaining bots
                    for idx, bot in enumerate(self.parent_app.bots, 1):
                        bot.bot_index = idx
                        bot.title_label.config(text=f"Bot #{idx}")
                except Exception as e:
                    logger.error(f"Error removing bot: {e}")
                    messagebox.showerror("Error", f"Failed to remove bot: {e}")

# ==================== MAIN APPLICATION ====================

class ModernLauncher(tk.Tk):
    """Modern trading bot launcher application"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Aventa HFT Hybrid PPO v9.0 - Modern Launcher")
        self.geometry("1200x700")
        self.minsize(800, 500)
        
        # Style configuration
        self.style = ttk.Style()
        self._configure_styles()
        
        # Setup theme
        self.style.theme_use('clam')
        
        self.bots: List[BotCard] = []
        self.bot_frames: List[ttk.Frame] = []
        
        self._create_ui()
        self._load_config()
        self._setup_logging_display()
    
    def _configure_styles(self) -> None:
        """Configure modern UI styles"""
        self.style.configure('Header.TLabel', font=("Segoe UI", 14, "bold"))
        self.style.configure('Subheader.TLabel', font=("Segoe UI", 11, "bold"))
        self.style.configure('Title.TLabel', font=("Segoe UI", 16, "bold"))
    
    def _create_ui(self) -> None:
        """Create main UI components"""
        # Top banner
        banner = ttk.Frame(self)
        banner.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(
            banner, text="🚀 Aventa HFT Pro Trading System",
            style='Title.TLabel'
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            banner, text="v9.0 Modern Edition",
            font=("Segoe UI", 10, "italic")
        ).pack(side=tk.LEFT, padx=10)
        
        # Bottom control panel (ATAS tab)
        self._create_control_panel()
        
        # Separator line
        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, padx=20, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        # Tab 1: Bot Management
        self._create_bot_management_tab()
        
        # Tab 2: Settings
        self._create_settings_tab()
        
        # Tab 3: Logs
        self._create_logs_tab()
        
        # Tab 4: Info
        self._create_info_tab()
    
    def _create_bot_management_tab(self) -> None:
        """Create bot management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🤖 Bot Management")
        
        # Frame with scrollbar using mousewheel_support
        self.bot_container = tk.Frame(tab, bg="white")
        self.bot_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add initial bot
        self._add_bot_card()
    
    def _create_settings_tab(self) -> None:
        """Create settings tab"""
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text="⚙️ Settings")
        
        # Global settings
        ttk.Label(tab, text="Global Settings", style='Subheader.TLabel').pack(anchor=tk.W)
        
        settings_frame = ttk.LabelFrame(tab, text="Window Timing Control", padding=10)
        settings_frame.pack(fill=tk.X, pady=10)
        
        # ON duration
        ttk.Label(settings_frame, text="Trading Window (seconds):").grid(row=0, column=0, sticky=tk.W)
        self.on_seconds_var = tk.StringVar(value="60")
        ttk.Entry(settings_frame, textvariable=self.on_seconds_var, width=10).grid(row=0, column=1, sticky=tk.W)
        
        # PAUSE duration
        ttk.Label(settings_frame, text="Pause Window (seconds):").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.pause_seconds_var = tk.StringVar(value="10")
        ttk.Entry(settings_frame, textvariable=self.pause_seconds_var, width=10).grid(row=1, column=1, sticky=tk.W)
        
        # MT5 Path
        path_frame = ttk.LabelFrame(tab, text="MetaTrader 5 Default Path", padding=10)
        path_frame.pack(fill=tk.X, pady=10)
        
        self.mt5_default_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.mt5_default_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Browse", command=self._browse_mt5_default).pack(side=tk.LEFT, padx=5)
    
    def _create_logs_tab(self) -> None:
        """Create logs tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📋 Logs")
        
        # Log viewer
        ttk.Label(tab, text="Application Logs", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            tab, height=20, font=("Courier", 9),
            bg="#f5f5f5", fg="#212121"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Control buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="🔄 Refresh", command=self._refresh_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Clear", command=self._clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 Save", command=self._save_logs).pack(side=tk.LEFT, padx=5)
        
        # Auto-refresh logs
        self._refresh_logs()
    
    def _create_info_tab(self) -> None:
        """Create information tab"""
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text="ℹ️ About")
        
        # Version info
        info_frame = ttk.LabelFrame(tab, text="System Information", padding=15)
        info_frame.pack(fill=tk.X, pady=10)
        
        info_data = [
            ("Application", "Aventa HFT Hybrid PPO"),
            ("Version", "v9.0 Modern Edition"),
            ("Created", "31 January 2026"),
            ("Status", "✅ Production Ready"),
            ("Python Version", f"{__import__('sys').version.split()[0]}"),
            ("Log File", LOG_FILE),
            ("Config File", CONFIG_FILE),
        ]
        
        for label, value in info_data:
            ttk.Label(info_frame, text=f"{label}:").pack(anchor=tk.W, pady=2)
            ttk.Label(info_frame, text=value, font=("Courier", 10), foreground="blue").pack(anchor=tk.W, padx=20, pady=(0, 5))
        
        # Features
        features_frame = ttk.LabelFrame(tab, text="Features", padding=15)
        features_frame.pack(fill=tk.X, pady=10)
        
        features = [
            "✓ Modern Tabbed Interface",
            "✓ Real-time Bot Monitoring",
            "✓ Advanced Configuration",
            "✓ Live Log Viewer",
            "✓ Multi-Bot Management",
            "✓ Professional UI Design",
        ]
        
        for feature in features:
            ttk.Label(features_frame, text=feature).pack(anchor=tk.W, pady=3)
    
    def _create_control_panel(self) -> None:
        """Create control panel with all buttons"""
        # Control panel frame
        panel = ttk.Frame(self)
        panel.pack(fill=tk.X, padx=20, pady=10)
        
        # Left side buttons
        left_frame = ttk.Frame(panel)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_frame, text="➕ Add Bot", command=self._add_bot_card).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_frame, text="🔄 Refresh", command=self._refresh_all).pack(side=tk.LEFT, padx=5)
        
        # Middle buttons
        middle_frame = ttk.Frame(panel)
        middle_frame.pack(side=tk.LEFT, expand=True, padx=20)
        
        ttk.Button(middle_frame, text="▶️ Start All", command=self._start_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(middle_frame, text="⏹️ Stop All", command=self._stop_all).pack(side=tk.LEFT, padx=5)
        
        # Right side buttons
        right_frame = ttk.Frame(panel)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_frame, text="💾 Save Config", command=self._save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_frame, text="📂 Load Config", command=self._load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_frame, text="❌ Exit", command=self._exit_app).pack(side=tk.LEFT, padx=5)
    
    def _add_bot_card(self) -> None:
        """Add new bot card"""
        bot_index = len(self.bots) + 1
        bot = BotCard(self.bot_container, bot_index, parent_app=self)
        bot.pack(fill=tk.X, pady=10)
        self.bots.append(bot)
        logger.info(f"Added bot #{bot_index}")
    
    def _start_all(self) -> None:
        """Start all bots"""
        for bot in self.bots:
            if bot.status_var.get() != "Running ▶️":
                bot._start_bot()
                time.sleep(0.5)
    
    def _stop_all(self) -> None:
        """Stop all bots"""
        for bot in self.bots:
            if bot.status_var.get() == "Running ▶️":
                bot._stop_bot()
                time.sleep(0.5)
    
    def _refresh_all(self) -> None:
        """Refresh all information"""
        self._refresh_logs()
        for bot in self.bots:
            if hasattr(bot, '_monitor_window_status'):
                # Window status will auto-update
                pass
    
    def _refresh_logs(self) -> None:
        """Refresh log display"""
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    logs = f.read()
                
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, logs)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.NORMAL)
        except Exception as e:
            logger.error(f"Error refreshing logs: {e}")
    
    def _clear_logs(self) -> None:
        """Clear log file"""
        if messagebox.askyesno("Confirm", "Clear all logs?"):
            try:
                open(LOG_FILE, 'w').close()
                self.log_text.delete(1.0, tk.END)
                logger.info("Logs cleared")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear logs: {e}")
    
    def _save_logs(self) -> None:
        """Save logs to file"""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if path:
            try:
                with open(path, 'w') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Logs saved to {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {e}")
    
    def _save_config(self) -> None:
        """Save all bot configurations"""
        try:
            configs = [bot._get_config() for bot in self.bots]
            with open(CONFIG_FILE, 'w') as f:
                json.dump(configs, f, indent=2)
            messagebox.showinfo("Success", f"Configuration saved to {CONFIG_FILE}")
            logger.info(f"Saved {len(configs)} bot configurations")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
    
    def _load_config(self) -> None:
        """Load bot configurations"""
        try:
            if not os.path.exists(CONFIG_FILE):
                return
            
            with open(CONFIG_FILE, 'r') as f:
                configs = json.load(f)
            
            # Clear existing bots
            for bot in self.bots:
                bot.destroy()
            self.bots.clear()
            
            # Load saved configs
            for config in configs:
                bot = BotCard(self.bot_container, len(self.bots) + 1, config, parent_app=self)
                bot.pack(fill=tk.X, pady=10)
                self.bots.append(bot)
            
            logger.info(f"Loaded {len(configs)} bot configurations")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    def _browse_mt5_default(self) -> None:
        """Browse for default MT5 path"""
        path = filedialog.askopenfilename(
            title="Select MetaTrader 5 Terminal",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if path:
            self.mt5_default_var.set(path)
    
    def _exit_app(self) -> None:
        """Exit application gracefully"""
        if messagebox.askyesno("Confirm", "Stop all bots and exit?"):
            self._stop_all()
            time.sleep(1)
            self.quit()
    
    def _setup_logging_display(self) -> None:
        """Setup periodic log refresh"""
        def refresh_loop():
            while True:
                time.sleep(2)
                try:
                    self._refresh_logs()
                except:
                    pass
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()

# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Aventa HFT Hybrid PPO v9.0 - Modern Launcher Starting...")
    logger.info("=" * 60)
    
    try:
        app = ModernLauncher()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Application closed")
        logger.info("=" * 60)
