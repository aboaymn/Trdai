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
import logging

logger = logging.getLogger(__name__)

MANUAL_VIP_USER_ID, MANUAL_VIP_DURATION = range(2)
DURATIONS = {'7': 7, '30': 30, '90': 90}

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة الأدمن الرئيسية"""
    try:
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
    except Exception as e:
        logger.error(f"خطأ في لوحة الأدمن: {e}")
        await update.message.reply_text("❌ حدث خطأ.")

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الأدمن"""
    query = update.callback_query
    try:
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        
        if user_id not in config.ADMIN_IDS:
            await query.answer("❌ لا تملك صلاحيات", show_alert=True)
            return

        if data == "admin_stats":
            # احصل على الإحصائيات
            all_users = await db.get_all_users()
            stats_text = f"📊 إحصائيات البوت:\n\n👥 عدد المستخدمين: {len(all_users)}"
            await query.edit_message_text(stats_text)
            
        elif data == "admin_addtask":
            await query.edit_message_text("➕ يتم العمل على هذه الميزة...")
            
        elif data == "admin_broadcast":
            await query.edit_message_text("📢 أرسل الرسالة التي تريد بثها:")
            context.user_data['awaiting_broadcast'] = True
            
        elif data == "admin_support":
            try:
                msgs = await db.get_unreplied_support()
                if not msgs:
                    await query.edit_message_text("✅ لا توجد رسائل دعم جديدة.")
                else:
                    text = "📩 رسائل الدعم الجديدة:\n\n"
                    for m in msgs:
                        text += f"🆔 {m[0]} | من: {m[1]}\n📝 {m[2]}\n\n"
                    await query.edit_message_text(text[:4096])  # حد أقصى للرسالة
            except Exception as e:
                logger.error(f"خطأ في الحصول على رسائل الدعم: {e}")
                await query.edit_message_text(f"❌ خطأ: {e}")
                
        elif data == "admin_payments":
            await query.edit_message_text("💳 يتم العمل على هذه الميزة...")
            
    except Exception as e:
        logger.error(f"خطأ في معالج أزرار الأدمن: {e}")
        await query.answer("❌ حدث خطأ", show_alert=True)

async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج رسائل البث"""
    try:
        if context.user_data.get('awaiting_broadcast'):
            user_id = update.effective_user.id
            
            if user_id not in config.ADMIN_IDS:
                await update.message.reply_text("❌ لا تملك صلاحيات البث")
                return
            
            text = update.message.text
            context.user_data['awaiting_broadcast'] = False
            
            # احصل على جميع المستخدمين
            all_users = await db.get_all_users()
            
            if not all_users:
                await update.message.reply_text("❌ لا توجد مستخدمين للبث.")
                return
            
            success_count = 0
            fail_count = 0
            
            await update.message.reply_text(f"📢 جاري البث للـ {len(all_users)} مستخدم...")
            
            for user_row in all_users:
                try:
                    await context.bot.send_message(user_row[0], text)
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    logger.warning(f"خطأ في الإرسال للمستخدم {user_row[0]}: {e}")
            
            result_text = f"✅ اكتمل البث!\n\n✔️ نجح: {success_count}\n❌ فشل: {fail_count}"
            await update.message.reply_text(result_text)
    except Exception as e:
        logger.error(f"خطأ في معالج البث: {e}")
        await update.message.reply_text(f"❌ خطأ في البث: {e}")

async def manual_vip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء محادثة التفعيل اليدوي للـ VIP"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in config.ADMIN_IDS:
        await query.answer("❌ لا تملك صلاحيات", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    await query.edit_message_text("📥 أرسل أيدي المستخدم الذي تريد تفعيل VIP له:")
    return MANUAL_VIP_USER_ID

async def manual_vip_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال أيدي المستخدم"""
    try:
        user_id_text = update.message.text.strip()
        try:
            user_id = int(user_id_text)
        except ValueError:
            await update.message.reply_text("❌ أيدي غير صالح. أرسل رقمًا صحيحًا:")
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
        
    except Exception as e:
        logger.error(f"خطأ في استقبال أيدي المستخدم: {e}")
        await update.message.reply_text(f"❌ خطأ: {e}")
        return ConversationHandler.END

async def manual_vip_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال مدة الاشتراك وتفعيل VIP"""
    query = update.callback_query
    try:
        await query.answer()
        data = query.data

        if data == "cancel_manual_vip":
            await query.edit_message_text("❌ تم الإلغاء.")
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
            await db.add_payment(user_id, 0, "manual", f"admin_grant_{days}d", "manual_grant")
            
            await query.edit_message_text(f"✅ تم تفعيل VIP للمستخدم `{user_id}` لمدة {days} يوم.")
            
            try:
                await context.bot.send_message(
                    user_id, 
                    f"🎉 تم تفعيل اشتراك VIP لك لمدة {days} يوم من قبل المشرف!"
                )
            except Exception as e:
                logger.warning(f"تعذر إرسال الإشعار للمستخدم {user_id}: {e}")
                
        except Exception as e:
            logger.error(f"خطأ في تفعيل VIP: {e}")
            await query.edit_message_text(f"❌ خطأ في تفعيل VIP: {str(e)}")
            
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"خطأ في معالج مدة الـ VIP: {e}")
        await query.answer("❌ حدث خطأ", show_alert=True)
        return ConversationHandler.END
