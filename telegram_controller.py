import os
import json
import shlex
import psutil
import signal
import subprocess
import time
import traceback
import threading
from pathlib import Path
from typing import Dict, Any, List
from types import SimpleNamespace

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# ============================
#  CONFIG & ENV
# ============================
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "bot_config.json"          # Shared with Launcher
PID_PATH     = BASE_DIR / "aventa_bot.pid"          # Store running PID
LOG_PATH     = BASE_DIR / "controller.log"          # Simple text log
# New: dedicated telegram user command log
TELEGRAM_USERS_LOG_PATH = BASE_DIR / "telegram_users.log"

# Load environment variables
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
ALLOWED_CHAT_IDS = {
    cid.strip() for cid in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if cid.strip()
}

AVENTA_FILE = os.getenv("AVENTA_FILE", "Aventa_Hybrid_PPO_v9.py")
# New: enable debug via .env DEBUG=1/true/yes
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes", "on")

# ============================
#  UTILITIES
# ============================
def log(msg: str, level: str = "INFO") -> None:
    """Write timestamped message to log file and print to console.
    When DEBUG=False, DEBUG-level messages are still written but printing is kept for traceability.
    """
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{level}] {msg}"
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # best-effort, but still print
        pass
    # Always print to console; include extra visibility when DEBUG
    if DEBUG or level != "DEBUG":
        print(line)
    else:
        # still print debug to console if DEBUG enabled (handled above); if not, print minimal
        print(line)

def load_config_list() -> List[Dict[str, Any]]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
            if isinstance(cfg, list):
                return cfg
            elif isinstance(cfg, dict):
                return [cfg]
    return [{}]

def save_config_list(cfg_list: List[Dict[str, Any]]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg_list, f, indent=2)

def coerce_value(v: str):
    # convert string to int/float/bool if applicable
    vl = v.lower()
    if vl in {"true","yes","on"}:
        return True
    if vl in {"false","no","off"}:
        return False
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v

def type_filling_to_int(val: str) -> int:
    m = {"FOK":1, "IOC":2, "RET":3, "ORDER_FILLING_FOK":1, "ORDER_FILLING_IOC":2, "ORDER_FILLING_RETURN":3, "RETURN":3}
    return m.get(str(val).strip().upper(), 2)  # default IOC=2

def build_cmd_from_config(conf: Dict[str, Any]) -> List[str]:
    # Required mapping; provide safe defaults. Accept common aliases for keys.
    mt5_path = str(conf.get("mt5_path", conf.get("path", "")))
    symbol = str(conf.get("symbol", "XAUUSD"))
    # accept both "lot_size" and legacy "lot"
    lot_size = str(conf.get("lot_size", conf.get("lot", "0.01")))
    close_profit = str(conf.get("close_profit", "1.0"))
    max_open_trades = str(conf.get("max_open_trades", "3"))
    # type_filling may be given as text (FOK/IOC/RET) or numeric; controller will convert
    type_filling = str(type_filling_to_int(conf.get("type_filling", "IOC")))
    max_spread = str(conf.get("max_spread", "30"))
    ppo_model_path = str(conf.get("ppo_model_path", conf.get("model_path", "")))
    start_trading_hour = str(conf.get("start_trading_hour", "9"))
    end_trading_hour = str(conf.get("end_trading_hour", "17"))
    daily_target = str(conf.get("daily_target", "2.0"))
    max_dd = str(conf.get("max_dd", "5.0"))
    window_open_limit = str(conf.get("window_open_limit", "50"))
    window_on_seconds = str(conf.get("window_on_seconds", "60"))
    window_pause_seconds = str(conf.get("window_pause_seconds", "10"))

    args = [
        "python", AVENTA_FILE,
        "--mt5_path", mt5_path,
        "--symbol", symbol,
        "--lot_size", lot_size,
        "--close_profit", close_profit,
        "--max_open_trades", max_open_trades,
        "--type_filling", type_filling,
        "--max_spread", max_spread,
        "--ppo_model_path", ppo_model_path,
        "--start_trading_hour", start_trading_hour,
        "--end_trading_hour", end_trading_hour,
        "--daily_target", daily_target,
        "--max_dd", max_dd,
        "--window_open_limit", window_open_limit,
        "--window_on_seconds", window_on_seconds,
        "--window_pause_seconds", window_pause_seconds,
    ]

    # reverse may be boolean-like
    if str(conf.get("reverse", "")).lower() in {"true", "1", "yes", "on"}:
        args.append("--reverse")

    try:
        log(f"Built command: {' '.join(shlex.quote(a) for a in args)}", "DEBUG")
    except Exception:
        log(f"Built command (unrepresentable args): {args}", "DEBUG")
    return args

