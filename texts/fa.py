# Persian texts – full emoji style

WELCOME = """
سلام {name} عزیز 👋✨
به ROBIXA BOT خوش آمدید 🛒🚀

از منوی زیر گزینه مورد نظرتون رو انتخاب کنید:
"""

ADMIN_WELCOME = """
🛡 نسخه ROBIXA BOT: <b>{version}</b>
سلام ادمین <b>{name}</b> عزیز خوش آمدید 👑✨
"""

MAIN_MENU_USER = "🏠 منوی اصلی"
BTN_BUY = "🛒 خرید پنل"
BTN_TEST = "🎁 اکانت تست"
BTN_MY_SERVICES = "📦 سرویس‌های من"
BTN_SUPPORT = "💬 پشتیبانی"
BTN_WALLET = "💰 کیف پول"
BTN_ADMIN = "⚙️ مدیریت"

# Admin
BTN_PANELS = "🖥 پنل‌ها"
BTN_PRODUCTS = "📦 محصولات"
BTN_USERS = "👥 مدیریت کاربران"
BTN_BANKING = "💳 مدیریت بانکی"
BTN_BROADCAST = "📢 پیام همگانی"
BTN_TEXTS = "📝 تغییر متون"
BTN_BACKUP = "💾 بکاپ"
BTN_BACK = "🔙 بازگشت"

ADD_PANEL = "➕ افزودن پنل"
LIST_PANELS = "📋 لیست پنل‌ها"
PANEL_ADDED_SUCCESS = "✅ پنل با موفقیت اضافه شد و اتصال تست شد! 🎉"
PANEL_CONNECTION_FAILED = "❌ اتصال به پنل برقرار نشد:\n<code>{error}</code>"

ADD_PRODUCT = "➕ افزودن محصول"
PRODUCT_CREATED = "✅ محصول «{name}» با موفقیت ساخته شد. 🎉"

SELECT_PRODUCT = "🛒 لطفاً محصول مورد نظر را انتخاب کنید:"
PRODUCT_INFO = """
📦 <b>{name}</b>

💰 قیمت: <b>{price:,}</b> تومان
📊 حجم: {data}
⏱ مدت: {days} روز
"""
INSUFFICIENT_BALANCE = (
    "❌ موجودی شما کافی نیست.\n"
    "موجودی فعلی: <b>{balance:,}</b> تومان\n\n"
    "از بخش 💰 کیف پول موجودی خود را شارژ کنید."
)
SERVICE_CREATED = """
✅ سرویس شما با موفقیت ساخته شد! 🎉

👤 یوزرنیم:
<code>{username}</code>

🔑 پسورد:
<code>{password}</code>

🖥 آدرس پنل:
<code>{panel_url}</code>

📦 محصول: {product_name}
⏱ انقضا: {expire}
"""

TEST_ALREADY_USED = "⚠️ شما قبلاً اکانت تست ساخته‌اید.\nمحدودیت ساخت اکانت تست فعال است."
TEST_CREATED = """
🎁 اکانت تست شما آماده شد!

👤 یوزرنیم:
<code>{username}</code>

🔑 پسورد:
<code>{password}</code>

⏱ مدت تست: {days} روز
📊 حجم: {data} گیگ
"""

CANCELLED = "❌ عملیات لغو شد."
ERROR_GENERIC = "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید."
NOT_ADMIN = "⛔️ شما دسترسی ادمین ندارید."
USER_BLOCKED = "🚫 حساب شما مسدود شده است."

SUPPORT_TEXT = """
💬 پشتیبانی

برای ارتباط با پشتیبانی روی دکمه زیر کلیک کنید:
{support}
"""

# Wallet / Charge
WALLET_INFO = """
💰 <b>کیف پول شما</b>

موجودی فعلی: <b>{balance:,}</b> تومان

برای شارژ موجودی یکی از روش‌های زیر را انتخاب کنید:
"""
BTN_CHARGE = "➕ شارژ موجودی"
CHARGE_METHODS = "روش پرداخت را انتخاب کنید:"
CARD_PAYMENT_INFO = """
💳 <b>پرداخت کارت به کارت</b>

مبلغ قابل پرداخت:
<code>{amount:,}</code> تومان

{security_note}

کارت:
<code>{card_number}</code>
به نام: <b>{card_holder}</b>
{bank}

پس از واریز، <b>عکس رسید</b> را ارسال کنید.
"""
SECURITY_NOTE = (
    "⚠️ مبلغ دقیق بالا را واریز کنید (عدد امنیتی اضافه شده).\n"
    "این کار برای شناسایی سریع واریز شماست."
)
SEND_RECEIPT = "📸 لطفاً عکس رسید واریز را ارسال کنید:"
RECEIPT_RECEIVED = "✅ رسید دریافت شد.\nدر انتظار تأیید ادمین... ⏳"
RECEIPT_APPROVED = "✅ واریز شما تأیید شد!\nموجودی جدید: <b>{balance:,}</b> تومان 🎉"
RECEIPT_REJECTED = "❌ رسید شما رد شد.\nدلیل: {reason}"

# Admin banking
BANKING_MENU = "💳 مدیریت بانکی و روش‌های پرداخت"
CARD_SETTINGS = "⚙️ تنظیمات کارت به کارت"
MANAGE_CARDS = "📋 مدیریت شماره کارت‌ها"
TOGGLE_ON = "🟢 روشن"
TOGGLE_OFF = "🔴 خاموش"

# User management
USER_SEARCH = "🔍 آیدی عددی یا یوزرنیم کاربر را ارسال کنید:"
USER_NOT_FOUND = "❌ کاربر یافت نشد."
USER_INFO = """
👤 <b>اطلاعات کاربر</b>

🆔 تلگرام: <code>{telegram_id}</code>
👤 نام: {name}
🔗 یوزرنیم: @{username}
💰 موجودی: <b>{balance:,}</b> تومان
📊 وضعیت: {status}
📅 عضویت: {created}
"""
