# 📖 QUICK START GUIDE - Aventa HFT Hybrid PPO v9.0 Launcher

**Last Updated**: 31 January 2026  
**Version**: 9.0 (Improved)

---

## ⚡ QUICK START (5 Minutes)

### 1️⃣ Run the Launcher
```bash
python Launcher_Aventa_Hybrid_PPO_v9.py
```

### 2️⃣ Configure Your First Bot
| Field | Example | Notes |
|-------|---------|-------|
| **Symbol** | BTCUSD | Trading pair |
| **Lot** | 0.01 | Position size |
| **Max DD** | 5.0 | Max drawdown % |
| **Terminal Path** | C:\Program Files\MetaTrader5\terminal64.exe | Click Browse |
| **Filling** | FOK | Order type |
| **Max Spread** | 0.5 | Max allowed spread |
| **Max OP** | 5 | Max open positions |
| **Close $** | 0.5 | Target profit per trade |
| **PPO Path** | (Optional) | Click Browse if using PPO model |
| **SH** | 9 | Start hour (0-23) |
| **EH** | 17 | End hour (0-23) |
| **Daily Target** | 10.0 | Daily profit target % |

### 3️⃣ Start Bot
1. Click **"Start"** button
2. System validates configuration
3. Bot starts automatically
4. Watch **"Status"** change to **"Running"** (green)

### 4️⃣ Monitor
- **WinStat**: Shows current window timing (e.g., "3/5 | 01:30 ON")
- **Status**: Color indicator (Green=Running, Red=Stopped, Orange=Error)
- Check **launcher_logs.txt** for detailed logs

### 5️⃣ Stop Bot
1. Click **"Stop"** button
2. Bot terminates gracefully
3. Status returns to "Stopped" (red)

---

## 🎨 COLOR CODING GUIDE

### Status Colors
| Color | Meaning |
|-------|---------|
| 🟢 **Green** | Bot is running normally |
| 🔴 **Red** | Bot is stopped |
| 🟠 **Orange** | Error or warning state |
| ⚪ **Gray** | Disabled/inactive |

### Window Status Colors
| Color | Meaning |
|-------|---------|
| 🟢 **Light Green** | Window is ON (trading active) |
| 🟡 **Orange** | Window is in PAUSE |
| 🔴 **Red** | Error reading status |

---

## 📋 CONFIGURATION MANAGEMENT

### Save Configuration
```
1. Configure all bots
2. Click "💾 Save Config" button
3. Configuration saved to bot_config.json
```

### Load Configuration
```
1. Click "📂 Load Config" button
2. Previous configuration automatically loaded
3. Make adjustments if needed
4. Click "Start" to begin trading
```

### Configuration File Format
```json
[
  {
    "symbol": "BTCUSD",
    "lot": "0.01",
    "max_dd": "5.0",
    "path": "C:\\Program Files\\MetaTrader5\\terminal64.exe",
    "type_filling": "FOK",
    "max_spread": "0.5",
    "max_open_trades": "5",
    "close_profit": "0.5",
    "ppo_model_path": "",
    "start_trading_hour": "9",
    "end_trading_hour": "17",
    "daily_target": "10.0",
    "reverse": false,
    "window_open_limit": "50"
  }
]
```

---

## 🤖 MANAGING MULTIPLE BOTS

### Add New Bot
```
1. Click "➕ Add Bot" button
2. New row appears at bottom
3. Configure parameters
4. Click "Start" to run
```

### Remove Bot
```
1. Stop the bot first (click "Stop" button)
2. Click "➖ Remove Bot" button
3. Last bot row is removed
4. Window automatically resizes
```

### Start All Bots
```
1. Configure all bot rows
2. Click "▶️ Start All" button
3. All bots start with slight delay between them
4. Monitor each bot's status
```

### Stop All Bots
```
1. Click "⏹️ Stop All" button
2. All running bots are stopped
3. Proper cleanup happens automatically
```

---

## ⏱️ WINDOW TIMING CONTROL

### What is Window Timing?
- **ON Period**: Bot actively trades
- **PAUSE Period**: Bot pauses trading
- Helps manage risk and overexposure

### Adjust Timing
```
At bottom of window:

ON (s): [60]        <- Time to trade (seconds)
PAUSE (s): [10]     <- Time to pause (seconds)
```

### Examples
| ON | PAUSE | Description |
|----|----- -|-------------|
| 60 | 10 | Trade 1 min, pause 10 sec |
| 300 | 60 | Trade 5 min, pause 1 min |
| 120 | 30 | Trade 2 min, pause 30 sec |

---

## 🔔 BUTTON REFERENCE

| Button | Color | Action | Shortcut |
|--------|-------|--------|----------|
| **Start** | 🟢 Green | Start single bot | Click on row |
| **Stop** | 🔴 Red | Stop single bot | Click on row |
| **Browse** | 🟢 Green | Select terminal | MT5 path |
| **PPO** | 🔵 Blue | Select model | PPO model file |
| ➕ **Add Bot** | 🟢 Green | Add new bot | - |
| ➖ **Remove Bot** | 🔴 Red | Remove last bot | - |
| 💾 **Save Config** | 🔵 Blue | Save settings | Ctrl+S |
| 📂 **Load Config** | 🔵 Blue | Load settings | Ctrl+L |
| ▶️ **Start All** | 🟢 Green | Start all bots | - |
| ⏹️ **Stop All** | 🟠 Orange | Stop all bots | - |

---

## 📊 MONITORING & LOGGING