def is_pid_running(pid: int) -> bool:
    return psutil.pid_exists(pid) and psutil.Process(pid).is_running()

# New helper: record who invoked a telegram command (timestamp, chat id, user, command text)
def record_telegram_user(update) -> None:
    try:
        # Support regular messages, edited messages and callback_query messages
        msg = getattr(update, "message", None) \
              or getattr(update, "edited_message", None) \
              or (getattr(update, "callback_query", None).message if getattr(update, "callback_query", None) else None)
        chat = getattr(update, "effective_chat", None) \
               or (msg.chat if msg is not None else None)
        user = getattr(update, "effective_user", None) \
               or (getattr(update, "callback_query", None).from_user if getattr(update, "callback_query", None) else None) \
               or (msg.from_user if msg is not None and getattr(msg, "from_user", None) else None)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        chat_id = getattr(chat, "id", "(no-chat)")
        user_id = getattr(user, "id", "(no-user)")
        username = getattr(user, "username", "")
        first_name = getattr(user, "first_name", "")
        last_name = getattr(user, "last_name", "")
        text = msg.text.replace("\n", " ") if (msg and getattr(msg, "text", None)) else ""
        line = f"{ts} | chat_id={chat_id} | user_id={user_id} | username={username} | name=\"{first_name} {last_name}\" | text=\"{text}\""
        TELEGRAM_USERS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TELEGRAM_USERS_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        log(f"record_telegram_user: {chat_id}/{user_id} recorded", "DEBUG")
    except Exception as e:
        # do not raise; best-effort logging
        log(f"record_telegram_user: failed to write user log: {e}", "ERROR")

# New helpers to manage multiple PIDs in PID_PATH (JSON list)
def read_pids() -> List[int]:
    if PID_PATH.exists():
        try:
            data = PID_PATH.read_text(encoding="utf-8").strip()
            if not data:
                log("read_pids: pid file empty", "DEBUG")
                return []
            pids = json.loads(data)
            if isinstance(pids, int):
                pids = [pids]
            if isinstance(pids, list):
                # filter to only currently running pids
                valid = []
                for p in pids:
                    try:
                        pi = int(p)
                        if is_pid_running(pi):
                            valid.append(pi)
                        else:
                            log(f"read_pids: pid {pi} not running, ignoring", "DEBUG")
                    except Exception as e:
                        log(f"read_pids: invalid pid entry {p}: {e}", "DEBUG")
                        continue
                log(f"read_pids -> {valid}", "DEBUG")
                return valid
        except Exception as e:
            log(f"read_pids: error reading pid file: {e}\n{traceback.format_exc()}", "ERROR")
    return []

def write_pids(pids: List[int]) -> None:
    try:
        PID_PATH.parent.mkdir(parents=True, exist_ok=True)
        PID_PATH.write_text(json.dumps(pids), encoding="utf-8")
        log(f"write_pids: wrote {pids}", "DEBUG")
    except Exception as e:
        log(f"write_pids: failed to write {pids}: {e}\n{traceback.format_exc()}", "ERROR")

def add_pid(pid: int) -> None:
    pids = read_pids()
    if pid not in pids:
        pids.append(pid)
        write_pids(pids)
        log(f"add_pid: added {pid}", "INFO")
    else:
        log(f"add_pid: pid {pid} already present", "DEBUG")

