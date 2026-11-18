import json
import time
import uuid
import requests
import telebot
from telebot import types
import os

# ========== الإعدادات ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "9052738013:AAE6oSr_r7V8MsbzOwNtTkSeHK1gXDlP9VM")

# ========== إعدادات الأدمن ==========
ADMIN_ID = 9052738013
ADMIN_USERNAME = "@Mmo23110"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود!")

bot = telebot.TeleBot(BOT_TOKEN)

try:
    bot.remove_webhook()
except:
    pass

USERS_FILE = "users_data.json"
SETTINGS_FILE = "settings.json"
BANNED_FILE = "banned_users.json"

# ========== تحميل وحفظ البيانات ==========
def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(file, data):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

users_data = load_json(USERS_FILE, {})
settings = load_json(SETTINGS_FILE, {"bot_enabled": True})
banned_users = load_json(BANNED_FILE, [])

def save_users():
    save_json(USERS_FILE, users_data)

def save_settings():
    save_json(SETTINGS_FILE, settings)

def save_banned():
    save_json(BANNED_FILE, banned_users)

# ========== فحص حالة البوت ==========
def is_bot_enabled():
    return settings.get("bot_enabled", True)

def is_banned(user_id):
    return str(user_id) in [str(b) for b in banned_users]

def is_admin(user_id):
    return int(user_id) == ADMIN_ID

