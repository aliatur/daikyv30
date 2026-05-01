# 🌟 Bot Đại Kỵ Nhật Chủ - Telegram

Bot tính ngày đại kỵ cá nhân theo **Nhật Chủ Tứ Trụ** (ngày tháng năm sinh dương lịch).

---

## ⚡ Cách hoạt động

### Logic tính Đại Kỵ
1. Nhập ngày sinh → tính **Nhật Chủ** (Can Chi ngày sinh)
2. Nhật Chủ → xác định **Kỵ Thần** (hành nào khắc mày)
3. Quét lịch → tìm ngày/tháng/năm có Địa Chi mang Kỵ Thần
4. **Đồng Phase 3 Khung** = Ngày + Tháng + Năm đều chứa Kỵ Thần

### 4 mức độ Đại Kỵ
| Mức | Ý nghĩa | Ví dụ đời thường |
|-----|---------|-----------------|
| 🔴 ĐẶC BIỆT NẶNG | Đồng phase 3 khung hoặc xung trực tiếp | Tránh ký hợp đồng, đầu tư, phẫu thuật |
| 🟠 NẶNG | Kỵ Thần mạnh hoặc đồng phase 2 khung | Hạn chế giao dịch tài chính |
| 🟡 TRUNG BÌNH | Kỵ Thần tiêu hao, không xung trực tiếp | Double-check kỹ, tránh mạo hiểm |
| 🟢 NHẸ | Hành không thuận nhưng không xung | Cẩn thận hơn chút, vẫn làm bình thường |

---

## 🚀 Cài đặt & Chạy

### Bước 1: Lấy Bot Token
1. Nhắn @BotFather trên Telegram
2. Gõ `/newbot` → đặt tên → lấy token

### Bước 2: Lấy Anthropic API Key
1. Vào https://console.anthropic.com
2. API Keys → Create Key

### Bước 3: Lấy Chat ID của mày
- Nhắn @userinfobot trên Telegram → lấy số ID

### Bước 4: Cài dependencies
```bash
pip install -r requirements.txt
```

### Bước 5: Set biến môi trường
```bash
# Linux/Mac
export BOT_TOKEN="1234567890:ABCdef..."
export ANTHROPIC_API_KEY="sk-ant-..."
export CHAT_ID="123456789"

# Windows
set BOT_TOKEN=1234567890:ABCdef...
set ANTHROPIC_API_KEY=sk-ant-...
set CHAT_ID=123456789
```

### Bước 6: Chạy bot
```bash
# Terminal 1 - Bot chính
python bot.py

# Terminal 2 - Scheduler thông báo (nếu muốn nhắc tự động)
python scheduler.py
```

---

## 📱 Các lệnh

| Lệnh | Chức năng |
|------|-----------|
| `/start` | Menu chính |
| `/dangky` | Nhập ngày sinh dương lịch |
| `/homnay` | Mức độ đại kỵ hôm nay |
| `/ngaydaiky` | Tất cả ngày cần chú ý trong năm |
| `/thang` | Ngày đại kỵ 1 tháng cụ thể |
| `/dongpha` | Tìm tất cả ngày đồng phase 3 khung |
| `/nhacnho` | Bật/tắt thông báo tự động 20:00 |
| `/tracuu` | Hỏi đáp AI về Tứ Trụ, Can Chi |

---

## ☁️ Deploy lên server (tuỳ chọn)

### Dùng screen (Linux VPS)
```bash
screen -S daiky_bot
python bot.py
# Ctrl+A+D để detach

screen -S daiky_scheduler  
python scheduler.py
# Ctrl+A+D để detach
```

### Dùng systemd (production)
Tạo file `/etc/systemd/system/daiky-bot.service`:
```ini
[Unit]
Description=Dai Ky Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/daiky_bot
ExecStart=/usr/bin/python3 bot.py
Environment=BOT_TOKEN=your_token
Environment=ANTHROPIC_API_KEY=your_key
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable daiky-bot
sudo systemctl start daiky-bot
```

---

## 📝 Lưu ý
- Profile được lưu trong `user_profile.json` (local)
- Bot chỉ phục vụ 1 người dùng (single-user mode)
- `/tracuu` dùng Claude AI, cần API key Anthropic
- Lịch vạn niên tính theo dương lịch, quy đổi Can Chi nội bộ