def remove_pid(pid: int) -> None:
    pids = read_pids()
    pids = [p for p in pids if p != pid]
    if pids:
        write_pids(pids)
        log(f"remove_pid: removed {pid}, remaining {pids}", "INFO")
    else:
        try:
            PID_PATH.unlink(missing_ok=True)
            log(f"remove_pid: removed last pid {pid}, pid file deleted", "INFO")
        except Exception as e:
            log(f"remove_pid: error removing pid file: {e}\n{traceback.format_exc()}", "ERROR")

def current_pid() -> int:
    # keep compatibility: return first running pid or 0
    pids = read_pids()
    return pids[0] if pids else 0

def ensure_allowed(update) -> bool:
    if not ALLOWED_CHAT_IDS:
        # If not set, allow first user and record them:
        chat_id = str(update.effective_chat.id)
        ALLOWED_CHAT_IDS.add(chat_id)
        # persist in .env (best-effort)
        try:
            envp = BASE_DIR / ".env"
            lines = envp.read_text().splitlines() if envp.exists() else []
            d = {k:(v if "=" in v else None) for k,v in (l.split("=",1) for l in lines if "=" in l)}
            d["ALLOWED_CHAT_IDS"] = ",".join(sorted(ALLOWED_CHAT_IDS))
            envp.write_text("\n".join([f"{k}={v}" for k,v in d.items()]))
        except Exception as e:
            log(f"[WARN] Unable to persist ALLOWED_CHAT_IDS: {e}")
        return True
    return str(update.effective_chat.id) in ALLOWED_CHAT_IDS

def require_auth(func):
    async def wrapper(update, context):
        # record every incoming command attempt (best-effort)
        try:
            record_telegram_user(update)
        except Exception:
            # ensure recording failures don't block execution
            log("require_auth: record_telegram_user failed", "DEBUG")
        if not ensure_allowed(update):
            await update.message.reply_text("Unauthorized. Contact the bot owner.")
            return
        return await func(update, context)
    return wrapper