# ========== API Twist ==========
class TwistMusicAPI:
    def __init__(self, user_id=None):
        self.base_url = "https://api.twistmena.com/music"
        self.device_id = "AP3A.240905.015.A2"
        self.session_id = str(uuid.uuid4())
        self.token = None
        self.access_token = None
        self.tg_token = None
        self.refresh_token = None
        self.balance = 0
        self.phone = None
        self.monthly_used = 0
        self.user_id = user_id

    def get_headers(self, extra=None):
        headers = {
            "user-agent": "Twist-Mobile/11.2.10 (Android; 15; Infinix X6885; music; ar-EG)",
            "app_version": "11.2.10",
            "appversion": "11.2.10",
            "channel": "mobileapp",
            "platform": "android",
            "accept": "application/json",
            "accept-language": "ar",
            "content-type": "application/json",
            "device_id": self.device_id,
            "sessionid": self.session_id,
            "host": "api.twistmena.com",
            "connection": "keep-alive",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.access_token:
            headers["access-token"] = self.access_token
        if self.tg_token:
            headers["tg-token"] = self.tg_token
        if self.refresh_token:
            headers["tg-refresh-token"] = self.refresh_token
        if extra:
            headers.update(extra)
        return headers

    def format_phone(self, phone):
        phone = phone.strip().replace(" ", "").replace("+", "")
        if phone.startswith("0"):
            return "20" + phone[1:]
        if phone.startswith("20"):
            return phone
        return "20" + phone

    def send_otp(self, phone):
        formatted_phone = self.format_phone(phone)
        url = f"{self.base_url}/Dlogin/sendCode"
        payload = {"dial": formatted_phone}
        try:
            response = requests.post(url, json=payload, headers=self.get_headers(), timeout=30)
            if response.status_code == 200:
                self.phone = formatted_phone
                return True, "✅ تم إرسال كود التحقق بنجاح!"
            return False, "❌ فشل الإرسال"
        except Exception as e:
            return False, f"❌ خطأ: {str(e)}"

    def verify_otp(self, code):
        if not self.phone:
            return False, "❌ لم يتم إرسال كود بعد!"
        url = f"{self.base_url}/Dlogin/verify"
        payload = {
            "dial": self.phone,
            "verifyCode": code,
            "socialServiceName": "",
            "socialServiceToken": "",
        }
        try:
            response = requests.post(url, json=payload, headers=self.get_headers(), timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.access_token = data.get("accessToken")
                self.tg_token = data.get("tgToken")
                self.refresh_token = data.get("refreshToken")
                self.get_balance()
                return True, "✅ تم تسجيل الدخول بنجاح!"
            return False, "❌ كود غير صحيح!"
        except Exception as e:
            return False, f"❌ خطأ: {str(e)}"

    def get_balance(self):
        if not self.token:
            return 0
        url = f"{self.base_url}/user/loyalty/balance/details"
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.balance = data.get("balance", 0)
                return self.balance
            return 0
        except:
            return 0

    def complete_tasks(self):
        if not self.token:
            return False, "❌ يجب تسجيل الدخول أولاً!"
            
        url = f"{self.base_url}/user/loyalty/achievements/v2"
        try:
            # 1. جلب الرصيد قبل تنفيذ المهام
            old_balance = self.get_balance()
            
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            if response.status_code != 200:
                return False, "❌ فشل جلب المهام"
                
            data = response.json()
            badges = data.get("badges", [])
            completed = 0
            
            for category in badges:
                for task in category.get("badges", []):
                    if not task.get("rewarded"):
                        action_url = f"{self.base_url}/loyalty/action/{task.get('id')}"
                        requests.post(action_url, headers=self.get_headers(), timeout=30)
                        completed += 1
            
            # 2. جلب الرصيد بعد تنفيذ المهام
            self.get_balance()
            new_balance = self.balance
            
            # 3. حساب الفرق (الكوينز اللي اتضافت فعلياً)
            points_earned = new_balance - old_balance
            if points_earned < 0: 
                points_earned = 0
                
            if completed == 0:
                return True, f"ℹ️ مفيش مهام جديدة متاحة حالياً.\n📊 رصيدك الحالي: {self.balance} كوينز"
                
            return True, f"✅ تم إنجاز {completed} مهمة\n💰 ربحت {points_earned} كوينز\n📊 رصيدك الحالي: {self.balance} كوينز"
            
        except Exception as e:
            return False, f"❌ خطأ: {str(e)}"

    def redeem_units(self, package_id):
        if not self.token:
            return False, "❌ يجب تسجيل الدخول أولاً!"
        packages = {
            "1": "EAND_50_UNITS_ID_9",
            "2": "EAND_100_UNITS_ID_10",
            "3": "EAND_150_UNITS_ID_11",
            "4": "EAND_300_UNITS_ID_12",
            "5": "EAND_500_UNITS_ID_13",
            "6": "EAND_750_UNITS_ID_14",
            "7": "EAND_1000_UNITS_ID_15",
        }
        costs = {"1": 100, "2": 200, "3": 300, "4": 600, "5": 1000, "6": 1500, "7": 2000}
        units = {"1": 50, "2": 100, "3": 150, "4": 300, "5": 500, "6": 750, "7": 1000}
        if package_id not in packages:
            return False, "❌ باقة غير معروفة"
        if self.monthly_used + units[package_id] > 2000:
            return False, "⚠️ تم تجاوز الحد الشهري!"
        if self.balance < costs.get(package_id, 0):
            return False, f"⚠️ رصيدك غير كافٍ! تحتاج {costs[package_id]} كوينز."
        url = f"{self.base_url}/loyalty/redeem/{packages.get(package_id)}"
        try:
            response = requests.post(url, headers=self.get_headers(), timeout=30)
            if response.status_code == 200:
                self.monthly_used += units[package_id]
                self.get_balance()
                return True, f"✅ تم استبدال {units[package_id]} وحدة بنجاح!"
            return False, "❌ فشل الاستبدال"
        except Exception as e:
            return False, f"❌ خطأ: {str(e)}"

user_sessions = {}

# ========== رسائل النظام ==========
def send_bot_disabled(chat_id):
    text = (
        "🛑 <b>البوت متوقف مؤقتاً</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ تم إيقاف البوت من قِبل الإدارة\n"
        "🔄 يرجى المحاولة لاحقاً"
    )
    bot.send_message(chat_id, text, parse_mode="HTML")

def send_banned_msg(chat_id):
    text = (
        "🚫 <b>أنت محظور</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⛔️ تم حظرك من استخدام البوت\n"
        f"📞 للتواصل مع الإدارة: {ADMIN_USERNAME}"
    )
    bot.send_message(chat_id, text, parse_mode="HTML")

def check_access(message_or_call):
    if hasattr(message_or_call, 'from_user'):
        user_id = message_or_call.from_user.id
    else:
        user_id = message_or_call.from_user.id

    chat_id = None
    if hasattr(message_or_call, 'message') and message_or_call.message:
        chat_id = message_or_call.message.chat.id
    elif hasattr(message_or_call, 'chat'):
        chat_id = message_or_call.chat.id

    # الأدمن دايماً مسموح
    if is_admin(user_id):
        return True

    if is_banned(user_id):
        if chat_id:
            send_banned_msg(chat_id)
        return False

    if not is_bot_enabled():
        if chat_id:
            send_bot_disabled(chat_id)
        return False

    return True

# ========== الأزرار والقوائم (ملونة بالإيموجي) ==========

def get_back_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔴 🔙 رجوع للقائمة الرئيسية", callback_data="cancel_to_menu"))
    return keyboard

def show_main_menu(chat_id):
    total_users = len(users_data)
    current_time = time.strftime('%I:%M')

    text = (
        "🎵 <b>❤️🧡💛 مرحباً بك في بوت Twist Music! 💚💙💜</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏠 <b>🌈 البوت الرسمي لتجميع نقاط تويست</b>\n"
        "⚡️ <b>⭐ سريع | آمن | موثوق 100% ⭐</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>🎨 اختر الخدمة يا معلم:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>👤 المستخدمين:</b> <code>{total_users}</code>\n"
        f"⏰ <b>🕐 {current_time}</b>"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("🟢 ✨ تجميع نقاط تويست", callback_data="collect_points"))
    keyboard.add(types.InlineKeyboardButton("🔵 💰 رصيدي الحالي", callback_data="my_balance"))
    keyboard.add(types.InlineKeyboardButton("🟡 📖 حول البوت", callback_data="about_bot"))
    keyboard.add(types.InlineKeyboardButton("🟣 📈 احصائيات حسابي", callback_data="my_stats"))
    keyboard.add(types.InlineKeyboardButton("🟠 👨‍💻 المطور", callback_data="developer"))

    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")

def show_admin_panel(chat_id):
    total_users = len(users_data)
    bot_status = "🟢 يعمل" if is_bot_enabled() else "🔴 متوقف"
    banned_count = len(banned_users)

    text = (
        "👑 <b>لوحة تحكم الأدمن</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>إجمالي المستخدمين:</b> <code>{total_users}</code>\n"
        f"🚫 <b>المحظورين:</b> <code>{banned_count}</code>\n"
        f"⚡ <b>حالة البوت:</b> {bot_status}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "اختر الإجراء المطلوب:"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    if is_bot_enabled():
        keyboard.add(types.InlineKeyboardButton("🔴 🛑 إيقاف البوت للجميع", callback_data="admin_stop_bot"))
    else:
        keyboard.add(types.InlineKeyboardButton("🟢 ▶️ تشغيل البوت للجميع", callback_data="admin_start_bot"))

    keyboard.add(types.InlineKeyboardButton("🔴 🚫 حظر مستخدم", callback_data="admin_ban"))
    keyboard.add(types.InlineKeyboardButton("🟢 ✅ فك حظر مستخدم", callback_data="admin_unban"))
    keyboard.add(types.InlineKeyboardButton("🟡 📋 قائمة المحظورين", callback_data="admin_list_banned"))
    keyboard.add(types.InlineKeyboardButton("🔵 📊 إحصائيات المستخدمين", callback_data="admin_stats"))

    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")

def start_collect_points(chat_id):
    text = (
        "🔄✨ <b>تجميع نقاط تويست</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 يرجى إدخال رقم هاتفك مع مفتاح الدولة\n"
        "📞 مثال: 011xxxxxxxx أو +2011xxxxxxxx\n\n"
        "🔙 للرجوع اضغط على الزر بالأسفل"
    )
    msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=get_back_keyboard())
    bot.register_next_step_handler(msg, process_phone_input)

def show_packages_menu(chat_id):
    api = user_sessions.get(chat_id)
    if not api:
        show_main_menu(chat_id)
        return
    remaining = 2000 - api.monthly_used
    text = f"📊 <b>رصيدك الحالي:</b> {api.balance} كوينز\n📉 <b>الحد الشهري المتبقي:</b> {remaining} وحدة\n\n🎁 <b>اختر الباقة التي تريد استبدالها:</b>"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("🟢 🎁 50 وحدة (100 كوينز)", callback_data="redeem_1"))
    keyboard.add(types.InlineKeyboardButton("🟢 🎁 100 وحدة (200 كوينز)", callback_data="redeem_2"))
    keyboard.add(types.InlineKeyboardButton("🟡 🎁 150 وحدة (300 كوينز)", callback_data="redeem_3"))
    keyboard.add(types.InlineKeyboardButton("🟠 🎁 300 وحدة (600 كوينز)", callback_data="redeem_4"))
    keyboard.add(types.InlineKeyboardButton("🔴 🎁 500 وحدة (1000 كوينز)", callback_data="redeem_5"))
    keyboard.add(types.InlineKeyboardButton("🔴 🎁 750 وحدة (1500 كوينز)", callback_data="redeem_6"))
    keyboard.add(types.InlineKeyboardButton("🔴 🎁 1000 وحدة (2000 كوينز)", callback_data="redeem_7"))
    keyboard.add(types.InlineKeyboardButton("🔵 🏠 القائمة الرئيسية", callback_data="main_menu"))
    
    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")

def show_balance(chat_id):
    api = user_sessions.get(chat_id)
    if not api or not api.token:
        text = "💳 <b>رصيدي الحالي</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ <b>يجب تسجيل الدخول أولاً!</b>"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🟢 🔄 تجميع نقاط تويست", callback_data="collect_points"))
        keyboard.add(types.InlineKeyboardButton("🔵 🏠 القائمة الرئيسية", callback_data="main_menu"))
        bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
        return
    balance = api.get_balance()
    remaining = 2000 - api.monthly_used
    text = f"💳 <b>رصيدي الحالي</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💰 <b>رصيد الكوينز:</b> <code>{balance}</code>\n📊 <b>الوحدات المتبقية شهرياً:</b> <code>{remaining}</code>\n📱 <b>رقم الهاتف:</b> <code>{api.phone}</code>"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("🟡 🔄 تحديث الرصيد", callback_data="refresh_balance"))
    keyboard.add(types.InlineKeyboardButton("🔵 🏠 القائمة الرئيسية", callback_data="main_menu"))
    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")

