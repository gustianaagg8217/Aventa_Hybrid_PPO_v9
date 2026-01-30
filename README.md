# Aventa Hybrid PPO v9

**Hybrid Reinforcement Learning Trading Bot with Telegram Integration**

Ultra-efficient AI trading system using Proximal Policy Optimization (PPO) for automated forex and crypto trading on MetaTrader 5.

---

## 📋 **Daftar Isi**

1. [Panduan Cepat](#-panduan-cepat)
2. [Persyaratan Sistem](#-persyaratan-sistem)
3. [Instalasi & Setup](#-instalasi--setup)
4. [Konfigurasi](#-konfigurasi)
5. [Menjalankan Bot](#-menjalankan-bot)
6. [Fitur Utama](#-fitur-utama)
7. [Struktur File](#-struktur-file)
8. [Telegram Integration](#-telegram-integration)
9. [Trading Parameters](#-trading-parameters)
10. [Troubleshooting](#-troubleshooting)

---

## 🚀 **Panduan Cepat**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup environment
copy .env.example .env
# Edit .env dengan Telegram token dan chat IDs

# 3. Jalankan Launcher GUI
python Launcher_Aventa_Hybrid_PPO_v9.py
```

---

## 💻 **Persyaratan Sistem**

### **Minimum Requirements:**
- **OS**: Windows 10/11 (64-bit)
- **RAM**: 8GB minimum, 16GB recommended
- **CPU**: Intel i5/AMD Ryzen 5 or better
- **Storage**: 10GB free space
- **Python**: 3.8 - 3.11

### **Software Dependencies:**
- MetaTrader 5 Terminal (running)
- Python 3.8+
- Telegram Bot (optional, for notifications)

### **Network:**
- Stable internet connection (minimum 10 Mbps)
- Low latency connection to broker
- Access to Telegram API (if enabled)

---

## 🔧 **Instalasi & Setup**

### **1. Clone/Download Repository**

```bash
# Extract files ke folder yang diinginkan
cd Aventa_Hybrid_PPO_v9
```

### **2. Setup Virtual Environment (Recommended)**

```bash
# Buat virtual environment
python -m venv venv

# Aktivasi (Windows)
venv\Scripts\activate

# Atau (Linux/Mac)
source venv/bin/activate
```

### **3. Install Python Dependencies**

```bash
pip install -r requirements.txt
```

Jika terjadi masalah dengan stable-baselines3, install dependencies-nya:
```bash
pip install stable-baselines3[extra]
```

### **4. Setup MetaTrader 5**

1. **Install MetaTrader 5 Terminal** (jika belum)
2. **Login ke akun trading** Anda
3. **Enable AutoTrading** di MT5:
   - Tools → Options → Expert Advisors
   - ✅ Allow automated trading
   - ✅ Allow WebRequest

4. **Keep MT5 running** (bot memerlukan MT5 aktif)

### **5. Setup Telegram Bot (Optional)**

#### **5a. Buat Telegram Bot**
1. Buka Telegram, cari **@BotFather**
2. Kirim `/newbot`
3. Ikuti instruksi dan copy **Bot Token**

#### **5b. Dapatkan Chat ID**
1. Buka Telegram, cari **@userinfobot**
2. Kirim `/start` untuk mendapatkan Chat ID Anda

#### **5c. Setup Environment Variables**
Buat file `.env` di folder root:

```env
TELEGRAM_TOKEN=YOUR_BOT_TOKEN_HERE
ALLOWED_CHAT_IDS=YOUR_CHAT_ID_1,YOUR_CHAT_ID_2
AVENTA_FILE=Aventa_Hybrid_PPO_v9.py
DEBUG=false
```

---

## ⚙️ **Konfigurasi**

### **File Konfigurasi Utama: `bot_config.json`**

```json
{
  "mt5_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
  "symbol": "XAUUSD",
  "lot_size": 0.01,
  "close_profit": 0.15,
  "max_open_trades": 5,
  "ppo_model_path": "ppo_model_XAUUSD_best.zip",
  "type_filling": "IOC",
  "max_spread": 0.5,
  "start_trading_hour": 9,
  "end_trading_hour": 17,
  "daily_target": 2.0,
  "max_dd": 5.0,
  "reverse": false,
  "window_open_limit": 50,
  "window_on_seconds": 60,
  "window_pause_seconds": 10
}
```

### **Parameter Penjelasan:**

| Parameter | Type | Default | Deskripsi |
|-----------|------|---------|-----------|
| `mt5_path` | string | - | Path ke terminal MetaTrader 5 |
| `symbol` | string | XAUUSD | Simbol trading (XAUUSD, EURUSD, dll) |
| `lot_size` | float | 0.01 | Ukuran lot per trade |
| `close_profit` | float | 0.15 | Target profit per trade ($) |
| `max_open_trades` | int | 5 | Maximum posisi terbuka |
| `ppo_model_path` | string | - | Path ke file model PPO |
| `type_filling` | string | IOC | Tipe pengisian order (FOK/IOC/RET) |
| `max_spread` | float | 0.5 | Spread maksimal yang diizinkan |
| `start_trading_hour` | int | 9 | Jam mulai trading (0-23) |
| `end_trading_hour` | int | 17 | Jam selesai trading (0-23) |
| `daily_target` | float | 2.0 | Target profit harian (%) |
| `max_dd` | float | 5.0 | Max drawdown harian (%) |
| `reverse` | bool | false | Balikkan sinyal trading |
| `window_open_limit` | int | 50 | Max open trade per window |
| `window_on_seconds` | int | 60 | Durasi window aktif (detik) |
| `window_pause_seconds` | int | 10 | Durasi window pause (detik) |

---

## ▶️ **Menjalankan Bot**

### **Opsi 1: GUI Launcher (Recommended)**

```bash
python Launcher_Aventa_Hybrid_PPO_v9.py
```

**Fitur GUI:**
- ✅ Multiple bot configuration
- ✅ Real-time status monitoring
- ✅ Easy parameter adjustments
- ✅ One-click start/stop
- ✅ Integrated logging

### **Opsi 2: Telegram Controller**

```bash
python Launcher_Telegram_Aventa_Hybrid_PPO_v9.py
```

Kelola bot melalui Telegram commands:
- `/start` - Mulai bot
- `/stop` - Hentikan bot
- `/status` - Cek status
- `/config` - Lihat konfigurasi
- `/logs` - Lihat log terbaru

### **Opsi 3: Direct Python**

```bash
python Aventa_Hybrid_PPO_v9.py \
  --mt5_path "C:\\Program Files\\MetaTrader 5\\terminal64.exe" \
  --symbol XAUUSD \
  --lot_size 0.01 \
  --close_profit 0.15 \
  --max_open_trades 5 \
  --ppo_model_path "ppo_model_XAUUSD_best.zip" \
  --type_filling 2 \
  --max_spread 0.5
```

### **Batch File (Windows)**

Buat `run_bot.bat`:
```batch
@echo off
cd /d "%~dp0"
venv\Scripts\activate.bat
python Launcher_Aventa_Hybrid_PPO_v9.py
pause
```

---

## 🤖 **Fitur Utama**

### **1. Proximal Policy Optimization (PPO)**
- State-of-the-art reinforcement learning algorithm
- Optimal balance antara exploration dan exploitation
- Adaptive to market conditions

### **2. Hybrid Trading Strategy**
- Kombinasi rule-based dan AI-based signals
- Intelligent position sizing
- Adaptive risk management

### **3. Risk Management**
- Daily drawdown limits
- Position size limits
- Profit target per trade
- Stop loss protection
- Maximum open positions

### **4. Real-time Monitoring**
- Live P&L tracking
- Position monitoring
- Market condition assessment
- Performance analytics

### **5. Telegram Integration**
- Real-time trade notifications
- Performance updates
- Alert systems
- Remote control

### **6. Trading Windows**
- Active trading windows (ON state)
- Pause windows (OFF state)
- Configurable durations
- Automatic cycling

---

## 📁 **Struktur File**

```
Aventa_Hybrid_PPO_v9/
├── Aventa_Hybrid_PPO_v9.py          # Main trading bot
├── Launcher_Aventa_Hybrid_PPO_v9.py # GUI launcher
├── telegram_controller.py            # Telegram bot controller
├── bot_config.json                   # Main configuration
├── .env                              # Environment variables
├── requirements.txt                  # Python dependencies
├── log_transaksi.csv                 # Transaction log
├── controller.log                    # System log
├── ppo_model_XAUUSD_best.zip         # Trained PPO model
├── baseline_equity_*.json             # Account baseline tracking
└── Trainer/                          # (Optional) Model training scripts
```

---

## 📱 **Telegram Integration**

### **Setup Instructions**

1. **Create Bot with @BotFather**
   - Save your Bot Token

2. **Get Your Chat ID**
   - Use @userinfobot to get Chat ID

3. **Create `.env` file**
   ```env
   TELEGRAM_TOKEN=YOUR_TOKEN
   ALLOWED_CHAT_IDS=YOUR_CHAT_ID
   ```

4. **Test Connection**
   - Run launcher and test via GUI button
   - Or send command `/status` to your bot

### **Available Commands**

| Command | Function |
|---------|----------|
| `/start` | Start trading bot |
| `/stop` | Stop trading bot |
| `/status` | Get bot status |
| `/stats` | Get trading statistics |
| `/config` | Show current config |
| `/logs` | Last 10 log lines |
| `/help` | Show all commands |

### **Notification Types**

- **Trade Open**: Position opened with entry price
- **Trade Close**: Position closed with P&L
- **Alert**: Risk management events
- **Status**: Periodic performance updates

---

## 📊 **Trading Parameters Guide**

### **For Conservative Trading**
```json
{
  "lot_size": 0.01,
  "close_profit": 0.10,
  "max_open_trades": 3,
  "max_dd": 2.0,
  "daily_target": 1.0,
  "max_spread": 0.3
}
```

### **For Moderate Trading**
```json
{
  "lot_size": 0.05,
  "close_profit": 0.15,
  "max_open_trades": 5,
  "max_dd": 5.0,
  "daily_target": 2.0,
  "max_spread": 0.5
}
```

### **For Aggressive Trading**
```json
{
  "lot_size": 0.1,
  "close_profit": 0.20,
  "max_open_trades": 10,
  "max_dd": 10.0,
  "daily_target": 5.0,
  "max_spread": 1.0
}
```

---

## 🔍 **Monitoring & Logging**

### **Log Files**
- `controller.log` - System and bot logs
- `telegram_users.log` - Telegram command log
- `log_transaksi.csv` - Transaction history

### **View Logs**
```bash
# Real-time monitoring
tail -f controller.log

# Or in GUI launcher
# Logs tab shows live output
```

### **Transaction History**
```bash
# Open CSV file with Excel or text editor
log_transaksi.csv
```

---

## ⚠️ **Troubleshooting**

### **Issue 1: MetaTrader 5 Connection Failed**
```
ERROR: Cannot connect to MetaTrader 5
```
**Solution:**
- ✅ Pastikan MT5 terminal sudah berjalan
- ✅ Check terminal path di config
- ✅ Verify AutoTrading enabled
- ✅ Restart MT5 terminal

### **Issue 2: PPO Model Not Found**
```
ERROR: Cannot load model at ppo_model_XAUUSD_best.zip
```
**Solution:**
- ✅ Pastikan file model ada di folder
- ✅ Check path di bot_config.json
- ✅ Verify file extension (.zip)

### **Issue 3: Telegram Not Working**
```
ERROR: Telegram signal error: no running event loop
```
**Solution:**
- ✅ Verify TELEGRAM_TOKEN di .env
- ✅ Check ALLOWED_CHAT_IDS valid
- ✅ Test connection via GUI button
- ✅ Check internet connection

### **Issue 4: High CPU/Memory Usage**
```
WARNING: High system resource usage
```
**Solution:**
- ✅ Reduce `max_open_trades`
- ✅ Increase `window_pause_seconds`
- ✅ Close unnecessary applications
- ✅ Check for memory leaks in logs

### **Issue 5: Model Performance Issues**
```
WARNING: Model predictions unreliable
```
**Solution:**
- ✅ Retrain PPO model with recent data
- ✅ Adjust trading hours
- ✅ Increase training samples
- ✅ Check market volatility

---

## 🔐 **Security Best Practices**

### **Configuration Security**
- ✅ Never commit `.env` to git
- ✅ Use strong Telegram bot token
- ✅ Restrict chat IDs to authorized users
- ✅ Keep credentials in .env file only

### **Trading Security**
- ✅ Test on demo account first
- ✅ Start with minimum lot size
- ✅ Monitor daily drawdown limits
- ✅ Keep emergency stop procedures

### **System Security**
- ✅ Run on secure network
- ✅ Keep Python updated
- ✅ Use firewall protection
- ✅ Regular backups of config

---

## 📈 **Performance Tips**

### **For Better Results:**
1. **Train PPO Model Regularly**
   - Use recent market data
   - Retrain every 2-4 weeks
   - Test on demo first

2. **Optimize Parameters**
   - Adjust for your broker
   - Test different symbols
   - Fine-tune risk parameters

3. **Monitor Performance**
   - Check logs daily
   - Analyze win rate
   - Track drawdown
   - Review P&L trends

4. **System Optimization**
   - Use stable internet
   - Keep MT5 updated
   - Monitor system resources
   - Regular maintenance

---

## 🔄 **Update & Maintenance**

### **Regular Tasks**
- **Daily**: Monitor logs and P&L
- **Weekly**: Review transaction history
- **Monthly**: Analyze performance metrics
- **Quarterly**: Retrain PPO model

### **Backup**
```bash
# Backup config and logs
xcopy bot_config.json backup\ /Y
xcopy *.log backup\ /Y
xcopy *.csv backup\ /Y
```

---

## 📞 **Support & Resources**

### **Documentation**
- `Aventa_HFT_Pro_2026_User_Manual_ID-EN.pdf`
- Inline code comments
- GitHub issues

### **Troubleshooting**
- Check `controller.log` for errors
- Review `telegram_users.log` for command issues
- Analyze `log_transaksi.csv` for trading issues

### **Community**
- GitHub Issues for bug reports
- Telegram channel for updates
- Discord for discussions

---

## ⚠️ **Disclaimer**

**Trading involves substantial risk of loss. This software is provided for educational purposes only.**

**IMPORTANT:**
- ✅ Test extensively on demo account first
- ✅ Start with very small lot sizes
- ✅ Understand all risks involved
- ✅ Have emergency stop procedures
- ✅ Monitor trading activity regularly
- ✅ Keep sufficient capital in account

**Past performance does not guarantee future results.**

---

## 📝 **Changelog**

### **Version 9.0**
- ✅ Hybrid PPO reinforcement learning
- ✅ Multi-bot support
- ✅ Telegram integration
- ✅ Advanced risk management
- ✅ Real-time monitoring

---

**Happy Trading! 🤖📈**

*Last Updated: January 31, 2026*  
*Developed by: Aventa AI Team*
