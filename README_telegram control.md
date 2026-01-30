
# Aventa Telegram Controller v9.0

Kendali jarak jauh untuk **Aventa_Hybrid_PPO_v9.py** melalui Telegram.

## Fitur
- Start / Stop bot trading
- Lihat status bot (RUNNING/STOPPED)
- Ubah konfigurasi `bot_config.json` via Telegram (`/set`)
- Ambil konfigurasi saat ini (`/get`)
- Pembatasan akses via `ALLOWED_CHAT_IDS`

## Persiapan
1. **Pastikan file ini berada di folder yang sama** dengan `Aventa_Hybrid_PPO_v9.py` dan `Launcher_Aventa_Hybrid_PPO_v9.py`.
2. Buat bot Telegram via **BotFather** dan salin **TOKEN**.
3. Salin `.env.example` menjadi `.env`, lalu isi:
   ```ini
   TELEGRAM_TOKEN=123456:ABCDEF-your-token
   ALLOWED_CHAT_IDS=123456789   # optional, bisa lebih dari satu dipisahkan koma
   AVENTA_FILE=Aventa_Hybrid_PPO_v9.py
   ```
4. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```

## Menjalankan
```bash
python telegram_controller.py
```

Jika sukses, buka Telegram dan kirim `/start` ke bot Anda.

## Perintah Telegram
- `/start` atau `/help` – bantuan
- `/status` – cek status bot
- `/startbot [idx]` – mulai bot dengan config index (default 0)
- `/stopbot` – hentikan bot
- `/get [key] [--idx=N]` – tampilkan seluruh config atau 1 kunci pada index N
- `/set key=value [key2=value2 ...] [--idx=N]` – ubah config pada index N

### Contoh
```
/set max_open_trades=5 close_profit=2.5 --idx=0
/set reverse=true
/get
/get daily_target --idx=0
/startbot
/stopbot
```

## Catatan Integrasi
- File `bot_config.json` ini **sama** dengan yang dipakai oleh **Launcher_Aventa_Hybrid_PPO_v9.py**. Anda tetap bisa memakai GUI launcher seperti biasa. 
- Controller ini **langsung mengeksekusi** `Aventa_Hybrid_PPO_v9.py` memakai parameter sesuai config.
- Nilai `type_filling` boleh `FOK/IOC/RET` (akan diubah ke 1/2/3 saat eksekusi).

## Menjalankan sebagai Layanan (systemd – Linux)
Buat file `/etc/systemd/system/aventa-telegram.service`:
```
[Unit]
Description=Aventa Telegram Controller
After=network.target

[Service]
WorkingDirectory=/path/ke/folder/Aventa_Telegram_Control_v9
ExecStart=/usr/bin/python3 telegram_controller.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Lalu:
```
sudo systemctl daemon-reload
sudo systemctl enable aventa-telegram
sudo systemctl start aventa-telegram
sudo systemctl status aventa-telegram
```

## Windows (Task Scheduler)
- Buat basic task → Start a program: `python` dengan argumen `telegram_controller.py`
- Set trigger "At startup" atau "On logon" sesuai kebutuhan.

## Troubleshooting
- **TOKEN invalid** → cek `.env`
- **STOP gagal** → proses bot mungkin sudah mati; hapus file `aventa_bot.pid` jika tertinggal
- **Tidak merespon** → cek koneksi internet VPS dan pastikan port Telegram tidak diblok

Selamat mencoba!