def about_bot(chat_id):
    total_users = len(users_data)
    text = f"ℹ️ <b>حول البوت</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎵 <b>بوت Twist Music</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>الوظيفة:</b> تجميع نقاط تويست بسرعة\n⚡️ <b>سرعة:</b> تنفيذ تلقائي للمهام\n🔒 <b>آمان:</b> موثوق 100%\n📱 <b>متطلبات:</b> حساب في تطبيق Twist\n👥 <b>عدد المستخدمين:</b> {total_users}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👨‍💻 <b>المطور:</b> {ADMIN_USERNAME}"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("🟢 📞 تواصل مع المطور", callback_data="contact_owner"))
    keyboard.add(types.InlineKeyboardButton("🔵 🏠 القائمة الرئيسية", callback_data="main_menu"))
    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")

def my_stats(chat_id):
    api = user_sessions.get(chat_id)
    user_id = str(chat_id)
    if not api or not api.token:
        text = "📊 <b>احصائيات حسابي</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ <b>يجب تسجيل الدخول أولاً!</b>"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🟢 🔄 تجميع نقاط تويست", callback_data="collect_points"))
        keyboard.add(types.InlineKeyboardButton("🔵 🏠 القائمة الرئيسية", callback_data="main_menu"))
        bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
        return
    user_info = users_data.get(user_id, {})
    text = f"📊 <b>احصائيات حسابي</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💰 <b>رصيد الكوينز:</b> <code>{api.balance}</code>\n📱 <b>رقم الهاتف:</b> <code>{api.phone}</code>\n📊 <b>الوحدات المستهلكة هذا الشهر:</b> <code>{api.monthly_used}/2000</code>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📌 <b>مرات استخدام البوت:</b> <code>{user_info.get('uses_count', 0)}</code>\n📅 <b>أول استخدام:</b> <code>{user_info.get('first_use', 'غير معروف')}</code>"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("🟡 🔄 تحديث الإحصائيات", callback_data="refresh_stats"))
    keyboard.add(types.InlineKeyboardButton("🔵 🏠 القائمة الرئيسية", callback_data="main_menu"))
    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")

