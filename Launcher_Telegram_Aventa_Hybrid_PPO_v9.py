import os
import json
import subprocess
import threading
import queue
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import MetaTrader5 as mt5

# --- Konfigurasi ---
CONFIG_FILE = "launcher_config.json"
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "Aventa_Hybrid_PPO_v9.py")
TELEGRAM_TOKEN = "8570175031:AAGDnWMAKrfAOVa8Ayahwru4wTHWhsf_8yE"  # Ganti dengan token bot Telegram Anda
ALLOWED_USER_IDS = []  # Kosongkan untuk allow semua user, atau isi dengan list [123456789, 987654321]

# Conversation states untuk edit bot
EDIT_FIELD = range(1)

class BotInstance:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.process = None
        self.thread = None
        self.output_queue = queue.Queue()
        self.running = False
        self.margin_alert_sent = False  # flag agar notifikasi tidak berulang

    def start(self):
        if self.running:
            return "Bot sudah running"
        
        args = [
            "python", "-u", SCRIPT_PATH,
            "--auto",
            "--mt5_path", self.config.get("MT5_PATH", ""),
            "--symbol", self.config.get("SYMBOL", "GOLD"),
            "--lot", str(self.config.get("LOT", 0.01)),
            "--tp_pips", str(self.config.get("TP_PIPS", 5)),
            "--sl_pips", str(self.config.get("SL_PIPS", 0)),
            "--max_trades", str(self.config.get("MAX_TRADES", 3)),
            "--deviation", str(self.config.get("DEVIATION", 10)),
            "--magic", str(self.config.get("MAGIC_NUMBER", 112233)),
            "--type_filling", self.config.get("TYPE_FILLING", "IOC"),
            "--margin_level_warn", str(self.config.get("MARGIN_LEVEL_WARN", 5600))
        ]
        
        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.running = True
            self.thread = threading.Thread(target=self._read_output, daemon=True)
            self.thread.start()
            return f"✅ Bot {self.name} berhasil distart"
        except Exception as e:
            return f"❌ Error starting bot: {e}"

    def stop(self):
        if not self.running:
            return "Bot sudah stopped"
        
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=5)
            self.running = False
            return f"✅ Bot {self.name} berhasil distop"
        except Exception as e:
            try:
                self.process.kill()
                self.running = False
                return f"✅ Bot {self.name} berhasil distop (forced)"
            except Exception:
                return f"❌ Error stopping bot: {e}"

    def _read_output(self):
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_queue.put(line.strip())
                if self.process.poll() is not None:
                    break
        except Exception:
            pass
        finally:
            try:
                self.process.stdout.close()
            except Exception:
                pass
            self.running = False

        # Cek margin level secara periodik
        while self.running and self.process and self.process.poll() is None:
            self.check_margin_level_and_notify()
            time.sleep(5)  # cek setiap 5 detik

    def check_margin_level_and_notify(self):
        try:
            if not mt5.initialize(self.config.get("MT5_PATH", "")):
                return
            account_info = mt5.account_info()
            if account_info is None:
                mt5.shutdown()
                return
            margin_level = getattr(account_info, "margin_level", None)
            margin_level_warn = float(self.config.get("MARGIN_LEVEL_WARN", 5600))
            if margin_level is not None and margin_level < margin_level_warn:
                if not self.margin_alert_sent:
                    send_telegram_alert(
                        f"⚠️ Margin Level rendah pada bot '{self.name}'!\nMargin Level: {margin_level:.2f}% (Batas: {margin_level_warn:.2f}%)"
                    )
                    self.margin_alert_sent = True
            else:
                self.margin_alert_sent = False
            mt5.shutdown()
        except Exception:
            pass

    def get_status(self):
        if self.process and self.process.poll() is None:
            self.running = True
            return "🟢 Running"
        else:
            self.running = False
            return "🔴 Stopped"

