"""
Scheduler thông báo tự động - chạy song song với bot.py
Mỗi tối 20:00 kiểm tra nếu ngày mai là đại kỵ thì nhắc
"""

import asyncio
import json
import os
from datetime import date, timedelta
from telegram import Bot

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "YOUR_CHAT_ID")  # lấy từ /start hoặc @userinfobot
PROFILE_FILE = "user_profile.json"

# Import logic từ bot chính
from bot import tinh_muc_do_ngay, MUC_DO_INFO

async def send_notify():
    profile_path = PROFILE_FILE
    if not os.path.exists(profile_path):
        return

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    if not profile.get("notify", False):
        return

    from datetime import date as d
    from bot import date as date_mod
    birth = d.fromisoformat(profile["birth"])
    tomorrow = d.today() + timedelta(days=1)

    result = tinh_muc_do_ngay(tomorrow, birth)
    if result["muc_do"] >= 3:
        muc = MUC_DO_INFO[result["muc_do"]]
        dp_str = " ⚡ ĐỒNG PHASE 3 KHUNG!" if result["dong_phase"] else ""
        msg = (
            f"📌 Nhắc nhở: Ngày mai *{tomorrow.strftime('%d/%m/%Y')}* là ngày đại kỵ!\n\n"
            f"{muc['label']}{dp_str}\n"
            f"Can Chi: {result['can_chi_ngay']}\n"
            f"⚠️ {muc['vi_du']}"
        )
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")

async def scheduler_loop():
    import datetime
    while True:
        now = datetime.datetime.now()
        # Chạy lúc 20:00 mỗi ngày
        target = now.replace(hour=20, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        await send_notify()

if __name__ == "__main__":
    asyncio.run(scheduler_loop())
