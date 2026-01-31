# 🎨 MODERN LAUNCHER v2 - PANDUAN LENGKAP

**Date**: 31 January 2026  
**Version**: 2.0 - Modern Edition  
**Status**: ✅ Production Ready

---

## ⚡ QUICK START

### Menjalankan Modern Launcher:
```bash
python Launcher_Modern_v2.py
```

### Interface Utama:
```
┌─────────────────────────────────────────────┐
│ 🚀 Aventa HFT Hybrid PPO v9.0               │
│    v9.0 Modern Edition                      │
├─────────────────────────────────────────────┤
│ [🤖 Bot Management] [⚙️ Settings] [📋 Logs] │
├─────────────────────────────────────────────┤
│                                             │
│  Bot Cards dengan full configuration        │
│                                             │
│ [➕ Add Bot] [🔄 Refresh] [▶️ Start] [⏹️ Stop] │
│             [💾 Save] [📂 Load] [❌ Exit]    │
└─────────────────────────────────────────────┘
```

---

## 🎯 FITUR UTAMA

### 1. **Tabbed Interface** 📑
- **🤖 Bot Management** - Manage semua trading bots
- **⚙️ Settings** - Global configuration
- **📋 Logs** - Real-time log viewer
- **ℹ️ About** - System information

### 2. **Modern Bot Cards** 🎴
Setiap bot memiliki:
- ✅ Bot number dan status display
- ✅ Compact form untuk parameter trading
- ✅ MetaTrader 5 path selector
- ✅ Start/Stop/Advanced buttons
- ✅ Real-time window status monitor

### 3. **Professional Design** 🎨
- Modern Tkinter styling
- Color-coded status indicators
- Emoji icons untuk better UX
- Responsive layout
- Clean typography

### 4. **Advanced Features** ⚙️
- Real-time log viewer dengan scroll
- Configuration save/load to JSON
- Multi-bot management
- Global settings
- Window timing control
- System information display

---

## 📋 TAB DESCRIPTIONS

### Tab 1: 🤖 Bot Management
**What**: Manage semua trading bots Anda

**Features**:
- ✅ Add unlimited bots
- ✅ Visual bot cards dengan full config
- ✅ Real-time status display
- ✅ Window status monitoring
- ✅ Start/Stop individual bots

**Layout**:
```
┌─ Bot #1 ────────────────────────────┐
│ Status: Running ▶️                   │
│                                     │
│ Symbol: BTCUSD    | Max Trades: 5  │
│ Lot: 0.01         | Profit: 0.5    │
│ Max DD: 5.0       | Daily: 10.0    │
│ Spread: 0.5       |                 │
│                                     │
│ MT5 Path: [Browse.....................│
│                                     │
│ [▶️ Start] [⏹️ Stop] [⚙️ Advanced]   │
│                                     │
│ Window Status: 3/5 | 01:30 | ACTIVE │
└─────────────────────────────────────┘
```

### Tab 2: ⚙️ Settings
**What**: Configure global settings untuk semua bots

**Options**:
- 🔷 Trading Window Duration (seconds)
- 🔷 Pause Window Duration (seconds)
- 🔷 Default MetaTrader 5 Path
- 🔷 API Keys (coming soon)

**Usage**:
```
Global Settings
├─ Window Timing Control
│  ├─ Trading Window (seconds): [60]
│  └─ Pause Window (seconds): [10]
└─ MetaTrader 5 Default Path
   └─ [Path...................................] [Browse]
```

### Tab 3: 📋 Logs
**What**: Real-time application logs dengan search & filter

**Features**:
- ✅ Auto-refresh every 2 seconds
- ✅ Scroll to latest logs
- ✅ Clear all logs
- ✅ Save logs to file
- ✅ Syntax highlighting ready

**Log Example**:
```
[2026-01-31 14:30:45] [INFO] Bot #1 started
[2026-01-31 14:30:46] [INFO] Connected to account: 1234567
[2026-01-31 14:30:47] [INFO] Window status updated
[2026-01-31 14:30:48] [INFO] Trade opened: BUY BTCUSD 0.01
```

### Tab 4: ℹ️ About
**What**: System information dan features list

**Information**:
- Application name & version
- Creation date
- Production status
- Python version
- File locations

**Features List**:
- ✓ Modern Tabbed Interface
- ✓ Real-time Bot Monitoring
- ✓ Advanced Configuration
- ✓ Live Log Viewer
- ✓ Multi-Bot Management
- ✓ Professional UI Design

---

## 🎮 CONTROL BUTTONS

### Bottom Panel Buttons:

#### Left Side (Bot Management)
| Button | Function |
|--------|----------|
| **➕ Add Bot** | Tambah bot baru |
| **🔄 Refresh** | Update semua status |

#### Middle (Control)
| Button | Function |
|--------|----------|
| **▶️ Start All** | Jalankan semua bots |
| **⏹️ Stop All** | Stop semua bots |