def developer(chat_id):
    text = f"👨‍💻 <b>معلومات التواصل</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📌 <b>المطور:</b> {ADMIN_USERNAME}\n📨 <b>للتواصل:</b> اضغط على الزر أدناه"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("🟢 📨 تواصل مع المطور", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"))
    keyboard.add(types.InlineKeyboardButton("🔵 🏠 القائمة الرئيسية", callback_data="main_menu"))
    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")

def contact_owner(chat_id):
    text = f"📞 <b>تواصل مع المطور</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👨‍💻 <b>المطور:</b> {ADMIN_USERNAME}\n📝 <b>للتواصل:</b> اضغط على الزر أدناه"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("🟢 📨 مراسلة المطور", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"))
    keyboard.add(types.InlineKeyboardButton("🔵 🏠 القائمة الرئيسية", callback_data="main_menu"))
    bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")


# ========== معالجات الخطوات ==========
def process_phone_input(message):
    chat_id = message.chat.id
    if not check_access(message):
        return
    if not message.text:
        msg = bot.send_message(chat_id, "❌ أرسل رقم صحيح أو اضغط زر الرجوع:",
                               parse_mode="HTML", reply_markup=get_back_keyboard())
        bot.register_next_step_handler(msg, process_phone_input)
        return
    phone = message.text.strip()
    if phone.lower() in ['الغاء', 'cancel', 'إلغاء']:
        show_main_menu(chat_id)
        return
    if not phone or len(phone) < 8:
        msg = bot.send_message(chat_id, "❌ رقم غير صحيح! حاول مرة أخرى:",
                               parse_mode="HTML", reply_markup=get_back_keyboard())
        bot.register_next_step_handler(msg, process_phone_input)
        return

    bot.send_message(chat_id, "⏳ جاري إرسال كود التحقق...")
    api = user_sessions.get(chat_id, TwistMusicAPI())
    user_sessions[chat_id] = api
    success, msg_text = api.send_otp(phone)
    bot.send_message(chat_id, msg_text)

    if success:
        user_id_str = str(message.from_user.id)
        if user_id_str in users_data:
            users_data[user_id_str]["phone"] = phone
            save_users()
        text = "🔐 <b>تم إرسال كود التحقق</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📱 أدخل الكود المكون من 6 أرقام:\n\n🔙 للرجوع اضغط على الزر بالأسفل"
        msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=get_back_keyboard())
        bot.register_next_step_handler(msg, process_otp_input)
    else:
        text = "❌ <b>فشل إرسال الكود</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔄 يرجى المحاولة مرة أخرى:"
        msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=get_back_keyboard())
        bot.register_next_step_handler(msg, process_phone_input)