class TelegramBotManager:
    def __init__(self):
        self.bots = []
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    for bot_data in data.get("bots", []):
                        bot = BotInstance(bot_data["name"], bot_data["config"])
                        self.bots.append(bot)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        data = {
            "bots": [{"name": bot.name, "config": bot.config} for bot in self.bots]
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def add_bot(self, name, config):
        bot = BotInstance(name, config)
        self.bots.append(bot)
        self.save_config()
        return f"✅ Bot {name} berhasil ditambahkan"

    def remove_bot(self, index):
        if 0 <= index < len(self.bots):
            bot = self.bots[index]
            if bot.running:
                return "❌ Stop bot terlebih dahulu sebelum menghapus"
            name = bot.name
            self.bots.pop(index)
            self.save_config()
            return f"✅ Bot {name} berhasil dihapus"
        return "❌ Bot tidak ditemukan"

    def start_bot(self, index):
        if 0 <= index < len(self.bots):
            return self.bots[index].start()
        return "❌ Bot tidak ditemukan"

    def stop_bot(self, index):
        if 0 <= index < len(self.bots):
            return self.bots[index].stop()
        return "❌ Bot tidak ditemukan"

    def start_all(self):
        messages = []
        for bot in self.bots:
            if not bot.running:
                msg = bot.start()
                messages.append(msg)
        return "\n".join(messages) if messages else "✅ Semua bot sudah running"

    def stop_all(self):
        messages = []
        for bot in self.bots:
            if bot.running:
                msg = bot.stop()
                messages.append(msg)
        return "\n".join(messages) if messages else "✅ Semua bot sudah stopped"

    def get_status(self):
        if not self.bots:
            return "📋 Tidak ada bot yang terdaftar"
        
        status_lines = ["📊 *Status Bot:*\n"]
        for i, bot in enumerate(self.bots):
            status = bot.get_status()
            symbol = bot.config.get("SYMBOL", "N/A")
            lot = bot.config.get("LOT", "N/A")
            # Ambil margin level
            margin_level_str = "N/A"
            try:
                if mt5.initialize(bot.config.get("MT5_PATH", "")):
                    account_info = mt5.account_info()
                    if account_info and getattr(account_info, "margin_level", None) is not None:
                        margin_level_str = f"{account_info.margin_level:.2f}%"
                    mt5.shutdown()
            except Exception:
                margin_level_str = "N/A"
            status_lines.append(f"{i+1}. *{bot.name}*")
            status_lines.append(f"   Symbol: {symbol} | Lot: {lot}")
            status_lines.append(f"   Status: {status}")
            status_lines.append(f"   Margin Level: {margin_level_str}\n")
        
        return "\n".join(status_lines)

    def edit_bot_field(self, index, field, value):
        if 0 <= index < len(self.bots):
            bot = self.bots[index]
            if bot.running:
                return "❌ Stop bot terlebih dahulu sebelum mengedit"
            try:
                # Convert value sesuai field
                if field in ["SYMBOL", "MT5_PATH", "TYPE_FILLING"]:
                    bot.config[field] = str(value)
                elif field in ["LOT", "TP_PIPS", "SL_PIPS"]:
                    bot.config[field] = float(value)
                elif field in ["MAX_TRADES", "DEVIATION", "MAGIC_NUMBER"]:
                    bot.config[field] = int(value)
                elif field == "MARGIN_LEVEL_WARN":
                    bot.config[field] = float(value)
                elif field == "name":
                    bot.name = str(value)
                else:
                    return "❌ Field tidak valid"
                self.save_config()
                return f"✅ {field} berhasil diupdate menjadi {value}"
            except ValueError:
                return f"❌ Nilai tidak valid untuk {field}"
        return "❌ Bot tidak ditemukan"

# Global manager instance
manager = TelegramBotManager()

# --- Authorization check ---
def is_authorized(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki akses ke bot ini.")
        return
    
    welcome_text = """
🤖 *AV-BitSonic Bot Launcher*

Selamat datang! Gunakan command berikut:

/status - Lihat status semua bot
/startbot <nomor> - Start bot tertentu
/stopbot <nomor> - Stop bot tertentu
/startall - Start semua bot
/stopall - Stop semua bot
/list - Lihat daftar bot dengan menu
/help - Tampilkan help ini
    """
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki akses.")
        return
    
    status_text = manager.get_status()
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def list_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki akses.")
        return
    
    if not manager.bots:
        await update.message.reply_text("📋 Tidak ada bot yang terdaftar")
        return
    
    keyboard = []
    for i, bot in enumerate(manager.bots):
        status_icon = "🟢" if bot.running else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                f"{status_icon} {bot.name}", 
                callback_data=f"info_{i}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🟢 Start All", callback_data="startall"),
        InlineKeyboardButton("🔴 Stop All", callback_data="stopall")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📋 *Daftar Bot:*\nPilih bot untuk melihat detail dan kontrol",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def startbot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki akses.")
        return
    
    if not context.args:
        await update.message.reply_text("Gunakan: /startbot <nomor>\nContoh: /startbot 1")
        return
    
    try:
        index = int(context.args[0]) - 1
        result = manager.start_bot(index)
        await update.message.reply_text(result)
    except ValueError:
        await update.message.reply_text("❌ Nomor bot tidak valid")