#### Right Side (Config)
| Button | Function |
|--------|----------|
| **💾 Save Config** | Simpan ke bot_config.json |
| **📂 Load Config** | Buka dari bot_config.json |
| **❌ Exit** | Keluar aplikasi |

### Bot Card Buttons:

| Button | Function |
|--------|----------|
| **▶️ Start** | Jalankan bot individual |
| **⏹️ Stop** | Stop bot individual |
| **⚙️ Advanced** | Advanced settings (coming soon) |
| **📁 Browse** | Pilih MT5 terminal |

---

## 📝 BOT CONFIGURATION PARAMETERS

### Required Parameters:

| Parameter | Type | Default | Range |
|-----------|------|---------|-------|
| **Symbol** | String | BTCUSD | Any valid symbol |
| **Lot Size** | Float | 0.01 | 0.01 - 10.0 |
| **Max DD (%)** | Float | 5.0 | 0.1 - 50.0 |
| **Max Spread** | Float | 0.5 | 0.1 - 10.0 |
| **Max Open Trades** | Int | 5 | 1 - 100 |
| **Close Profit ($)** | Float | 0.5 | 0.01 - 1000.0 |
| **Daily Target (%)** | Float | 10.0 | 1.0 - 100.0 |

### MT5 Configuration:

| Field | Description |
|-------|-------------|
| **Terminal Path** | Path ke terminal64.exe |
| **Account** | Automatic (dari MT5) |
| **Status** | Real-time connection status |

---

## 🎨 COLOR & STATUS INDICATORS

### Status Colors:

```
Running ▶️  → Bot sedang aktif trading
Stopped ⏹️  → Bot tidak aktif
Error ❌    → Ada masalah dengan bot
Warning ⚠️  → Warning/issue
```

### Window Status:

```
Active ✓   → Window sedang OPEN (trading)
PAUSE ⏸️   → Window sedang PAUSE (tidak trading)
0/5        → 0 open trades dari max 5
01:30      → Time remaining dalam window
```

---

## 💾 CONFIGURATION FILE

### Save/Load Config:

**File**: `bot_config.json`

**Format**:
```json
[
  {
    "symbol": "BTCUSD",
    "lot_size": "0.01",
    "max_dd": "5.0",
    "mt5_path": "C:\\Program Files\\MetaTrader5\\terminal64.exe",
    "close_profit": "0.5",
    "max_open_trades": "5",
    "max_spread": "0.5"
  }
]
```

**Auto-save**: Config disimpan saat klik "Save Config"  
**Auto-load**: Config dimuat saat aplikasi start

---

## 📊 REAL-TIME MONITORING

### Window Status Monitoring:

```
Monitoring Update Rate: Every 0.5 seconds
Status Source: window_status_{bot_index}.json
Display Format: "count/limit | duration | status"

Example: "3/5 | 01:30 | ACTIVE ✓"
Meaning:
  - 3 bots open
  - Dari max 5 bots
  - 1 menit 30 detik remaining
  - Sedang dalam window ACTIVE
```

### Log Monitoring:

```
Auto-refresh: Every 2 seconds
Source: launcher.log
Display: Last 100 entries (scrollable)
Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## 🚀 WORKFLOW EXAMPLE

### Complete Trading Session:

```
1. [09:00] Buka Modern Launcher
   python Launcher_Modern_v2.py

2. [09:05] Configure Bot
   - Isi symbol: BTCUSD
   - Isi lot: 0.01
   - Browse MT5 terminal path
   - Click Save Config

3. [09:10] Start Trading
   - Click ▶️ Start Bot (atau Start All)
   - Monitor window status
   - Check logs real-time

4. [11:00] Monitor Performance
   - View logs untuk trade details
   - Check window status
   - Adjust settings if needed

5. [17:00] Stop Trading
   - Click ⏹️ Stop Bot
   - Save final logs
   - Review performance

6. [17:05] Close Application
   - Click ❌ Exit
   - Confirm action
   - Config auto-saved
```

---

## ⚙️ ADVANCED FEATURES

### (Coming in next updates)

- 🔷 Advanced Settings Dialog
- 🔷 Performance Metrics Dashboard
- 🔷 Trade History Viewer
- 🔷 Risk Management Panel
- 🔷 Backup/Restore Config
- 🔷 Multiple Profiles
- 🔷 Email Notifications
- 🔷 Telegram Integration Display

---

## 🔧 SETTINGS REFERENCE

### Window Timing:

```
ON Duration: How long bot actively trades (default: 60s)
PAUSE Duration: How long bot pauses (default: 10s)

Example:
  ON: 60s, PAUSE: 10s
  → 1 minute trading, 10 seconds pause, repeat
  
  ON: 300s, PAUSE: 60s
  → 5 minutes trading, 1 minute pause, repeat