def process_otp_input(message):
    chat_id = message.chat.id
    if not check_access(message):
        return
    if not message.text:
        msg = bot.send_message(chat_id, "❌ أرسل الكود أو اضغط زر الرجوع:",
                               parse_mode="HTML", reply_markup=get_back_keyboard())
        bot.register_next_step_handler(msg, process_otp_input)
        return
    code = message.text.strip()
    if code.lower() in ['الغاء', 'cancel', 'إلغاء']:
        show_main_menu(chat_id)
        return
    if not code or len(code) != 6 or not code.isdigit():
        msg = bot.send_message(chat_id, "❌ الكود يجب أن يكون 6 أرقام. حاول مرة أخرى:",
                               parse_mode="HTML", reply_markup=get_back_keyboard())
        bot.register_next_step_handler(msg, process_otp_input)
        return

    bot.send_message(chat_id, "⏳ جاري التحقق من الكود...")
    api = user_sessions.get(chat_id)
    if not api:
        bot.send_message(chat_id, "⚠️ حدث خطأ في الجلسة، أعد المحاولة.")
        show_main_menu(chat_id)
        return
    success, msg_text = api.verify_otp(code)
    bot.send_message(chat_id, msg_text)

    if success:
        bot.send_message(chat_id, "⚡ جاري تنفيذ المهام التلقائية وحصد الكوينز...")
        task_success, task_msg = api.complete_tasks()
        bot.send_message(chat_id, task_msg)
        show_packages_menu(chat_id)
    else:
        text = "❌ <b>كود غير صحيح</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔄 حاول مرة أخرى:"
        msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=get_back_keyboard())
        bot.register_next_step_handler(msg, process_otp_input)