async def stopbot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki akses.")
        return
    
    if not context.args:
        await update.message.reply_text("Gunakan: /stopbot <nomor>\nContoh: /stopbot 1")
        return
    
    try:
        index = int(context.args[0]) - 1
        result = manager.stop_bot(index)
        await update.message.reply_text(result)
    except ValueError:
        await update.message.reply_text("❌ Nomor bot tidak valid")

async def startall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki akses.")
        return
    
    result = manager.start_all()
    await update.message.reply_text(result)

async def stopall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Anda tidak memiliki akses.")
        return
    
    result = manager.stop_all()
    await update.message.reply_text(result)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# --- Callback Query Handler ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_authorized(user_id):
        await query.answer("❌ Anda tidak memiliki akses")
        return
    
    await query.answer()
    
    data = query.data
    
    if data == "startall":
        result = manager.start_all()
        await query.edit_message_text(result)
    
    elif data == "stopall":
        result = manager.stop_all()
        await query.edit_message_text(result)
    
    elif data.startswith("info_"):
        index = int(data.split("_")[1])
        if 0 <= index < len(manager.bots):
            bot = manager.bots[index]
            status = bot.get_status()
            
            info_text = f"*{bot.name}*\n\n"
            info_text += f"Status: {status}\n"
            info_text += f"Symbol: {bot.config.get('SYMBOL', 'N/A')}\n"
            info_text += f"Lot: {bot.config.get('LOT', 'N/A')}\n"
            info_text += f"TP: {bot.config.get('TP_PIPS', 'N/A')} pips\n"
            info_text += f"SL: {bot.config.get('SL_PIPS', 'N/A')} pips\n"
            info_text += f"Max Trades: {bot.config.get('MAX_TRADES', 'N/A')}\n"
            info_text += f"Magic: {bot.config.get('MAGIC_NUMBER', 'N/A')}\n"
            info_text += f"Filling: {bot.config.get('TYPE_FILLING', 'N/A')}\n"
            
            keyboard = []
            if bot.running:
                keyboard.append([InlineKeyboardButton("🔴 Stop Bot", callback_data=f"stop_{index}")])
            else:
                keyboard.append([InlineKeyboardButton("🟢 Start Bot", callback_data=f"start_{index}")])
            
            # Tambahkan tombol Edit hanya jika bot tidak running
            if not bot.running:
                keyboard.append([InlineKeyboardButton("⚙️ Edit Bot", callback_data=f"edit_{index}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data.startswith("edit_"):
        index = int(data.split("_")[1])
        if 0 <= index < len(manager.bots):
            bot = manager.bots[index]
            
            edit_text = f"⚙️ *Edit {bot.name}*\n\nPilih field yang ingin diubah:"
            
            keyboard = [
                [InlineKeyboardButton("📝 Name", callback_data=f"editfield_{index}_name")],
                [InlineKeyboardButton("💱 Symbol", callback_data=f"editfield_{index}_SYMBOL")],
                [InlineKeyboardButton("📊 Lot", callback_data=f"editfield_{index}_LOT")],
                [InlineKeyboardButton("🎯 TP Pips", callback_data=f"editfield_{index}_TP_PIPS")],
                [InlineKeyboardButton("🛡️ SL Pips", callback_data=f"editfield_{index}_SL_PIPS")],
                [InlineKeyboardButton("🔢 Max Trades", callback_data=f"editfield_{index}_MAX_TRADES")],
                [InlineKeyboardButton("📈 Deviation", callback_data=f"editfield_{index}_DEVIATION")],
                [InlineKeyboardButton("🔮 Magic Number", callback_data=f"editfield_{index}_MAGIC_NUMBER")],
                [InlineKeyboardButton("⚡ Type Filling", callback_data=f"editfield_{index}_TYPE_FILLING")],
                [InlineKeyboardButton("🛑 Margin Level Warn", callback_data=f"editfield_{index}_MARGIN_LEVEL_WARN")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"info_{index}")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(edit_text, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data.startswith("editfield_"):
        parts = data.split("_", 2)
        index = int(parts[1])
        field = parts[2]
        
        # Simpan context untuk handler berikutnya
        context.user_data['edit_bot_index'] = index
        context.user_data['edit_bot_field'] = field
        
        bot = manager.bots[index]
        current_value = bot.config.get(field, "N/A") if field != "name" else bot.name
        
        prompt_text = f"⚙️ *Edit {field}*\n\n"
        prompt_text += f"Nilai saat ini: `{current_value}`\n\n"
        
        if field == "TYPE_FILLING":
            keyboard = [
                [InlineKeyboardButton("IOC", callback_data=f"setvalue_{index}_{field}_IOC")],
                [InlineKeyboardButton("FOK", callback_data=f"setvalue_{index}_{field}_FOK")],
                [InlineKeyboardButton("RETURN", callback_data=f"setvalue_{index}_{field}_RETURN")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"edit_{index}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(prompt_text + "Pilih Type Filling:", reply_markup=reply_markup, parse_mode="Markdown")
        elif field == "MARGIN_LEVEL_WARN":
            prompt_text += f"Kirim nilai baru untuk *{field}* (contoh: 500)\natau /cancel untuk batal"
            await query.edit_message_text(prompt_text, parse_mode="Markdown")
        else:
            prompt_text += f"Kirim nilai baru untuk *{field}*\natau /cancel untuk batal"
            await query.edit_message_text(prompt_text, parse_mode="Markdown")
    
    elif data.startswith("setvalue_"):
        parts = data.split("_", 3)
        index = int(parts[1])
        field = parts[2]
        value = parts[3]
        
        result = manager.edit_bot_field(index, field, value)
        await query.edit_message_text(result)
        
        # Kembali ke menu edit setelah 2 detik
        await asyncio.sleep(2)
        await show_edit_menu(query, index)
    
    elif data.startswith("start_"):
        index = int(data.split("_")[1])
        result = manager.start_bot(index)
        await query.edit_message_text(result)
    
    elif data.startswith("stop_"):
        index = int(data.split("_")[1])
        result = manager.stop_bot(index)
        await query.edit_message_text(result)
    
    elif data == "back":
        # Recreate list
        if not manager.bots:
            await query.edit_message_text("📋 Tidak ada bot yang terdaftar")
            return
        
        keyboard = []
        for i, bot in enumerate(manager.bots):
            status_icon = "🟢" if bot.running else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon} {bot.name}", 
                    callback_data=f"info_{i}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🟢 Start All", callback_data="startall"),
            InlineKeyboardButton("🔴 Stop All", callback_data="stopall")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📋 *Daftar Bot:*\nPilih bot untuk melihat detail dan kontrol",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# Handler untuk menerima input edit field
async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return
    
    if 'edit_bot_index' not in context.user_data or 'edit_bot_field' not in context.user_data:
        await update.message.reply_text("❌ Session edit expired. Silakan pilih bot lagi dari /list")
        return
    
    index = context.user_data['edit_bot_index']
    field = context.user_data['edit_bot_field']
    value = update.message.text.strip()
    
    result = manager.edit_bot_field(index, field, value)
    await update.message.reply_text(result)
    
    # Clear context
    context.user_data.pop('edit_bot_index', None)
    context.user_data.pop('edit_bot_field', None)
    
    # Show updated bot info
    bot = manager.bots[index]
    status = bot.get_status()
    
    info_text = f"*{bot.name}*\n\n"
    info_text += f"Status: {status}\n"
    info_text += f"Symbol: {bot.config.get('SYMBOL', 'N/A')}\n"
    info_text += f"Lot: {bot.config.get('LOT', 'N/A')}\n"
    info_text += f"TP: {bot.config.get('TP_PIPS', 'N/A')} pips\n"
    info_text += f"SL: {bot.config.get('SL_PIPS', 'N/A')} pips\n"
    info_text += f"Max Trades: {bot.config.get('MAX_TRADES', 'N/A')}\n"
    info_text += f"Magic: {bot.config.get('MAGIC_NUMBER', 'N/A')}\n"
    info_text += f"Filling: {bot.config.get('TYPE_FILLING', 'N/A')}\n"
    
    keyboard = [
        [InlineKeyboardButton("⚙️ Edit Bot", callback_data=f"edit_{index}")],
        [InlineKeyboardButton("🔙 Back to List", callback_data="back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(info_text, reply_markup=reply_markup, parse_mode="Markdown")

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('edit_bot_index', None)
    context.user_data.pop('edit_bot_field', None)
    await update.message.reply_text("❌ Edit dibatalkan")

# Helper function untuk show edit menu
async def show_edit_menu(query, index):
    bot = manager.bots[index]
    edit_text = f"⚙️ *Edit {bot.name}*\n\nPilih field yang ingin diubah:"
    
    keyboard = [
        [InlineKeyboardButton("📝 Name", callback_data=f"editfield_{index}_name")],
        [InlineKeyboardButton("💱 Symbol", callback_data=f"editfield_{index}_SYMBOL")],
        [InlineKeyboardButton("📊 Lot", callback_data=f"editfield_{index}_LOT")],
        [InlineKeyboardButton("🎯 TP Pips", callback_data=f"editfield_{index}_TP_PIPS")],
        [InlineKeyboardButton("🛡️ SL Pips", callback_data=f"editfield_{index}_SL_PIPS")],
        [InlineKeyboardButton("🔢 Max Trades", callback_data=f"editfield_{index}_MAX_TRADES")],
        [InlineKeyboardButton("📈 Deviation", callback_data=f"editfield_{index}_DEVIATION")],
        [InlineKeyboardButton("🔮 Magic Number", callback_data=f"editfield_{index}_MAGIC_NUMBER")],
        [InlineKeyboardButton("⚡ Type Filling", callback_data=f"editfield_{index}_TYPE_FILLING")],
        [InlineKeyboardButton("🛑 Margin Level Warn", callback_data=f"editfield_{index}_MARGIN_LEVEL_WARN")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"info_{index}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(edit_text, reply_markup=reply_markup, parse_mode="Markdown")

# Fungsi kirim notifikasi ke Telegram
def send_telegram_alert(message):
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Kirim ke semua user di ALLOWED_USER_IDS, jika kosong kirim ke chat id pertama yang interaksi
    chat_ids = ALLOWED_USER_IDS if ALLOWED_USER_IDS else []
    # Jika tidak ada chat id, skip
    if not chat_ids:
        return
    for chat_id in chat_ids:
        try:
            requests.post(url, data={"chat_id": chat_id, "text": message})
        except Exception:
            pass

def main():
    print("🤖 Starting AV-BitSonic Telegram Launcher...")
    print(f"📋 Loaded {len(manager.bots)} bot(s) from config")
    
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your TELEGRAM_TOKEN in the script!")
        print("   Get token from @BotFather on Telegram")
        return
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("list", list_bots))
    application.add_handler(CommandHandler("startbot", startbot_cmd))
    application.add_handler(CommandHandler("stopbot", stopbot_cmd))
    application.add_handler(CommandHandler("startall", startall_cmd))
    application.add_handler(CommandHandler("stopall", stopall_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("cancel", cancel_edit))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Handler untuk menerima text input saat edit
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_input))
    
    # Start bot
    print("✅ Telegram Bot is running...")
    print("   Send /start to your bot to begin")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    import asyncio
    main()
