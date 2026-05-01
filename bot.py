"""
Bot Telegram - Đại Kỵ Nhật Chủ (Tứ Trụ)
Tính theo ngày tháng năm sinh dương lịch
Phân 4 mức độ nặng nhẹ + đồng phase 3 khung
"""

import logging
from datetime import date, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import anthropic
import json
import os

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")

# File lưu profile user (1 người dùng)
PROFILE_FILE = "user_profile.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── CAN CHI DATA ─────────────────────────────────────────────────────────────

THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI   = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tị", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

# Ngũ hành của Thiên Can
HANH_THIEN_CAN = {
    "Giáp": "Mộc", "Ất": "Mộc",
    "Bính": "Hỏa", "Đinh": "Hỏa",
    "Mậu": "Thổ", "Kỷ": "Thổ",
    "Canh": "Kim", "Tân": "Kim",
    "Nhâm": "Thủy", "Quý": "Thủy"
}

# Ngũ hành của Địa Chi
HANH_DIA_CHI = {
    "Tý": "Thủy", "Sửu": "Thổ", "Dần": "Mộc", "Mão": "Mộc",
    "Thìn": "Thổ", "Tị": "Hỏa", "Ngọ": "Hỏa", "Mùi": "Thổ",
    "Thân": "Kim", "Dậu": "Kim", "Tuất": "Thổ", "Hợi": "Thủy"
}

# Hành khắc: key bị khắc bởi value
HANH_KHAC = {
    "Mộc": "Kim",   # Kim khắc Mộc
    "Kim": "Hỏa",   # Hỏa khắc Kim
    "Hỏa": "Thủy",  # Thủy khắc Hỏa
    "Thủy": "Thổ",  # Thổ khắc Thủy
    "Thổ": "Mộc",   # Mộc khắc Thổ
}

# Xung đối (Địa Chi xung trực tiếp - nặng nhất)
DIA_CHI_XUNG = {
    "Tý": "Ngọ", "Ngọ": "Tý",
    "Sửu": "Mùi", "Mùi": "Sửu",
    "Dần": "Thân", "Thân": "Dần",
    "Mão": "Dậu", "Dậu": "Mão",
    "Thìn": "Tuất", "Tuất": "Thìn",
    "Tị": "Hợi", "Hợi": "Tị"
}

# Hình hại của Địa Chi (mức nặng)
DIA_CHI_HINH_HAI = {
    "Tý": ["Mão"],
    "Mão": ["Tý"],
    "Dần": ["Tị", "Thân"],
    "Tị": ["Dần", "Thân"],
    "Thân": ["Dần", "Tị"],
    "Sửu": ["Tuất", "Mùi"],
    "Tuất": ["Sửu", "Mùi"],
    "Mùi": ["Sửu", "Tuất"],
    "Ngọ": ["Ngọ"],  # Tự hình
    "Thìn": ["Thìn"],
    "Dậu": ["Dậu"],
    "Hợi": ["Hợi"],
}

# ─── CAN CHI CALCULATION ──────────────────────────────────────────────────────

def get_can_chi_year(year: int) -> tuple:
    """Tính Can Chi năm dương lịch"""
    can_idx = (year - 4) % 10
    chi_idx = (year - 4) % 12
    return THIEN_CAN[can_idx], DIA_CHI[chi_idx]

def get_can_chi_month(year: int, month: int) -> tuple:
    """Tính Can Chi tháng (theo tiết khí, đơn giản hóa)"""
    # Tháng bắt đầu từ Dần (tháng 1 âm = Dần)
    # Dương lịch: tháng 1 ~ Sửu, tháng 2 ~ Dần...
    chi_idx = (month + 1) % 12  # offset để Dần = tháng 2 DL
    # Can tháng phụ thuộc Can năm
    can_year_idx = (year - 4) % 10
    # Chu kỳ Can tháng theo Can năm
    can_month_base = {0: 2, 1: 4, 2: 6, 3: 8, 4: 0, 5: 2, 6: 4, 7: 6, 8: 8, 9: 0}
    base = can_month_base[can_year_idx]
    can_idx = (base + month - 1) % 10
    return THIEN_CAN[can_idx], DIA_CHI[chi_idx]

def get_can_chi_day(target_date: date) -> tuple:
    """Tính Can Chi ngày theo công thức Julian Day"""
    ref_date = date(2024, 1, 1)  # 2024/1/1 = Nhâm Tuất (can_idx=8, chi_idx=10)
    ref_can = 8
    ref_chi = 10
    delta = (target_date - ref_date).days
    can_idx = (ref_can + delta) % 10
    chi_idx = (ref_chi + delta) % 12
    return THIEN_CAN[can_idx], DIA_CHI[chi_idx]