# ========== أوامر الأدمن والبدء ==========
@bot.message_handler(commands=["admin"])
def admin_command(message):
    if not is_admin(message.from_user.id):
        return # أي حد تاني ميردش عليه
    show_admin_panel(message.chat.id)

@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_id_str = str(user_id)
    username = message.from_user.username or "مستخدم"

    if not check_access(message):
        return

    if user_id_str not in users_data:
        users_data[user_id_str] = {
            "username": username,
            "first_use": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uses_count": 0,
            "phone": None
        }
    users_data[user_id_str]["uses_count"] = users_data[user_id_str].get("uses_count", 0) + 1
    users_data[user_id_str]["username"] = username
    save_users()

    user_sessions[chat_id] = TwistMusicAPI(user_id=user_id_str)
    show_main_menu(chat_id)

# ========== دوال الحظر وفك الحظر ==========
def start_ban_user(chat_id):
    msg = bot.send_message(
        chat_id,
        "🚫 <b>حظر مستخدم</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "أرسل <b>ID</b> المستخدم اللي عايز تحظره:\n"
        "للإلغاء أرسل /cancel",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_ban_user)

def process_ban_user(message):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        show_admin_panel(message.chat.id)
        return
    try:
        target_id = str(message.text.strip())
        if target_id in banned_users:
            bot.send_message(message.chat.id, f"⚠️ المستخدم <code>{target_id}</code> محظور بالفعل!", parse_mode="HTML")
            show_admin_panel(message.chat.id)
            return
        banned_users.append(target_id)
        save_banned()
        bot.send_message(message.chat.id, f"✅ تم حظر المستخدم: <code>{target_id}</code>", parse_mode="HTML")
        show_admin_panel(message.chat.id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")
        show_admin_panel(message.chat.id)

def start_unban_user(chat_id):
    msg = bot.send_message(
        chat_id,
        "✅ <b>فك حظر مستخدم</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "أرسل <b>ID</b> المستخدم اللي عايز تفك حظره:\n"
        "للإلغاء أرسل /cancel",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_unban_user)

def process_unban_user(message):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        show_admin_panel(message.chat.id)
        return
    try:
        target_id = str(message.text.strip())
        if target_id not in [str(b) for b in banned_users]:
            bot.send_message(message.chat.id, f"⚠️ المستخدم <code>{target_id}</code> غير محظور!", parse_mode="HTML")
            show_admin_panel(message.chat.id)
            return
        banned_users[:] = [b for b in banned_users if str(b) != target_id]
        save_banned()
        bot.send_message(message.chat.id, f"✅ تم فك حظر المستخدم: <code>{target_id}</code>", parse_mode="HTML")
        show_admin_panel(message.chat.id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")
        show_admin_panel(message.chat.id)

# ========== معالج الأزرار ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data

    # 1. أزرار لوحة تحكم الأدمن (تشتغل حتى لو البوت متوقف)
    admin_actions = ["admin_stop_bot", "admin_start_bot", "admin_ban",
                     "admin_unban", "admin_list_banned", "admin_stats"]
    if data in admin_actions:
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⛔️ غير مصرح", show_alert=True)
            return
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass

        if data == "admin_stop_bot":
            settings["bot_enabled"] = False
            save_settings()
            bot.send_message(chat_id, "🛑 <b>تم إيقاف البوت للجميع</b>", parse_mode="HTML")
            show_admin_panel(chat_id)
        elif data == "admin_start_bot":
            settings["bot_enabled"] = True
            save_settings()
            bot.send_message(chat_id, "▶️ <b>تم تشغيل البوت للجميع</b>", parse_mode="HTML")
            show_admin_panel(chat_id)
        elif data == "admin_ban":
            start_ban_user(chat_id)
        elif data == "admin_unban":
            start_unban_user(chat_id)
        elif data == "admin_list_banned":
            if not banned_users:
                bot.send_message(chat_id, "📋 <b>قائمة المحظورين فاضية</b>", parse_mode="HTML")
            else:
                txt = "📋 <b>قائمة المحظورين:</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                for i, b in enumerate(banned_users, 1):
                    txt += f"{i}. <code>{b}</code>\n"
                bot.send_message(chat_id, txt, parse_mode="HTML")
            show_admin_panel(chat_id)
        elif data == "admin_stats":
            # التعديل هنا: عدد المستخدمين فقط بدون أسماء ولا آي دي
            total_uses = sum(info.get('uses_count', 0) for info in users_data.values())
            
            txt = (
                f"📊 <b>إحصائيات البوت</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 <b>عدد الأشخاص الذين استخدموا البوت:</b> <code>{len(users_data)}</code> مستخدم\n"
                f"🔄 <b>إجمالي مرات التشغيل:</b> <code>{total_uses}</code> مرة\n"
                f"🚫 <b>عدد المحظورين:</b> <code>{len(banned_users)}</code>\n"
                f"⚡ <b>حالة البوت:</b> {'🟢 يعمل' if is_bot_enabled() else '🔴 متوقف'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
                
            bot.send_message(chat_id, txt, parse_mode="HTML")
            show_admin_panel(chat_id)
        return

    # 2. فحص الحظر والإيقاف للمستخدمين العاديين
    if not is_admin(user_id):
        if is_banned(user_id):
            send_banned_msg(chat_id)
            return
        if not is_bot_enabled():
            send_bot_disabled(chat_id)
            return

    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass

    if data in ("main_menu", "cancel_to_menu"):
        bot.clear_step_handler_by_chat_id(chat_id)
        show_main_menu(chat_id)
    elif data == "collect_points":
        start_collect_points(chat_id)
    elif data in ("my_balance", "refresh_balance"):
        show_balance(chat_id)
    elif data == "about_bot":
        about_bot(chat_id)
    elif data in ("my_stats", "refresh_stats"):
        my_stats(chat_id)
    elif data == "developer":
        developer(chat_id)
    elif data == "contact_owner":
        contact_owner(chat_id)
    elif data.startswith("redeem_"):
        package_id = data.split("_")[1]
        api = user_sessions.get(chat_id)
        if not api or not api.token:
            bot.send_message(chat_id, "⚠️ يجب تسجيل الدخول أولاً!", parse_mode="HTML")
            show_main_menu(chat_id)
            return
        success, msg = api.redeem_units(package_id)
        bot.send_message(chat_id, msg, parse_mode="HTML")
        if success:
            show_packages_menu(chat_id)
        else:
            show_main_menu(chat_id)
    else:
        bot.send_message(chat_id, "❌ خيار غير معروف", parse_mode="HTML")
        show_main_menu(chat_id)

# ========== منع أي رسالة غريبة ==========
@bot.message_handler(func=lambda m: True)
def handle_other(message):
    if message.text and message.text.startswith("/admin"):
        return
    if not check_access(message):
        return
    show_main_menu(message.chat.id)

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 تم تشغيل بوت Twist Music!")
    print("=" * 50)
    print(f"👑 الأدمن: {ADMIN_USERNAME} (ID: {ADMIN_ID})")
    print(f"📊 المستخدمين: {len(users_data)}")
    print(f"🚫 المحظورين: {len(banned_users)}")
    print(f"⚡ حالة البوت: {'🟢 يعمل' if is_bot_enabled() else '🔴 متوقف'}")
    print("=" * 50)

    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            print("🔄 إعادة المحاولة بعد 5 ثواني...")
            time.sleep(5)