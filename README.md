# ROBIXA BOT v2.0.0

ربات فروشگاهی تلگرام چندپنله برای **Rebecca**، **Marzban** و **PasarGuard**  
با کیف پول، کارت‌به‌کارت، **زرین‌پال**، مانیتور انقضا و **بکاپ خودکار**.

مخزن: https://github.com/mrmarzx/ROBIXA-BOT

---

## نصب یک‌خطی (سرور لینوکس)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mrmarzx/ROBIXA-BOT/2.0/install.sh)
```

یا:

```bash
wget -qO- https://raw.githubusercontent.com/mrmarzx/ROBIXA-BOT/2.0/install.sh | bash
```

کلون دستی:

```bash
git clone https://github.com/mrmarzx/ROBIXA-BOT.git
cd ROBIXA-BOT
bash install.sh
```

### جریان نصب
1. تشخیص نصب قبلی → سؤال **Y/N** برای پاک‌سازی کامل  
2. دریافت **آیدی عددی ادمین**  
3. دریافت **توکن BotFather**  
4. ساخت venv + نصب پکیج‌ها + نوشتن `.env` + دستور `robixa`

---

## مدیریت ترمینال

```bash
robixa
```

منوی CLI:
1. Uninstall کامل  
2. تنظیم آیدی ادمین  
3. لاگ (Error / All)  
4. Start bot  
5. Status  

---

## اجرا

```bash
cd ~/ROBIXA-BOT   # یا مسیر نصب
source venv/bin/activate
python main.py
```

برای اجرا در پس‌زمینه (systemd اختیاری):

```bash
# مثال ساده با nohup
nohup python main.py > data/robixa.log 2>&1 &
```

---

## پنل‌ها

| پنل | احراز هویت | نکات |
|-----|------------|------|
| **REBECCA** | User/Pass یا JWT | سازگار با API شبیه Marzban |
| **MARZBAN** | User/Pass → `/api/admin/token` | `POST /api/user` |
| **PASARGUARD** | **X-Api-Key** (الزامی) | `POST /api/admin/users` + group_ids |

### افزودن پنل
مدیریت → پنل‌ها → افزودن → انتخاب نوع → نام → آدرس → یوزر/پس → توکن/API Key → **تست اتصال خودکار**

- برای PasarGuard حتماً کلید `X-Api-Key` را وارد کنید (از منوی API Keys پنل).
- برای Marzban/Rebecca می‌توانید فقط یوزر و پس ادمین بدهید (توکن با `-`).

---

## پرداخت

- **کارت به کارت**: چند کارت، مبلغ امنیتی تصادفی، رسید عکس، تأیید/رد ادمین  
- **زرین‌پال**: Merchant ID در مدیریت بانکی → لینک پرداخت → دکمه «پرداخت کردم» → وریفای خودکار و شارژ کیف پول  

فعال‌سازی زرین‌پال: مدیریت → بانکی → زرین‌پال → Merchant ID + فعال‌سازی.

---

## بکاپ خودکار

- هر **۲۴ ساعت** (قابل تنظیم با `backup_interval_hours`) یک zip از `data/` و `.env` ساخته و برای ادمین‌ها ارسال می‌شود.
- دکمه **بکاپ** در منوی ادمین: بکاپ دستی فوری.
- فایل‌ها در `data/backups/` ذخیره می‌شوند.

برای ریستور دستی:
```bash
# توقف ربات، سپس
unzip -o data/backups/robixa_backup_XXXX.zip -d .
# سپس دوباره اجرا
```

---

## ساختار پروژه

```
ROBIXA-BOT/
├── install.sh          # نصب‌کننده تعاملی + one-liner
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── panels/
│   ├── rebecca.py
│   ├── marzban.py
│   ├── pasarguard.py
│   └── factory.py      # create / disable / test یکپارچه
├── payments/
│   └── zarinpal.py     # v4 request + verify
├── handlers/
│   ├── admin.py
│   ├── user.py
│   └── common.py
├── database/
│   ├── models.py
│   └── db.py
├── utils/
│   ├── generators.py   # HHabVI... / PASS--HH----#D...
│   ├── expire.py       # غیرفعال‌سازی سرویس منقضی
│   └── backup.py       # بکاپ خودکار و دستی
├── keyboards/
├── texts/
└── scripts/robixa      # CLI مدیریت
```

---

## نیازمندی‌ها

- Python **3.10+**
- دسترسی اینترنت (API پنل‌ها + زرین‌پال + تلگرام)
- لینوکس (توصیه‌شده برای production)

---

## لایسنس

MIT