# ============================
#  COMMANDS
# ============================
@require_auth
async def cmd_start(update, context):
    # Replace plain-text start reply with a button menu for quick actions
    keyboard = [
        [InlineKeyboardButton("Status", callback_data="menu_status"),
         InlineKeyboardButton("Start all", callback_data="menu_startall")],
        [InlineKeyboardButton("Stop all", callback_data="menu_stopall"),
         InlineKeyboardButton("Help", callback_data="menu_help")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Aventa Controller v8.4 siap. Pilih aksi:",
        reply_markup=markup
    )

@require_auth
async def cmd_help(update, context):
	# full help text reused for both /help and menu Help
	HELP_TEXT = (
		"Aventa Controller — Daftar Perintah dan Contoh\n\n"
		"/status\n"
		"  - Deskripsi: Cek status controller dan bot yang berjalan.\n"
		"  - Contoh: /status\n\n"
		"/startbot [idx]\n"
		"  - Deskripsi: Jalankan bot untuk konfigurasi index tertentu (default idx=0).\n"
		"  - Contoh: /startbot 1\n\n"
		"/startall\n"
		"  - Deskripsi: Jalankan semua konfigurasi yang saat ini OFF.\n"
		"  - Contoh: /startall\n\n"
		"/stopbot [idx]\n"
		"  - Deskripsi: Hentikan semua bot yang dikelola controller, atau hanya untuk index tertentu.\n"
		"  - Contoh: /stopbot   -> hentikan semua\n"
		"  - Contoh: /stopbot 0 -> hentikan bot untuk idx 0\n\n"
		"/get [key] [--idx=N]\n"
		"  - Deskripsi: Tampilkan seluruh konfigurasi atau nilai sebuah key dari konfigurasi index N.\n"
		"  - Contoh: /get                -> tampilkan semua konfigurasi\n"
		"  - Contoh: /get max_spread --idx=1\n\n"
		"/set key=value [key2=value2 ...] [--idx=N]\n"
		"  - Deskripsi: Ubah atau buat konfigurasi. Bila --idx tidak diberikan, index 0 digunakan.\n"
		"  - Contoh: /set lot_size=0.02 daily_target=3.0 --idx=1\n\n"
		"/menu\n"
		"  - Deskripsi: Tampilkan menu tombol (Status / Start all / Stop all / Help).\n"
		"  - Contoh: /menu\n\n"
		"Catatan:\n"
		"  - Untuk mengizinkan akses, set ALLOWED_CHAT_IDS di .env (koma-separated chat ids).\n"
		"  - Gunakan /set untuk menambah atau mengubah konfigurasi sebelum menjalankan bot.\n"
	)
	# If this was invoked as a regular /help command (message available), reply normally.
	if getattr(update, "message", None):
		await update.message.reply_text(HELP_TEXT)
	else:
		# fallback: try to send via effective_chat
		chat = getattr(update, "effective_chat", None)
		if chat:
			try:
				from telegram import Bot
				bot = Bot(BOT_TOKEN)
				await bot.send_message(chat_id=chat.id, text=HELP_TEXT)
			except Exception:
				# best-effort: log and ignore
				log("cmd_help: failed to send help via bot.send_message", "DEBUG")

@require_auth
async def cmd_status(update, context):
    log("cmd_status invoked", "DEBUG")
    # show all recorded bot PIDs and their resource usage
    pids = read_pids()
    running = bool(pids)
    if running:
        msg_lines = [f"Bots tercatat: ✅ {len(pids)} berjalan"]
        for pid in pids:
            try:
                p = psutil.Process(pid)
                msg_lines.append(f"PID {pid} | CPU: {p.cpu_percent(interval=0.1)}% | MEM: {p.memory_info().rss/1e6:.1f} MB")
                log(f"cmd_status: PID {pid} CPU {p.cpu_percent(interval=0.0)} MEM {p.memory_info().rss}", "DEBUG")
            except Exception as e:
                msg_lines.append(f"PID {pid} | (tidak dapat membaca statistik)")
                log(f"cmd_status: failed to read stats for pid {pid}: {e}", "DEBUG")
    else:
        msg_lines = ["Tidak ada bot tercatat berjalan. (Semua OFF)"]

    # show internet speed (non-blocking with timeout)
    try:
        net_info = measure_internet(timeout=15)
        msg_lines.append("\n" + net_info)
    except Exception as e:
        log(f"cmd_status: measure_internet exception: {e}\n{traceback.format_exc()}", "ERROR")
        msg_lines.append("\nSpeedtest: error")

    # Load configs and detect processes running the AVENTA_FILE
    cfg_list = load_config_list()
    # map idx -> list of pids that match that config
    idx_running = {i: [] for i in range(len(cfg_list))}
    unmatched_pids = []

    # Build expected arg sets for each config for matching
    expected_args_list = []
    for conf in cfg_list:
        expected = build_cmd_from_config(conf)[2:]  # skip "python" and script name
        expected_args_list.append(set(expected))

    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or proc.cmdline()
            if not cmdline:
                continue
            # check if this process is running the AVENTA script
            # match if any arg equals or endswith the AVENTA_FILE basename
            if not any((str(arg).endswith(AVENTA_FILE) or os.path.basename(str(arg)) == os.path.basename(AVENTA_FILE)) for arg in cmdline):
                continue
            proc_args_set = set(str(x) for x in cmdline[2:]) if len(cmdline) >= 3 else set(str(x) for x in cmdline[1:])
            matched = False
            for idx, expected_set in enumerate(expected_args_list):
                # if expected args are subset of actual process args, consider it a match
                if expected_set.issubset(proc_args_set):
                    idx_running[idx].append(proc.pid)
                    matched = True
                    break
            if not matched:
                unmatched_pids.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    # Compose status per config
    if cfg_list:
        msg_lines.append("\nConfig status per index:")
        for i, conf in enumerate(cfg_list):
            pids = idx_running.get(i) or []
            if pids:
                msg_lines.append(f"idx {i}: ✅ RUNNING (PID: {', '.join(str(x) for x in pids)})")
            else:
                msg_lines.append(f"idx {i}: ❌ OFF")
    else:
        msg_lines.append("Tidak ada konfigurasi (bot).")

    if unmatched_pids:
        msg_lines.append(f"\nProses Aventa yang tidak cocok dengan config: {', '.join(str(x) for x in unmatched_pids)}")
        log(f"cmd_status: unmatched pids {unmatched_pids}", "DEBUG")

    await update.message.reply_text("\n".join(msg_lines))

@require_auth
async def cmd_get(update, context):
    cfg_list = load_config_list()
    args = context.args
    if not args:
        await update.message.reply_text(json.dumps(cfg_list, indent=2))
        return
    key = args[0]
    idx = 0
    if len(args) > 1 and args[1].startswith("--idx"):
        try:
            idx = int(args[1].split("=")[1])
        except Exception:
            pass
    if 0 <= idx < len(cfg_list):
        await update.message.reply_text(str(cfg_list[idx].get(key, "(not set)")))
    else:
        await update.message.reply_text("Index out of range.")

@require_auth
async def cmd_set(update, context):
    # Syntax: /set key=value key2=value2 ... [--idx N]
    tokens = context.args
    if not tokens:
        await update.message.reply_text("Format: /set key=value [key2=value2 ...] [--idx N]")
        return

    idx = 0
    pairs = []
    for t in tokens:
        if t.startswith("--idx"):
            try:
                idx = int(t.split("=",1)[1])
            except Exception:
                pass
        elif "=" in t:
            k,v = t.split("=",1)
            pairs.append((k.strip(), v.strip()))
        else:
            await update.message.reply_text(f"Ignored token: {t}")

    cfg_list = load_config_list()
    while idx >= len(cfg_list):
        cfg_list.append({})

    for k,v in pairs:
        cfg_list[idx][k] = coerce_value(v)

    save_config_list(cfg_list)
    await update.message.reply_text(f"✅ Config idx {idx} updated.\n{json.dumps(cfg_list[idx], indent=2)}")

@require_auth
async def cmd_startbot(update, context):
     idx = 0
     if context.args:
         try:
             idx = int(context.args[0])
         except Exception:
             pass

     cfg_list = load_config_list()
     if not cfg_list:
         await update.message.reply_text("Config kosong. Set dahulu dengan /set ...")
         return
     if idx >= len(cfg_list):
         await update.message.reply_text("Index config di luar jangkauan.")
         return

     cmd = build_cmd_from_config(cfg_list[idx])
     try:
         #proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
         proc = subprocess.Popen(cmd)
         add_pid(proc.pid)
         await update.message.reply_text(f"✅ Bot dimulai dengan PID {proc.pid}\nCmd: {' '.join(shlex.quote(c) for c in cmd)}")
         log(f"[START] {' '.join(cmd)} (pid={proc.pid})", "INFO")
     except Exception as e:
         await update.message.reply_text(f"❌ Gagal start bot: {e}")
         log(f"[ERROR] start: {e}\n{traceback.format_exc()}", "ERROR")

@require_auth
async def cmd_stopbot(update, context):
    # Support: /stopbot            -> stop all (existing behavior)
    #          /stopbot <idx>      -> stop bots matching config index <idx>
    args = context.args
    # if an index was provided, attempt to stop only matching processes
    if args:
        try:
            idx = int(args[0])
            cfg_list = load_config_list()
            if not cfg_list:
                await update.message.reply_text("Config kosong. Tidak ada yang dihentikan.")
                return
            if idx < 0 or idx >= len(cfg_list):
                await update.message.reply_text("Index config di luar jangkauan.")
                return

            expected = set(build_cmd_from_config(cfg_list[idx])[2:])
            matched = []
            errors = []

            for proc in psutil.process_iter(["pid", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline") or proc.cmdline()
                    if not cmdline:
                        continue
                    # ensure this is an Aventa process
                    if not any((str(arg).endswith(AVENTA_FILE) or os.path.basename(str(arg)) == os.path.basename(AVENTA_FILE)) for arg in cmdline):
                        continue
                    proc_args_set = set(str(x) for x in cmdline[2:]) if len(cmdline) >= 3 else set(str(x) for x in cmdline[1:])
                    if expected.issubset(proc_args_set):
                        pid = proc.pid
                        log(f"cmd_stopbot(idx={idx}): attempting to stop pid {pid}", "INFO")
                        try:
                            proc.terminate()
                            try:
                                proc.wait(timeout=5)
                                log(f"cmd_stopbot(idx={idx}): pid {pid} terminated", "INFO")
                            except psutil.TimeoutExpired:
                                proc.kill()
                                log(f"cmd_stopbot(idx={idx}): pid {pid} killed after timeout", "INFO")
                        except Exception as e:
                            errors.append(f"{pid}:{e}")
                            log(f"cmd_stopbot(idx={idx}): error stopping pid {pid}: {e}\n{traceback.format_exc()}", "ERROR")
                        finally:
                            # best-effort remove from pid store
                            try:
                                remove_pid(pid)
                            except Exception:
                                pass
                        matched.append(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    log(f"cmd_stopbot(idx={idx}): process iteration error: {e}\n{traceback.format_exc()}", "ERROR")
                    continue

            if matched:
                msg = f"⛔ Dihentikan untuk idx {idx}: {', '.join(str(x) for x in matched)}"
                if errors:
                    msg += f"\nBeberapa error: {errors}"
                await update.message.reply_text(msg)
            else:
                if errors:
                    await update.message.reply_text(f"Gagal menghentikan beberapa PID: {errors}")
                else:
                    await update.message.reply_text(f"Tidak ada bot berjalan untuk idx {idx}.")
            return
        except ValueError:
            # not an integer: fall through to default stop-all behavior
            pass

    pids = read_pids()
    if not pids:
        await update.message.reply_text("Bot tidak berjalan.")
        log("cmd_stopbot: no pids to stop", "DEBUG")
        return
    errors = []
    for pid in list(pids):
        log(f"cmd_stopbot: attempting to stop pid {pid}", "INFO")
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=5)
                log(f"cmd_stopbot: pid {pid} terminated", "INFO")
            except psutil.TimeoutExpired:
                proc.kill()
                log(f"cmd_stopbot: pid {pid} killed after timeout", "INFO")
        except Exception as e:
            errors.append(f"{pid}:{e}")
            log(f"cmd_stopbot: error stopping pid {pid}: {e}\n{traceback.format_exc()}", "ERROR")
        finally:
            remove_pid(pid)

    if errors:
        await update.message.reply_text(f"Gagal menghentikan beberapa PID: {errors}")
        log(f"cmd_stopbot: errors {errors}", "ERROR")
    else:
        await update.message.reply_text("⛔ Semua bot dihentikan.")
        log("cmd_stopbot: all pids stopped", "INFO")

# New: start all configs that are not currently running
@require_auth
async def cmd_startall(update, context):
    log("cmd_startall invoked", "DEBUG")
    cfg_list = load_config_list()
    if not cfg_list:
        await update.message.reply_text("Config kosong. Set dahulu dengan /set ...")
        return

    # build expected arg sets per config
    expected_args_list = [set(build_cmd_from_config(conf)[2:]) for conf in cfg_list]

    # gather running Aventa processes and their arg-sets
    running_procs = []
    try:
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or proc.cmdline()
                if not cmdline:
                    continue
                if not any((str(arg).endswith(AVENTA_FILE) or os.path.basename(str(arg)) == os.path.basename(AVENTA_FILE)) for arg in cmdline):
                    continue
                proc_args_set = set(str(x) for x in cmdline[2:]) if len(cmdline) >= 3 else set(str(x) for x in cmdline[1:])
                running_procs.append((proc.pid, proc_args_set))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                log(f"cmd_startall: error reading process: {e}\n{traceback.format_exc()}", "ERROR")
    except Exception as e:
        log(f"cmd_startall: psutil iteration failed: {e}\n{traceback.format_exc()}", "ERROR")

    started = []
    skipped = []
    errors = []

    for idx, conf in enumerate(cfg_list):
        expected = expected_args_list[idx]
        already = any(expected.issubset(proc_args) for _, proc_args in running_procs)
        if already:
            skipped.append(idx)
            log(f"cmd_startall: idx {idx} skipped (already running)", "DEBUG")
            continue

        cmd = build_cmd_from_config(conf)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            add_pid(proc.pid)
            started.append((idx, proc.pid))
            log(f"cmd_startall: started idx {idx} pid {proc.pid}", "INFO")
        except Exception as e:
            errors.append((idx, str(e)))
            log(f"cmd_startall: failed to start idx {idx}: {e}\n{traceback.format_exc()}", "ERROR")

    # build reply
    parts = []
    if started:
        parts.append("Started:")
        for i, pid in started:
            parts.append(f"  idx {i} -> PID {pid}")
    if skipped:
        parts.append("Skipped (already running): " + ", ".join(str(i) for i in skipped))
    if errors:
        parts.append("Errors:")
        for i, err in errors:
            parts.append(f"  idx {i}: {err}")

    if not parts:
        parts = ["No actions performed."]

    await update.message.reply_text("\n".join(parts))

@require_auth
async def cmd_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("Status", callback_data="menu_status"),
         InlineKeyboardButton("Start all", callback_data="menu_startall")],
        [InlineKeyboardButton("Stop all", callback_data="menu_stopall"),
         InlineKeyboardButton("Help", callback_data="menu_help")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih aksi:", reply_markup=markup)

@require_auth
async def menu_callback(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data

    # Build a small synthetic update object with the attributes expected by command handlers.
    # Avoid setting attributes on the real Update instance (it's read-only).
    mini_update = SimpleNamespace(
        message = q.message,
        effective_chat = q.message.chat if q.message else getattr(update, "effective_chat", None),
        effective_user = q.from_user if getattr(q, "from_user", None) else getattr(update, "effective_user", None)
    )

    if data == "menu_status":
        await cmd_status(mini_update, context)
    elif data == "menu_startall":
        await cmd_startall(mini_update, context)
    elif data == "menu_stopall":
        await cmd_stopbot(mini_update, context)
    elif data == "menu_help":
        # show help by editing the original menu message (so help appears "in the menu")
        HELP_TEXT = (
			"Aventa Controller — Daftar Perintah dan Contoh\n\n"
			"/status\n"
			"  - Deskripsi: Cek status controller dan bot yang berjalan.\n"
			"  - Contoh: /status\n\n"
			"/startbot [idx]\n"
			"  - Deskripsi: Jalankan bot untuk konfigurasi index tertentu (default idx=0).\n"
			"  - Contoh: /startbot 1\n\n"
			"/startall\n"
			"  - Deskripsi: Jalankan semua konfigurasi yang saat ini OFF.\n"
			"  - Contoh: /startall\n\n"
			"/stopbot [idx]\n"
			"  - Deskripsi: Hentikan semua bot yang dikelola controller, atau hanya untuk index tertentu.\n"
			"  - Contoh: /stopbot   -> hentikan semua\n"
			"  - Contoh: /stopbot 0 -> hentikan bot untuk idx 0\n\n"
			"/get [key] [--idx=N]\n"
			"  - Deskripsi: Tampilkan seluruh konfigurasi atau nilai sebuah key dari konfigurasi index N.\n"
			"  - Contoh: /get                -> tampilkan semua konfigurasi\n"
			"  - Contoh: /get max_spread --idx=1\n\n"
			"/set key=value [key2=value2 ...] [--idx=N]\n"
			"  - Deskripsi: Ubah atau buat konfigurasi. Bila --idx tidak diberikan, index 0 digunakan.\n"
			"  - Contoh: /set lot_size=0.02 daily_target=3.0 --idx=1\n\n"
			"/menu\n"
			"  - Deskripsi: Tampilkan menu tombol (Status / Start all / Stop all / Help).\n"
			"  - Contoh: /menu\n\n"
			"Tekan 'Back' untuk kembali ke menu."
		)
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="menu_back")]])
        try:
            await q.edit_message_text(HELP_TEXT, reply_markup=back_kb)
        except Exception:
            # fallback: send as new message
            await mini_update.message.reply_text(HELP_TEXT)
    elif data == "menu_back":
        # restore original menu inline keyboard
        keyboard = [
            [InlineKeyboardButton("Status", callback_data="menu_status"),
             InlineKeyboardButton("Start all", callback_data="menu_startall")],
            [InlineKeyboardButton("Stop all", callback_data="menu_stopall"),
             InlineKeyboardButton("Help", callback_data="menu_help")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        try:
            await q.edit_message_text("Pilih aksi:", reply_markup=markup)
        except Exception:
            await mini_update.message.reply_text("Pilih aksi:", reply_markup=markup)
    else:
        await q.edit_message_text("Pilihan tidak dikenal.")

def measure_internet(timeout: int = 8) -> str:
    """Try to measure internet speed using speedtest module with a timeout.
    Returns a human-readable string or an unavailable message.
    """
    result = {}
    def _run(res):
        try:
            try:
                import speedtest  # pylint: disable=import-outside-toplevel
            except ImportError:
                res["ok"] = False
                res["err"] = "speedtest-cli not installed"
                return
            s = speedtest.Speedtest()
            s.get_best_server()
            # download/upload return bits per second
            down = s.download()
            up = s.upload()
            ping = s.results.ping if hasattr(s, "results") and s.results else None
            res["ok"] = True
            res["down"] = down
            res["up"] = up
            res["ping"] = ping
        except Exception as e:
            res["ok"] = False
            res["err"] = str(e)

    th = threading.Thread(target=_run, args=(result,))
    th.daemon = True
    th.start()
    th.join(timeout)
    if not result.get("ok"):
        log(f"measure_internet: failed or timed out ({result.get('err', 'no result')})", "DEBUG")
        return "Speedtest: unavailable (install 'speedtest-cli' or increase timeout)"
    try:
        down_mbps = result["down"] / 1e6
        up_mbps = result["up"] / 1e6
        ping = result.get("ping")
        ping_str = f"{ping:.1f} ms" if ping is not None else "n/a"
        return f"Speedtest: ping {ping_str} | down {down_mbps:.2f} Mbps | up {up_mbps:.2f} Mbps"
    except Exception as e:
        log(f"measure_internet: formatting error: {e}\n{traceback.format_exc()}", "ERROR")
        return "Speedtest: error formatting results"

# ============================
#  MAIN
# ============================
def main():
    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_TOKEN belum di-set di .env")
    # Import telegram.ext at runtime so we can show a clear error if the
    # python-telegram-bot package is missing or incompatible.
    try:
        from telegram.ext import ApplicationBuilder, CommandHandler
    except Exception as e:
        raise SystemExit("python-telegram-bot not installed or incompatible. Install 'python-telegram-bot' (v20+) and retry. Error: " + str(e))
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("get",      cmd_get))
    app.add_handler(CommandHandler("set",      cmd_set))
    app.add_handler(CommandHandler("startbot", cmd_startbot))
    app.add_handler(CommandHandler("startall", cmd_startall))
    app.add_handler(CommandHandler("stopbot",  cmd_stopbot))
    app.add_handler(CommandHandler("menu",     cmd_menu))
    app.add_handler(CallbackQueryHandler(menu_callback))

    log("Launcher Telegram Aventa_Hybrid_PPO_v9 Running...")
    # include callback_query so InlineKeyboardButton presses are delivered
    app.run_polling(allowed_updates=["message", "edited_message", "channel_post", "callback_query"])

if __name__ == "__main__":
    main()