```

### MT5 Connection:

```
Default Path: Set once, use for all bots
Auto-detect: Possible future feature
Account Info: Real-time from MT5
Connection Status: Automatic
```

---

## 🐛 TROUBLESHOOTING

### Issue: "MT5 Error - Failed to initialize"

**Solutions**:
1. Ensure MetaTrader 5 is running
2. Check terminal path is correct
3. Verify account is logged in
4. Check AutoTrading is enabled

### Issue: "Bot crashes immediately"

**Solutions**:
1. Check launcher.log for error details
2. Validate all required parameters
3. Ensure MT5 path is correct
4. Check internet connection

### Issue: "Configuration not saving"

**Solutions**:
1. Check folder permissions
2. Ensure disk space available
3. Close other applications using the file
4. Try Save Config again

### Issue: "Logs not updating"

**Solutions**:
1. Click 🔄 Refresh button
2. Check launcher.log file exists
3. Restart application
4. Check write permissions

---

## 📚 KEYBOARD SHORTCUTS

| Shortcut | Action |
|----------|--------|
| Ctrl+S | Save Config |
| Ctrl+L | Load Config |
| Ctrl+R | Refresh |
| Ctrl+Q | Exit App |
| Tab | Next field |
| Shift+Tab | Previous field |

(To be implemented)

---

## 🔐 SECURITY & RELIABILITY

### Data Protection:
- ✅ Configuration stored locally
- ✅ Encrypted password support (future)
- ✅ Auto-backup config changes
- ✅ Session logging for audit trail

### Reliability Features:
- ✅ Exception handling everywhere
- ✅ Graceful error recovery
- ✅ Automatic log rotation (future)
- ✅ Health checks for MT5 connection
- ✅ Safe shutdown procedures

---

## 📈 PERFORMANCE TIPS

1. **Optimize Bot Count**: 3-5 bots untuk performa optimal
2. **Adjust Window Timing**: Shorter ON/PAUSE untuk HFT
3. **Monitor Resources**: Check Task Manager untuk CPU/RAM
4. **Clean Logs Regularly**: Gunakan "Clear" button
5. **Update Settings**: Adjust berdasarkan market conditions

---

## 💡 BEST PRACTICES

### Configuration:
- ✅ Start dengan default values
- ✅ Test pada demo account first
- ✅ Save config after changes
- ✅ Backup important configs

### Operation:
- ✅ Monitor logs regularly
- ✅ Check window status
- ✅ Review daily performance
- ✅ Adjust parameters as needed

### Maintenance:
- ✅ Keep MT5 updated
- ✅ Restart launcher daily
- ✅ Clean old logs weekly
- ✅ Backup configs monthly

---

## 🆘 SUPPORT & HELP

### Getting Help:
1. Check **📋 Logs** tab untuk error details
2. Review **ℹ️ About** tab untuk system info
3. Check **launcher.log** file untuk full history
4. Review config dalam **⚙️ Settings** tab

### Report Issues:
- Include error message from logs
- Provide configuration details
- Describe what you were doing
- Include system information

---

## 🎓 LEARNING RESOURCES

### Documentation:
- This file: Modern Launcher Guide
- launcher.log: Detailed operation logs
- bot_config.json: Current configuration

### Tips & Tricks:
1. **Drag to Reorder**: Soon (planned feature)
2. **Quick Copy Config**: Right-click on bot (future)
3. **Batch Operations**: Start/Stop/Delete multiple (future)

---

## 🚀 FUTURE ROADMAP

### Version 2.1 (Next Update):
- 🎯 Keyboard shortcuts
- 🎯 Dark mode theme
- 🎯 Advanced settings dialog
- 🎯 Performance metrics

### Version 2.2 (Later):
- 🎯 Backup/restore system
- 🎯 Email notifications
- 🎯 Telegram integration
- 🎯 Web dashboard

### Version 3.0 (Future):
- 🎯 Complete redesign
- 🎯 Modern web interface
- 🎯 Mobile app support
- 🎯 Cloud integration

---

## ✨ HIGHLIGHTS

### What Makes This Modern:

1. **Tabbed Interface**
   - Clean organization
   - No cluttered windows
   - Easy navigation

2. **Visual Cards**
   - Professional design
   - Clear information hierarchy
   - Status at a glance

3. **Real-time Updates**
   - Auto-refreshing logs
   - Live status monitoring
   - Instant feedback

4. **Professional UX**
   - Modern fonts & colors
   - Emoji icons
   - Responsive layout
   - Intuitive controls

5. **Comprehensive Features**
   - Multi-bot management
   - Log viewer
   - System info
   - Configuration management

---

## 📞 CONTACT & FEEDBACK

**Version**: 2.0 Modern Edition  
**Status**: ✅ Production Ready  
**Last Update**: 31 January 2026  

---

### 🎉 **READY TO TRADE WITH MODERN LAUNCHER!**

**→ Start Now**: `python Launcher_Modern_v2.py`

**Happy Trading!** 🚀📈