# ─── NHẬT CHỦ & KỴ THẦN ──────────────────────────────────────────────────────

def get_nhat_chu(birth_date: date) -> tuple:
    """Trả về (Can, Chi) của ngày sinh = Nhật Chủ"""
    return get_can_chi_day(birth_date)

def get_ky_than(nhat_chu_can: str) -> dict:
    """
    Xác định Kỵ Thần và mức độ từ Nhật Chủ Can
    Trả về dict: hanh -> mức độ kỵ (1-4, 4 là nặng nhất)
    """
    hanh_nhat_chu = HANH_THIEN_CAN[nhat_chu_can]
    hanh_khac_truc_tiep = HANH_KHAC[hanh_nhat_chu]  # hành khắc Nhật Chủ mạnh nhất

    # Xây dựng mức độ kỵ của từng hành
    ky_than = {}

    for hanh in ["Mộc", "Kim", "Hỏa", "Thủy", "Thổ"]:
        if hanh == hanh_khac_truc_tiep:
            ky_than[hanh] = 4  # Khắc trực tiếp - ĐẶC BIỆT NẶNG
        elif HANH_KHAC.get(hanh) == hanh_nhat_chu:
            ky_than[hanh] = 2  # Hành này bị Nhật Chủ khắc lại - tiêu hao
        elif hanh == hanh_nhat_chu:
            ky_than[hanh] = 0  # Cùng hành - không kỵ
        else:
            # Sinh/Tiết - trung bình
            ky_than[hanh] = 1

    return ky_than

# ─── MỨC ĐỘ KỴ ───────────────────────────────────────────────────────────────

MUC_DO_INFO = {
    4: {
        "label": "🔴 ĐẶC BIỆT NẶNG",
        "mo_ta": "Đồng phase 3 khung hoặc Xung trực tiếp Nhật Chủ",
        "vi_du": "Tránh ký hợp đồng, đầu tư lớn, phẫu thuật, khởi nghiệp. Nên ở nhà, nghỉ ngơi, tránh tranh cãi."
    },
    3: {
        "label": "🟠 NẶNG",
        "mo_ta": "Kỵ Thần mạnh xuất hiện trong ngày hoặc đồng phase 2 khung",
        "vi_du": "Hạn chế giao dịch tài chính, tránh gặp đối tác mới. Cẩn thận khi lái xe, không quyết định hấp tấp."
    },
    2: {
        "label": "🟡 TRUNG BÌNH",
        "mo_ta": "Có Kỵ Thần nhưng mức tiêu hao, không xung trực tiếp",
        "vi_du": "Làm việc bình thường nhưng double-check kỹ, tránh mạo hiểm. Không nên nhậu nhẹt hay thức khuya."
    },
    1: {
        "label": "🟢 NHẸ",
        "mo_ta": "Hành không thuận nhưng không xung khắc mạnh",
        "vi_du": "Ngày bình thường, cẩn thận hơn chút là được. Vẫn có thể làm việc, gặp đối tác như bình thường."
    },
    0: {
        "label": "✅ KHÔNG KỴ",
        "mo_ta": "Ngày thuận Nhật Chủ hoặc trung tính",
        "vi_du": "Ngày tốt để ra quyết định, gặp gỡ, đầu tư. Phù hợp khởi công dự án mới."
    }
}

