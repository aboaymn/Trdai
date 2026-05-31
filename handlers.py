import asyncio
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from database import db
import config
import logging
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import yfinance as yf
from io import BytesIO

logger = logging.getLogger(__name__)

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
        'task_already_done': "❌ أنت أنهيت هذه المهمة بالفعل!",
        'referral_link': "رابط الإحالة الخاص بك:\n{}",
        'support_prompt': "أرسل رسالتك وسيتم إيصالها للمشرف:",
        'support_sent': "✅ تم إرسال رسالتك للمشرف.",
        'error': "❌ حدث خطأ. حاول لاحقاً."
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
        'task_already_done': "❌ You already completed this task!",
        'referral_link': "Your referral link:\n{}",
        'support_prompt': "Send your message and it will be delivered to the admin:",
        'support_sent': "✅ Your message has been sent to the admin.",
        'error': "❌ An error occurred. Try later."
    }
}

def get_lang_text(user_data, key):
    """احصل على النص بلغة المستخدم"""
    if not user_data:
        return TEXTS.get('ar', {}).get(key, key)
    lang = user_data[3]  # الفهرس الصحيح للغة
    return TEXTS.get(lang, TEXTS['ar']).get(key, key)

def main_menu_keyboard(lang):
    """إنشاء لوحة مفاتيح القائمة الرئيسية"""
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
    """توليد رسم بياني للرمز المطلوب"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            return None
        buf = BytesIO()
        mpf.plot(df, type='candle', style='charles', volume=False, savefig=buf)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"خطأ في توليد الرسم البياني: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    try:
        user = update.effective_user
        args = context.args
        ref_id = None
        
        if args and args[0].startswith('ref'):
            try:
                ref_id = int(args[0].replace('ref', ''))
            except ValueError:
                pass
        
        await db.add_user(user.id, user.username or "", user.first_name or "")
        user_data = await db.get_user(user.id)
        lang = user_data[3] if user_data else 'ar'
        
        await update.message.reply_text(
            TEXTS[lang]['welcome'], 
            reply_markup=main_menu_keyboard(lang)
        )
        logger.info(f"مستخدم جديد: {user.id}")
    except Exception as e:
        logger.error(f"خطأ في معالج start: {e}")
        await update.message.reply_text("❌ حدث خطأ. حاول من جديد.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج جميع أزرار الـ callback"""
    query = update.callback_query
    try:
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        user = await db.get_user(user_id)
        
        if not user:
            await start(update, context)
            return
        
        lang = user[3]

        # تبديل اللغة
        if data == 'switch_lang':
            new_lang = 'en' if lang == 'ar' else 'ar'
            await db.update_language(user_id, new_lang)
            await query.edit_message_text(
                TEXTS[new_lang]['welcome'], 
                reply_markup=main_menu_keyboard(new_lang)
            )
            return

        # قوائم الأقسام
        if data == 'menu_crypto':
            btns = [
                [InlineKeyboardButton("BTC-USD", callback_data='analysis_BTC-USD')],
                [InlineKeyboardButton("ETH-USD", callback_data='analysis_ETH-USD')],
                [InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]
            ]
            await query.edit_message_text(TEXTS[lang]['menu_crypto'], reply_markup=InlineKeyboardMarkup(btns))
            return

        if data == 'menu_market':
            await query.edit_message_text("📊 قيد التطوير", 
                                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]]))
            return

        if data == 'menu_forex':
            await query.edit_message_text("💱 قيد التطوير", 
                                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]]))
            return

        if data == 'menu_ai':
            await query.edit_message_text("🤖 قيد التطوير", 
                                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]]))
            return

        # باقات VIP
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

        # شراء VIP
        if data.startswith('vip_buy_'):
            payload = data.replace('vip_buy_', '')
            prices = {'vip_7': 20, 'vip_30': 50, 'vip_90': 130}
            price = prices.get(payload, 50)
            title = "اشتراك VIP"
            description = f"باقة {payload}"
            try:
                await context.bot.send_invoice(
                    chat_id=user_id,
                    title=title,
                    description=description,
                    payload=payload,
                    provider_token="",
                    currency="XTR",
                    prices=[LabeledPrice("VIP", price * 100)],
                    start_parameter="vip"
                )
            except Exception as e:
                logger.error(f"خطأ في إرسال الفاتورة: {e}")
                await query.edit_message_text("❌ حدث خطأ في الدفع. حاول لاحقاً.")
            return

        # التحليل
        if data.startswith('analysis_'):
            symbol = data.split('_')[1]
            is_vip = await db.is_user_vip(user_id)
            
            # تحقق من التحليلات المتبقية للمستخدمين العاديين
            if not is_vip:
                remaining = await db.get_daily_analysis_count(user_id)
                if remaining <= 0:
                    await query.edit_message_text(
                        TEXTS[lang]['no_analysis'],
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(TEXTS[lang]['menu_vip'], callback_data='menu_vip')
                        ]])
                    )
                    return
            
            # توليد الرسم البياني
            chart = generate_chart(symbol)
            note = TEXTS[lang]['analysis_note']
            caption = f"{note}\n\n📈 {symbol}"
            
            if chart:
                await context.bot.send_photo(chat_id=user_id, photo=chart, caption=caption)
            else:
                await context.bot.send_message(chat_id=user_id, text=f"عذراً، لا توجد بيانات لـ {symbol}")
            
            # قلل التحليلات للمستخدمين العاديين
            if not is_vip:
                await db.increment_analysis(user_id)
                remaining = await db.get_daily_analysis_count(user_id)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=TEXTS[lang]['free_limit'].format(remaining),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(TEXTS[lang]['menu_vip'], callback_data='menu_vip')
                    ]])
                )
            return

        # المهام
        if data == 'menu_tasks':
            tasks = await db.get_active_tasks()
            if not tasks:
                await query.edit_message_text(
                    TEXTS[lang]['no_tasks'], 
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]])
                )
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
            await query.edit_message_text(
                TEXTS[lang]['task_verify'], 
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ تحقق", callback_data=f"verify_{task_id}")],
                    [InlineKeyboardButton(TEXTS[lang]['back'], callback_data='menu_tasks')]
                ])
            )
            return

        if data.startswith('verify_'):
            task_id = int(data.split('_')[1])
            tasks = await db.get_active_tasks()
            task = next((t for t in tasks if t[0] == task_id), None)
            
            if task:
                # تحقق من أن المستخدم لم ينهِ المهمة من قبل
                already_done = await db.has_completed_task(user_id, task_id)
                if already_done:
                    await query.edit_message_text(TEXTS[lang]['task_already_done'])
                    return
                
                success = await db.complete_task(task_id, user_id, task[4], task[5])
                if success:
                    await query.edit_message_text(TEXTS[lang]['task_done'].format(task[5]))
                else:
                    await query.edit_message_text(TEXTS[lang]['task_already_done'])
            else:
                await query.edit_message_text("❌ المهمة غير متاحة")
            return

        # الإحالة
        if data == 'menu_ref':
            bot_username = (await context.bot.get_me()).username
            link = f"https://t.me/{bot_username}?start=ref{user_id}"
            await query.edit_message_text(
                TEXTS[lang]['referral_link'].format(link), 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_main')]])
            )
            return

        # الدعم
        if data == 'menu_support':
            await query.edit_message_text(TEXTS[lang]['support_prompt'])
            context.user_data['awaiting_support'] = True
            return

        # رجوع للقائمة الرئيسية
        if data == 'back_main':
            await query.edit_message_text(TEXTS[lang]['welcome'], reply_markup=main_menu_keyboard(lang))
            return

    except Exception as e:
        logger.error(f"خطأ في معالج الأزرار: {e}")
        try:
            await query.answer(TEXTS.get('ar', {}).get('error', '❌ حدث خطأ'), show_alert=True)
        except:
            pass

async def support_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج رسائل الدعم"""
    try:
        if context.user_data.get('awaiting_support'):
            user_id = update.effective_user.id
            message_text = update.message.text
            
            await db.add_support_message(user_id, message_text)
            context.user_data['awaiting_support'] = False
            
            user = await db.get_user(user_id)
            lang = user[3] if user else 'ar'
            
            await update.message.reply_text(TEXTS[lang]['support_sent'])
            
            # أرسل الإشعار للمشرفين
            for admin_id in config.ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id, 
                        f"📩 رسالة دعم من {user_id}:\n\n{message_text}"
                    )
                except Exception as e:
                    logger.warning(f"خطأ في إرسال الإشعار للمشرف {admin_id}: {e}")
                    
    except Exception as e:
        logger.error(f"خطأ في معالج رسائل الدعم: {e}")
