import asyncio
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import db
import config
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import yfinance as yf
from io import BytesIO

TEXTS = {
    'ar': {
        'welcome': "أهلاً بك في بوت التحليل الذكي! 🚀",
        'menu_crypto': "🪙 تحليل العملات",
        'menu_market': "📊 السوق والأخبار",
        'menu_forex': "💱 تحليل فوركس",
        'menu_ai': "🤖 مساعد ذكي",
        'menu_vip': "⭐ اشترك VIP",
        'menu_tasks': "🎯 المهام",
        'menu_ref': "👥 الإحالة",
        'menu_support': "💬 تواصل مع المشرف",
        'lang_btn': "🌐 اللغة / Language",
        'back': "🔙 رجوع",
        'analysis_coin': "تحليل عملة",
        'free_limit': "باقي لك {} تحليلات. اشترك VIP لتحليلات لا محدودة",
        'no_analysis': "عذراً، انتهت تحليلاتك اليومية. اشترك VIP للمزيد",
        'vip_info': "اختر الباقة:",
        'analysis_note': "⚠️ تحليل AI تعليمي وليس نصيحة مالية",
        'task_text': "🎯 المهام المتاحة:",
        'no_tasks': "لا توجد مهام حالياً.",
        'task_verify': "اضغط على 'تحقق' بعد تنفيذ المهمة",
        'task_done': "✅ تم التحقق! حصلت على {}",
        'referral_link': "رابط الإحالة الخاص بك:\n{}",
        'support_prompt': "أرسل رسالتك وسيتم إيصالها للمشرف:",
        'support_sent': "تم إرسال رسالتك للمشرف.",
    },
    'en': {
        'welcome': "Welcome to AI Analysis Bot! 🚀",
        'menu_crypto': "🪙 Crypto Analysis",
        'menu_market': "📊 Market & News",
        'menu_forex': "💱 Forex Analysis",
        'menu_ai': "🤖 AI Assistant",
        'menu_vip': "⭐ VIP Subscribe",
        'menu_tasks': "🎯 Tasks",
        'menu_ref': "👥 Referral",
        'menu_support': "💬 Contact Admin",
        'lang_btn': "🌐 اللغة / Language",
        'back': "🔙 Back",
        'analysis_coin': "Coin Analysis",
        'free_limit': "You have {} analyses left. Subscribe to VIP for unlimited",
        'no_analysis': "Sorry, you've used all free analyses. Subscribe to VIP",
        'vip_info': "Choose package:",
        'analysis_note': "⚠️ AI analysis is educational, not financial advice",
        'task_text': "🎯 Available tasks:",
        'no_tasks': "No tasks currently.",
        'task_verify': "Press 'Verify' after completing the task",
        'task_done': "✅ Verified! You received {}",
        'referral_link': "Your referral link:\n{}",
        'support_prompt': "Send your message and it will be delivered to the admin:",
        'support_sent': "Your message has been sent to the admin.",
    }
}

def get_lang_text(user_data, key):
    lang = user_data[2] if user_data else 'ar'
    return TEXTS.get(lang, TEXTS['ar']).get(key, key)

def main_menu_keyboard(lang):
    keys = [
        [InlineKeyboardButton(TEXTS[lang]['menu_crypto'], callback_data='menu_crypto')],
        [InlineKeyboardButton(TEXTS[lang]['menu_market'], callback_data='menu_market')],
        [InlineKeyboardButton(TEXTS[lang]['menu_forex'], callback_data='menu_forex')],
        [InlineKeyboardButton(TEXTS[lang]['menu_ai'], callback_data='menu_ai')],
        [InlineKeyboardButton(TEXTS[lang]['menu_vip'], callback_data='menu_vip')],
        [InlineKeyboardButton(TEXTS[lang]['menu_tasks'], callback_data='menu_tasks')],
        [InlineKeyboardButton(TEXTS[lang]['menu_ref'], callback_data='menu_ref')],
        [InlineKeyboardButton(TEXTS[lang]['menu_support'], callback_data='menu_support')],
        [InlineKeyboardButton(TEXTS[lang]['lang_btn'], callback_data='switch_lang')],
    ]
    return InlineKeyboardMarkup(keys)