def tinh_muc_do_ngay(target_date: date, birth_date: date) -> dict:
    """Tính mức độ kỵ của 1 ngày cụ thể"""
    nhat_chu_can, nhat_chu_chi = get_nhat_chu(birth_date)
    ky_than = get_ky_than(nhat_chu_can)

    can_ngay, chi_ngay = get_can_chi_day(target_date)
    can_thang, chi_thang = get_can_chi_month(target_date.year, target_date.month)
    can_nam, chi_nam = get_can_chi_year(target_date.year)

    hanh_ngay = HANH_DIA_CHI[chi_ngay]
    hanh_thang = HANH_DIA_CHI[chi_thang]
    hanh_nam = HANH_DIA_CHI[chi_nam]

    # Tính điểm kỵ từng khung
    diem_ngay = ky_than.get(hanh_ngay, 0)
    diem_thang = ky_than.get(hanh_thang, 0)
    diem_nam = ky_than.get(hanh_nam, 0)

    # Kiểm tra xung trực tiếp với Nhật Chủ Chi
    xung_nhat_chu = DIA_CHI_XUNG.get(nhat_chu_chi, "")
    is_xung_ngay = (chi_ngay == xung_nhat_chu)
    is_hinh_hai_ngay = nhat_chu_chi in DIA_CHI_HINH_HAI.get(chi_ngay, [])

    # Đếm số khung kỵ (diem >= 2)
    so_khung_ky = sum(1 for d in [diem_ngay, diem_thang, diem_nam] if d >= 2)

    # Tính mức độ tổng
    if so_khung_ky == 3 or is_xung_ngay:
        muc_do = 4
        dong_phase = True
    elif so_khung_ky == 2 or is_hinh_hai_ngay:
        muc_do = 3
        dong_phase = so_khung_ky == 2
    elif diem_ngay >= 2:
        muc_do = 2
        dong_phase = False
    elif diem_ngay == 1:
        muc_do = 1
        dong_phase = False
    else:
        muc_do = 0
        dong_phase = False

    return {
        "date": target_date,
        "can_chi_ngay": f"{can_ngay} {chi_ngay}",
        "can_chi_thang": f"{can_thang} {chi_thang}",
        "can_chi_nam": f"{can_nam} {chi_nam}",
        "hanh_ngay": hanh_ngay,
        "hanh_thang": hanh_thang,
        "hanh_nam": hanh_nam,
        "muc_do": muc_do,
        "dong_phase": dong_phase,
        "so_khung_ky": so_khung_ky,
        "is_xung": is_xung_ngay,
        "nhat_chu": f"{nhat_chu_can} {nhat_chu_chi}",
        "hanh_nhat_chu": HANH_THIEN_CAN[nhat_chu_can],
    }

# ─── PROFILE ──────────────────────────────────────────────────────────────────

def load_profile() -> dict:
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_profile(profile: dict):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

# ─── FORMAT HELPERS ───────────────────────────────────────────────────────────

def format_ngay_result(result: dict) -> str:
    muc = MUC_DO_INFO[result["muc_do"]]
    dong_phase_str = ""
    if result["dong_phase"]:
        dong_phase_str = f"\n⚡ ĐỒNG PHASE {result['so_khung_ky']} KHUNG"
    if result["is_xung"]:
        dong_phase_str += "\n💥 XUNG TRỰC TIẾP NHẬT CHỦ"

    return (
        f"📅 {result['date'].strftime('%d/%m/%Y')}\n"
        f"Nhật Chủ: {result['nhat_chu']} ({result['hanh_nhat_chu']})\n"
        f"Can Chi ngày: {result['can_chi_ngay']} [{result['hanh_ngay']}]\n"
        f"Can Chi tháng: {result['can_chi_thang']} [{result['hanh_thang']}]\n"
        f"Can Chi năm: {result['can_chi_nam']} [{result['hanh_nam']}]\n"
        f"{dong_phase_str}\n"
        f"\n{muc['label']}\n"
        f"📌 {muc['mo_ta']}\n"
        f"⚠️ {muc['vi_du']}"
    )

# ─── CONVERSATION STATE ───────────────────────────────────────────────────────
WAITING_BIRTHDAY = 1
WAITING_TRACUU = 2
WAITING_THANG = 3

# ─── HANDLERS ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🌟 *Bot Đại Kỵ Nhật Chủ* 🌟\n\n"
        "Các lệnh có sẵn:\n"
        "/dangky - Đăng ký ngày sinh\n"
        "/ngaydaiky - Ngày đại kỵ cả năm\n"
        "/thang - Ngày đại kỵ 1 tháng cụ thể\n"
        "/homnay - Mức độ đại kỵ hôm nay\n"
        "/dongpha - Ngày đồng phase 3 khung\n"
        "/nhacnho - Bật/tắt thông báo\n"
        "/tracuu - Hỏi đáp tự do (AI)\n\n"
        "👉 Bắt đầu với /dangky để nhập ngày sinh!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ── /dangky ──
async def cmd_dangky(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Nhập ngày sinh dương lịch theo định dạng:\n*DD/MM/YYYY*\n\nVí dụ: 15/08/1990",
        parse_mode="Markdown"
    )
    return WAITING_BIRTHDAY

