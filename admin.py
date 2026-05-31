from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from database import db
import config

MANUAL_VIP_USER_ID, MANUAL_VIP_DURATION = range(2)

DURATIONS = {'7': 7, '30': 30, '90': 90}

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ أنت لست مشرفًا.")
        return
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ إضافة مهمة", callback_data="admin_addtask")],
        [InlineKeyboardButton("⭐ تفعيل VIP يدوي", callback_data="admin_manual_vip")],
        [InlineKeyboardButton("📢 بث رسالة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💬 الرد على الدعم", callback_data="admin_support")],
        [InlineKeyboardButton("💳 سجل الدفع", callback_data="admin_payments")],
    ]
    await update.message.reply_text("🔧 لوحة الأدمن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "admin_stats":
        await query.edit_message_text("📊 الإحصائيات قريباً...")
    elif data == "admin_addtask":
        await query.edit_message_text("➕ سيتم إضافة مهمة قريباً...")
    elif data == "admin_broadcast":
        await query.edit_message_text("📢 أرسل الرسالة التي تريد بثها:")
        context.user_data['awaiting_broadcast'] = True
    elif data == "admin_support":
        try:
            msgs = await db.get_unreplied_support()
            if not msgs:
                await query.edit_message_text("لا توجد رسائل دعم جديدة.")
            else:
                text = "\n".join([f"ID: {m[0]} | مستخدم: {m[1]} | {m[2]}" for m in msgs])
                await query.edit_message_text(text)
        except Exception as e:
            await query.edit_message_text(f"❌ خطأ: {e}")
    elif data == "admin_payments":
        await query.edit_message_text("💳 سجل الدفع قريباً...")

async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_broadcast'):
        text = update.message.text
        context.user_data['awaiting_broadcast'] = False
        await update.message.reply_text(f"✅ تم استلام رسالة البث:\n\n{text}")

async def manual_vip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📥 أرسل أيدي المستخدم الذي تريد تفعيل VIP له:")
    return MANUAL_VIP_USER_ID

async def manual_vip_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_text = update.message.text.strip()
    try:
        user_id = int(user_id_text)
    except ValueError:
        await update.message.reply_text("❌ أيدي غير صالح. أرسل رقمًا:")
        return MANUAL_VIP_USER_ID

    context.user_data['manual_vip_user_id'] = user_id
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ هذا المستخدم غير موجود في قاعدة البيانات. تأكد من أنه بدأ البوت أولاً.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("أسبوع (7 أيام)", callback_data="vip_dur_7")],
        [InlineKeyboardButton("شهر (30 يوم)", callback_data="vip_dur_30")],
        [InlineKeyboardButton("3 شهور (90 يوم)", callback_data="vip_dur_90")],
        [InlineKeyboardButton("إلغاء", callback_data="cancel_manual_vip")],
    ]
    await update.message.reply_text("⏳ اختر مدة الاشتراك:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MANUAL_VIP_DURATION

async def manual_vip_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel_manual_vip":
        await query.edit_message_text("تم الإلغاء.")
        return ConversationHandler.END

    duration_key = data.replace("vip_dur_", "")
    days = DURATIONS.get(duration_key)
    if not days:
        await query.edit_message_text("❌ مدة غير صالحة.")
        return ConversationHandler.END

    user_id = context.user_data.get('manual_vip_user_id')
    if not user_id:
        await query.edit_message_text("❌ خطأ: لم يتم العثور على أيدي المستخدم.")
        return ConversationHandler.END

    try:
        await db.set_vip(user_id, days)
        await db.add_payment(user_id, 0, "manual", f"admin_grant_{days}d", "manual")
        await query.edit_message_text(f"✅ تم تفعيل VIP للمستخدم `{user_id}` لمدة {days} يوم.")
        try:
            await context.bot.send_message(user_id, f"🎉 تم تفعيل اشتراك VIP لك لمدة {days} يوم من قبل المشرف!")
        except Exception as e:
            print(f"تعذر إرسال الإشعار: {e}")
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ في تفعيل VIP: {str(e)}")
    return ConversationHandler.END