def generate_chart(symbol, period="1mo"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            return None
        buf = BytesIO()
        mpf.plot(df, type='candle', style='charles', volume=False, savefig=buf)
        buf.seek(0)
        return buf
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref_id = None
    if args and args[0].startswith('ref'):
        try:
            ref_id = int(args[0].replace('ref', ''))
        except:
            pass
    await db.add_user(user.id, user.username, user.first_name, ref_id)
    user_data = await db.get_user(user.id)
    lang = user_data[2] if user_data else 'ar'
    await update.message.reply_text(TEXTS[lang]['welcome'], reply_markup=main_menu_keyboard(lang))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await start(update, context)
        return
    lang = user[2]

    if data == 'switch_lang':
        new_lang = 'en' if lang == 'ar' else 'ar'
        await db.update_language(user_id, new_lang)
        await query.edit_message_text(TEXTS[new_lang]['welcome'], reply_markup=main_menu_keyboard(new_lang))
        return

    if data == 'menu_crypto':
        btns = [
            [InlineKeyboardButton(TEXTS[lang]['analysis_coin'], callback_data='analysis_BTC-USD')],
            [InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]
        ]
        await query.edit_message_text(TEXTS[lang]['menu_crypto'], reply_markup=InlineKeyboardMarkup(btns))
        return

    if data == 'menu_market':
        await query.edit_message_text("قيد التطوير", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]]))
        return

    if data == 'menu_forex':
        await query.edit_message_text("قيد التطوير", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]]))
        return

    if data == 'menu_ai':
        await query.edit_message_text("قيد التطوير", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]]))
        return

    if data == 'menu_vip':
        packages = [
            ("أسبوعي - 20 نجمة", "vip_7", 20),
            ("شهري - 50 نجمة", "vip_30", 50),
            ("3 شهور - 130 نجمة", "vip_90", 130)
        ]
        btns = [[InlineKeyboardButton(name, callback_data=f"vip_buy_{payload}")] for name, payload, _ in packages]
        btns.append([InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')])
        await query.edit_message_text(TEXTS[lang]['vip_info'], reply_markup=InlineKeyboardMarkup(btns))
        return

    if data.startswith('vip_buy_'):
        payload = data.replace('vip_buy_', '')
        prices = {'vip_7': 20, 'vip_30': 50, 'vip_90': 130}
        price = prices.get(payload, 50)
        title = "VIP اشتراك"
        description = f"باقة {payload}"
        await context.bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("VIP", price)],
            start_parameter="vip"
        )
        return

    if data.startswith('analysis_'):
        symbol = data.split('_')[1]
        if user[5] == 0:
            count = await db.get_daily_analysis_count(user_id)
            if count <= 0:
                await query.edit_message_text(TEXTS[lang]['no_analysis'],
                                              reply_markup=InlineKeyboardMarkup([[
                                                  InlineKeyboardButton(TEXTS[lang]['menu_vip'], callback_data='menu_vip')
                                              ]]))
                return
        chart = generate_chart(symbol)
        note = TEXTS[lang]['analysis_note']
        caption = f"{note}\n\n📈 {symbol}"
        if chart:
            await context.bot.send_photo(chat_id=user_id, photo=chart, caption=caption)
        else:
            await context.bot.send_message(chat_id=user_id, text=f"عذراً، لا توجد بيانات لـ {symbol}")
        if user[5] == 0:
            await db.increment_analysis(user_id)
            remaining = await db.get_daily_analysis_count(user_id)
            await context.bot.send_message(chat_id=user_id,
                                           text=TEXTS[lang]['free_limit'].format(remaining),
                                           reply_markup=InlineKeyboardMarkup([[
                                               InlineKeyboardButton(TEXTS[lang]['menu_vip'], callback_data='menu_vip')
                                           ]]))
        return

    if data == 'menu_tasks':
        tasks = await db.get_active_tasks()
        if not tasks:
            await query.edit_message_text(TEXTS[lang]['no_tasks'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]]))
            return
        btns = []
        for t in tasks:
            title = t[1] if lang == 'ar' else t[2]
            btns.append([InlineKeyboardButton(f"{title}", callback_data=f"task_{t[0]}")])
        btns.append([InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')])
        await query.edit_message_text(TEXTS[lang]['task_text'], reply_markup=InlineKeyboardMarkup(btns))
        return

    if data.startswith('task_'):
        task_id = int(data.split('_')[1])
        await query.edit_message_text(TEXTS[lang]['task_verify'], reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تحقق", callback_data=f"verify_{task_id}")],
            [InlineKeyboardButton(TEXTS[lang]['back'], callback_data='menu_tasks')]
        ]))
        return

    if data.startswith('verify_'):
        task_id = int(data.split('_')[1])
        tasks = await db.get_active_tasks()
        task = next((t for t in tasks if t[0] == task_id), None)
        if task:
            await db.complete_task(task_id, user_id, task[4], task[5])
            await query.edit_message_text(TEXTS[lang]['task_done'].format(task[5]))
        else:
            await query.edit_message_text("المهمة غير متاحة")
        return

    if data == 'menu_ref':
        ref_code = user[7]
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start=ref{user_id}"
        await query.edit_message_text(TEXTS[lang]['referral_link'].format(link), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]]))
        return

    if data == 'menu_support':
        await query.edit_message_text(TEXTS[lang]['support_prompt'])
        context.user_data['awaiting_support'] = True
        return

    if data == 'back_main':
        await query.edit_message_text(TEXTS[lang]['welcome'], reply_markup=main_menu_keyboard(lang))
        return

async def support_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_support'):
        user_id = update.effective_user.id
        message_text = update.message.text
        await db.add_support_message(user_id, message_text)
        context.user_data['awaiting_support'] = False
        user = await db.get_user(user_id)
        lang = user[2] if user else 'ar'
        await update.message.reply_text(TEXTS[lang]['support_sent'])
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, f"📩 رسالة دعم من {user_id}:\n{message_text}")
            except:
                pass