async def handle_birthday(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        parts = text.split("/")
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        birth = date(y, m, d)
    except:
        await update.message.reply_text("❌ Sai định dạng. Nhập lại: DD/MM/YYYY")
        return WAITING_BIRTHDAY

    nhat_chu_can, nhat_chu_chi = get_nhat_chu(birth)
    hanh = HANH_THIEN_CAN[nhat_chu_can]
    ky_than = get_ky_than(nhat_chu_can)
    hanh_ky = [h for h, d in ky_than.items() if d >= 2]

    profile = {
        "birth": birth.isoformat(),
        "nhat_chu_can": nhat_chu_can,
        "nhat_chu_chi": nhat_chu_chi,
        "hanh_nhat_chu": hanh,
        "ky_than": ky_than,
        "notify": False
    }
    save_profile(profile)

    await update.message.reply_text(
        f"✅ Đã lưu!\n\n"
        f"🧬 Nhật Chủ của bạn: *{nhat_chu_can} {nhat_chu_chi}* ({hanh})\n"
        f"⚠️ Kỵ Thần (hành khắc): *{', '.join(hanh_ky)}*\n\n"
        f"Dùng /ngaydaiky để xem ngay!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ── /homnay ──
async def cmd_homnay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    profile = load_profile()
    if not profile:
        await update.message.reply_text("⚠️ Chưa có ngày sinh. Dùng /dangky trước!")
        return

    birth = date.fromisoformat(profile["birth"])
    today = date.today()
    result = tinh_muc_do_ngay(today, birth)

    msg = f"📊 *ĐÁNH GIÁ HÔM NAY* - {today.strftime('%d/%m/%Y')}\n\n"
    msg += format_ngay_result(result)
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /ngaydaiky ──
async def cmd_ngaydaiky(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    profile = load_profile()
    if not profile:
        await update.message.reply_text("⚠️ Chưa có ngày sinh. Dùng /dangky trước!")
        return

    birth = date.fromisoformat(profile["birth"])
    year = date.today().year
    await update.message.reply_text(f"⏳ Đang tính ngày đại kỵ năm {year}...")

    # Gom theo tháng, chỉ lấy ngày mức >= 2
    results_by_month = {}
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        r = tinh_muc_do_ngay(d, birth)
        if r["muc_do"] >= 2:
            m = d.month
            if m not in results_by_month:
                results_by_month[m] = []
            results_by_month[m].append(r)
        d += timedelta(days=1)

    THANG_TEN = ["", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
                 "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
                 "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]

    for month in range(1, 13):
        days = results_by_month.get(month, [])
        if not days:
            continue
        msg = f"📅 *{THANG_TEN[month]}* - Ngày cần chú ý:\n"
        for r in days:
            icon = "🔴" if r["muc_do"] == 4 else "🟠" if r["muc_do"] == 3 else "🟡"
            dp = " ⚡3K" if r["dong_phase"] else ""
            xung = " 💥XUNG" if r["is_xung"] else ""
            msg += f"{icon} *{r['date'].strftime('%d/%m')}* ({r['can_chi_ngay']}){dp}{xung}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

# ── /thang ──
async def cmd_thang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📅 Nhập số tháng cần xem (1-12):")
    return WAITING_THANG

async def handle_thang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    profile = load_profile()
    if not profile:
        await update.message.reply_text("⚠️ Chưa có ngày sinh. Dùng /dangky trước!")
        return ConversationHandler.END

    try:
        month = int(update.message.text.strip())
        if month < 1 or month > 12:
            raise ValueError
    except:
        await update.message.reply_text("❌ Nhập số từ 1 đến 12")
        return WAITING_THANG

    birth = date.fromisoformat(profile["birth"])
    year = date.today().year

    import calendar
    _, last_day = calendar.monthrange(year, month)
    d = date(year, month, 1)
    end = date(year, month, last_day)

    results = []
    while d <= end:
        r = tinh_muc_do_ngay(d, birth)
        results.append(r)
        d += timedelta(days=1)

    msg = f"📋 *Chi tiết tháng {month}/{year}*\n\n"
    for r in results:
        if r["muc_do"] == 0:
            continue
        muc = MUC_DO_INFO[r["muc_do"]]
        dp = " ⚡ĐỒNG PHASE" if r["dong_phase"] else ""
        xung = " 💥XUNG" if r["is_xung"] else ""
        msg += (
            f"{muc['label'][:2]} *{r['date'].strftime('%d/%m')}*"
            f" | {r['can_chi_ngay']} | {r['hanh_ngay']}{dp}{xung}\n"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")
    return ConversationHandler.END

# ── /dongpha ──
async def cmd_dongpha(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    profile = load_profile()
    if not profile:
        await update.message.reply_text("⚠️ Chưa có ngày sinh. Dùng /dangky trước!")
        return

    birth = date.fromisoformat(profile["birth"])
    year = date.today().year
    await update.message.reply_text("⚡ Đang tìm ngày ĐỒNG PHASE 3 KHUNG...")

    dong_phase_days = []
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        r = tinh_muc_do_ngay(d, birth)
        if r["dong_phase"] and r["so_khung_ky"] == 3:
            dong_phase_days.append(r)
        d += timedelta(days=1)

    if not dong_phase_days:
        await update.message.reply_text(f"✅ Năm {year} không có ngày đồng phase 3 khung. Tương đối an toàn!")
        return

    msg = f"⚡ *NGÀY ĐỒNG PHASE 3 KHUNG - {year}*\n"
    msg += f"_(Ngày + Tháng + Năm cùng kỵ Nhật Chủ)_\n\n"
    msg += "🔴 *TRÁNH TUYỆT ĐỐI*: Ký kết, đầu tư, phẫu thuật, tranh cãi\n\n"

    for r in dong_phase_days:
        msg += (
            f"💀 *{r['date'].strftime('%d/%m/%Y')}*\n"
            f"   Ngày: {r['can_chi_ngay']} [{r['hanh_ngay']}]\n"
            f"   Tháng: {r['can_chi_thang']} [{r['hanh_thang']}]\n"
            f"   Năm: {r['can_chi_nam']} [{r['hanh_nam']}]\n\n"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /nhacnho ──
async def cmd_nhacnho(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    profile = load_profile()
    if not profile:
        await update.message.reply_text("⚠️ Chưa có ngày sinh. Dùng /dangky trước!")
        return

    profile["notify"] = not profile.get("notify", False)
    save_profile(profile)
    status = "🔔 BẬT" if profile["notify"] else "🔕 TẮT"
    await update.message.reply_text(
        f"Thông báo tự động: {status}\n\n"
        f"Khi bật, bot sẽ nhắc bạn vào 8h tối hôm trước những ngày đại kỵ nặng (🔴🟠).\n"
        f"_(Cần chạy scheduler riêng - xem README.md)_"
    )

# ── /tracuu ──
async def cmd_tracuu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    profile = load_profile()
    context_str = ""
    if profile:
        context_str = (
            f"Thông tin người dùng:\n"
            f"- Ngày sinh: {profile['birth']}\n"
            f"- Nhật Chủ: {profile['nhat_chu_can']} {profile['nhat_chu_chi']} ({profile['hanh_nhat_chu']})\n"
            f"- Kỵ Thần: {profile['ky_than']}\n"
        )

    await update.message.reply_text(
        "🤖 Chế độ tra cứu AI. Hỏi bất kỳ điều gì về Tứ Trụ, Đại Kỵ, Can Chi...\n"
        "Gõ /exit để thoát."
    )
    ctx.user_data["tracuu_context"] = context_str
    ctx.user_data["tracuu_history"] = []
    return WAITING_TRACUU

async def handle_tracuu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip().lower() in ["/exit", "exit", "thoát"]:
        await update.message.reply_text("✅ Thoát chế độ tra cứu.")
        return ConversationHandler.END

    user_msg = update.message.text.strip()
    history = ctx.user_data.get("tracuu_history", [])
    profile_ctx = ctx.user_data.get("tracuu_context", "")

    system_prompt = (
        "Bạn là chuyên gia Tứ Trụ, Bát Tự, Can Chi, lịch vạn niên. "
        "Trả lời ngắn gọn, rõ ràng bằng tiếng Việt. "
        "Tập trung vào Nhật Chủ, Kỵ Thần, Đại Kỵ, Đồng Phase. "
        f"\n{profile_ctx}"
    )

    history.append({"role": "user", "content": user_msg})

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=history
        )
        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        ctx.user_data["tracuu_history"] = history[-10:]  # giữ 10 turn gần nhất

        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi AI: {str(e)}")

    return WAITING_TRACUU

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ConversationHandler cho /dangky
    dangky_handler = ConversationHandler(
        entry_points=[CommandHandler("dangky", cmd_dangky)],
        states={WAITING_BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_birthday)]},
        fallbacks=[]
    )

    # ConversationHandler cho /thang
    thang_handler = ConversationHandler(
        entry_points=[CommandHandler("thang", cmd_thang)],
        states={WAITING_THANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_thang)]},
        fallbacks=[]
    )

    # ConversationHandler cho /tracuu
    tracuu_handler = ConversationHandler(
        entry_points=[CommandHandler("tracuu", cmd_tracuu)],
        states={WAITING_TRACUU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tracuu)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("homnay", cmd_homnay))
    app.add_handler(CommandHandler("ngaydaiky", cmd_ngaydaiky))
    app.add_handler(CommandHandler("dongpha", cmd_dongpha))
    app.add_handler(CommandHandler("nhacnho", cmd_nhacnho))
    app.add_handler(dangky_handler)
    app.add_handler(thang_handler)
    app.add_handler(tracuu_handler)

    logger.info("Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