### Check Logs
```
File: launcher_logs.txt
Location: Same folder as launcher

Example log entry:
[2026-01-31 14:30:45,123] [INFO] Starting bot with command: python Aventa_Hybrid_PPO_v9.py ...
[2026-01-31 14:30:46,456] [INFO] Connected to account: 1234567 (John Doe)
[2026-01-31 14:30:47,789] [INFO] Bot started successfully for account 1234567
```

### Log Levels
- 🔵 **DEBUG**: Detailed debugging information
- 🟢 **INFO**: General information about operations
- 🟡 **WARNING**: Warning messages (non-critical issues)
- 🔴 **ERROR**: Error messages (operations failed)
- 🔴 **CRITICAL**: Critical errors (system failure)

---

## ⚠️ ERROR HANDLING

### Common Errors & Solutions

#### ❌ "MT5 Terminal path wajib diisi"
**Solution**: Click "Browse" and select MetaTrader 5 terminal (terminal64.exe)

#### ❌ "Terminal path tidak ditemukan"
**Solution**: Verify path exists. Browse button helps select correct path.

#### ❌ "Failed to initialize MetaTrader 5"
**Solution**: 
1. Ensure MetaTrader 5 is running
2. Check terminal.exe path is correct
3. Ensure account is logged in
4. Enable AutoTrading in MT5

#### ❌ "Lot size harus antara 0.01 dan 10"
**Solution**: Enter lot between 0.01 and 10.0

#### ❌ "Max open trades harus antara 1 dan 100"
**Solution**: Enter number between 1 and 100

#### ✅ All errors show clear messages in dialog box

---

## 🎯 BEST PRACTICES

### Before Starting
- ✅ Test on demo account first
- ✅ Verify all parameters are correct
- ✅ Check MetaTrader 5 is running
- ✅ Ensure AutoTrading is enabled
- ✅ Save configuration for future use

### While Running
- ✅ Monitor logs regularly (launcher_logs.txt)
- ✅ Watch status indicators
- ✅ Check window timing periodically
- ✅ Verify bot is opening trades
- ✅ Keep system running with stable internet

### Best Trading Hours
- 🟢 **9:00 - 17:00**: Optimal trading hours
- 🟡 **17:00 - 22:00**: Good trading hours
- 🔴 **22:00 - 9:00**: Low volatility (optional)

---

## 🔄 WORKFLOW EXAMPLE

### Complete Trading Session

```
1. [14:00] Open launcher
   - Application starts
   - Loads previous configuration

2. [14:05] Review Configuration
   - Check symbol (BTCUSD)
   - Verify lot size (0.01)
   - Check max positions (5)

3. [14:10] Start Bot
   - Click "Start" button
   - System validates inputs
   - MT5 connects successfully
   - Bot status: RUNNING (green)

4. [14:15-17:00] Monitor
   - Watch window timing: "3/5 | 02:15 ON"
   - Check for trades in logs
   - Monitor status periodically

5. [17:00] Check Performance
   - Review today's trades
   - Check profit/loss
   - Save configuration

6. [17:05] Stop Bot
   - Click "Stop" button
   - Bot stops gracefully
   - Status: STOPPED (red)

7. [17:10] Close Application
   - All threads cleaned up
   - No zombie processes
   - Ready for next session
```

---

## 📞 TROUBLESHOOTING

### Problem: GUI is slow
**Solution**:
- Close unnecessary applications
- Check system resources
- Reduce number of bots

### Problem: Bot crashes immediately
**Solution**:
1. Check launcher_logs.txt for error
2. Verify all parameters are valid
3. Ensure MetaTrader 5 is responsive
4. Restart MetaTrader 5

### Problem: Configuration won't load
**Solution**:
1. Check bot_config.json exists
2. Verify JSON format is valid
3. Try creating new configuration

### Problem: Bot stops after 48 hours
**Solution**:
- This is by design (auto-stop after 48 hours)
- Click "Start" again to continue
- Configure daily targets appropriately

---

## 🎓 TERMINOLOGY

| Term | Meaning |
|------|---------|
| **Symbol** | Trading pair (e.g., BTCUSD) |
| **Lot** | Position size (0.01 = 1000 units) |
| **DD** | Drawdown (max loss percentage) |
| **FOK** | Fill or Kill order |
| **IOC** | Immediate or Cancel order |
| **RET** | Return order |
| **PPO** | Proximal Policy Optimization (AI model) |
| **Window** | Trading active period |

---

## 💾 FILE LOCATIONS

| File | Purpose |
|------|---------|
| `Launcher_Aventa_Hybrid_PPO_v9.py` | Launcher application |
| `Aventa_Hybrid_PPO_v9.py` | Trading bot engine |
| `bot_config.json` | Configuration storage |
| `launcher_logs.txt` | Application logs |
| `window_status_*.json` | Window timing status |

---

## 🚀 ADVANCED FEATURES

### PPO Model Integration
1. Click "PPO" button in bot row
2. Select trained PPO model (.zip file)
3. Bot will use AI predictions for trades

### Multiple Accounts
1. Create multiple bot rows
2. Each row can use different MT5 account
3. Click "Start All" to run all simultaneously

### Daily Targets
1. Set "Daily Target" percentage
2. Bot will close all positions when target reached
3. Useful for profit taking

### Reverse Trading
1. Check "Reverse" checkbox
2. Signals are inverted (BUY → SELL, SELL → BUY)
3. Useful for testing opposite direction

---

## 📧 SUPPORT

**For issues or questions**:
1. Check log files: `launcher_logs.txt`
2. Review configuration: `bot_config.json`
3. Verify MetaTrader 5 is running
4. Restart launcher and try again

---

**Happy Trading! 🎯📈**

