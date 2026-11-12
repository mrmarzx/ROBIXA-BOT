# ROBIXA BOT v2.1.512 – Persian UI (reseller / نمایندگی)

WELCOME = """
سلام <b>{name}</b> عزیز 👋✨

به <b>ROBIXA BOT</b> خوش آمدید 🛒🚀
فروشگاه نمایندگی پنل‌های <b>Rebecca · Marzban · PasarGuard</b>

از منوی زیر انتخاب کنید:
"""

MAIN_MENU_USER = "🏠 منوی اصلی"

BTN_BUY = "🛒 خرید نمایندگی"
BTN_TEST = "🎁 نمایندگی تست"
BTN_MY_SERVICES = "📦 نمایندگی‌های من"
BTN_SUPPORT = "💬 پشتیبانی"
BTN_WALLET = "💰 کیف پول"
BTN_ADMIN = "⚙️ مدیریت"

BTN_PANELS = "🖥 پنل‌ها"
BTN_PRODUCTS = "📦 محصولات"
BTN_USERS = "👥 مدیریت کاربران"
BTN_BANKING = "💳 مدیریت بانکی"
BTN_BROADCAST = "📢 پیام همگانی"
BTN_TEXTS = "📝 تغییر متون"
BTN_BACKUP = "💾 بکاپ"
BTN_STATS = "📊 آمار"
BTN_BACK = "🔙 بازگشت"

BTN_CHARGE = "➕ شارژ موجودی"
BTN_WALLET_BACK = "🔙 بازگشت به کیف پول"

NOT_ADMIN = "⛔️ شما دسترسی ادمین ندارید."
USER_BLOCKED = "🚫 حساب شما مسدود شده است."
USER_NOT_FOUND = "❌ کاربر یافت نشد."
ERROR_GENERIC = "❌ خطایی رخ داد. دوباره تلاش کنید."
INSUFFICIENT_BALANCE = "❌ موجودی کافی نیست.\nموجودی فعلی: <b>{balance:,}</b> تومان"
CANCELLED = "❌ لغو شد."

SUPPORT_TEXT = """
💬 <b>پشتیبانی</b>

برای ارتباط با پشتیبانی روی دکمه زیر بزنید:
"""

WALLET_INFO = """
💰 <b>کیف پول شما</b>

موجودی: <b>{balance:,}</b> تومان
"""

CHARGE_METHODS = "روش شارژ را انتخاب کنید:"

SECURITY_NOTE = "\n⚠️ مبلغ امنیتی تصادفی اضافه شده — دقیقاً همین مبلغ را واریز کنید."
CARD_PAYMENT_INFO = """
💳 <b>پرداخت کارت‌به‌کارت</b>

مبلغ قابل پرداخت: <b>{amount:,}</b> تومان{security_note}

شماره کارت:
<code>{card_number}</code>
به نام: {card_holder}{bank}

پس از واریز، رسید (عکس) را ارسال کنید.
"""
SEND_RECEIPT = "📷 لطفاً عکس رسید واریز را ارسال کنید."
RECEIPT_RECEIVED = "✅ رسید دریافت شد و برای بررسی به ادمین ارسال شد."

PANEL_ADDED_SUCCESS = "✅ پنل با موفقیت اضافه شد و اتصال تست شد! 🎉"
PANEL_CONNECTION_FAILED = "❌ اتصال به پنل برقرار نشد:\n<code>{error}</code>"

SERVICE_CREATED = """
✅ <b>نمایندگی شما فعال شد!</b> 🎉

👤 یوزرنیم ادمین:
<code>{username}</code>

🔑 پسورد:
<code>{password}</code>

🖥 ورود به داشبورد:
{dashboard_url}

📦 پلن: {product_name}
⏱ انقضا: {expire}
📊 حجم پلن: {data_limit}

⚠️ این حساب <b>نمایندگی (ادمین غیرسودو)</b> است.
با این مشخصات وارد داشبورد شوید و کاربران خود را بسازید و مدیریت کنید.
"""

TEST_ALREADY_USED = "⚠️ شما قبلاً نمایندگی تست گرفته‌اید.\nمحدودیت زمانی هنوز فعال است."
TEST_CREATED = """
🎁 <b>نمایندگی تست آماده شد</b>

👤 یوزرنیم:
<code>{username}</code>

🔑 پسورد:
<code>{password}</code>

🖥 داشبورد:
{dashboard_url}

⏱ اعتبار: {days} روز
"""

MY_SERVICES_EMPTY = "📦 هنوز نمایندگی فعالی ندارید."
MY_SERVICE_ITEM = """
{status} <b>{username}</b>{test_tag}
🔑 <code>{password}</code>
🖥 {dashboard}
⏱ انقضا: {expire}
📊 حجم: {data_limit} GB
"""

EXPIRED_NOTIFY = """
⚠️ <b>نمایندگی شما منقضی شد</b>

👤 <code>{username}</code>

ادمین نمایندگی و کاربران فعال آن غیرفعال شدند.
برای تمدید روی دکمه زیر بزنید و از موجودی کیف پول استفاده کنید.
"""

RENEW_SUCCESS = """
✅ <b>نمایندگی تمدید شد</b>

👤 <code>{username}</code>
⏱ انقضای جدید: {expire}
📊 حجم پلن: {data_limit} GB

ادمین و کاربرانی که سیستم قبلاً خاموش کرده بود دوباره فعال شدند.
"""

RENEW_NO_BALANCE = "❌ موجودی برای تمدید کافی نیست."
RENEW_NO_PRODUCT = "❌ محصول مرتبط یافت نشد."
PASSWORD_CHANGED = "✅ پسورد نمایندگی با موفقیت تغییر کرد.\nپسورد جدید: <code>{password}</code>"

BANKING_MENU = "💳 مدیریت بانکی و درگاه‌ها"


ADMIN_WELCOME = """
⚙️ <b>پنل مدیریت ROBIXA</b>
نسخه: <code>{version}</code>
سلام {name} 👋

از منوی زیر بخش مورد نظر را انتخاب کنید.
"""


PRODUCT_CREATED = "✅ محصول <b>{name}</b> با موفقیت اضافه شد."
