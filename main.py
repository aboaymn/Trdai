import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
from config import BOT_TOKEN
from handlers import start, button_handler, support_message_handler
from admin import (
    admin_panel,
    admin_button_handler,
    manual_vip_start,
    manual_vip_user_id,
    manual_vip_duration,
    MANUAL_VIP_USER_ID,
    MANUAL_VIP_DURATION,
    broadcast_message_handler
)
from database import db

# إعداد السجلات (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def precheckout_handler(update, context):
    """معالج التحقق من الدفع"""
    try:
        query = update.pre_checkout_query
        await query.answer(ok=True)
    except Exception as e:
        logger.error(f"خطأ في معالج التحقق من الدفع: {e}")

async def successful_payment(update, context):
    """معالج الدفع الناجح"""
    try:
        msg = update.message.successful_payment
        user_id = update.effective_user.id
        payload = msg.invoice_payload
        
        days_map = {'vip_7': 7, 'vip_30': 30, 'vip_90': 90}
        days = days_map.get(payload, 30)
        
        await db.set_vip(user_id, days)
        await db.add_payment(user_id, msg.total_amount / 100, msg.currency, payload, msg.telegram_payment_charge_id)
        
        await update.message.reply_text("✅ تم تفعيل اشتراك VIP بنجاح! 🎉")
        logger.info(f"دفع ناجح من المستخدم {user_id} للباقة {payload}")
        
    except Exception as e:
        logger.error(f"خطأ في معالج الدفع الناجح: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة الدفع. حاول لاحقاً.")

async def error_handler(update, context):
    """معالج الأخطاء العامة"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    app = Application.builder().token(BOT_TOKEN).drop_pending_updates(True).build()

    # ============ أوامر أساسية ============
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    # ============ محادثة التفعيل اليدوي VIP ============
    manual_vip_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                manual_vip_start, 
                pattern='^admin_manual_vip$'
            )
        ],
        states={
            MANUAL_VIP_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_vip_user_id)
            ],
            MANUAL_VIP_DURATION: [
                CallbackQueryHandler(
                    manual_vip_duration, 
                    pattern='^vip_dur_|^cancel_manual_vip'
                )
            ],
        },
        fallbacks=[],
    )
    app.add_handler(manual_vip_conv)

    # ============ معالجات الأزرار (ترتيب محدد!) ============
    # 1. أزرار الأدمن (استثنِ admin_manual_vip لأنه محادثة)
    app.add_handler(
        CallbackQueryHandler(
            admin_button_handler, 
            pattern='^admin_(?!manual_vip)'
        )
    )

    # 2. رسائل البث من الأدمن
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            broadcast_message_handler
        )
    )

    # 3. رسائل الدعم من المستخدمين
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            support_message_handler
        )
    )

    # 4. أزرار المستخدمين العادية (استثنِ admin_, vip_dur_, cancel_manual_vip)
    app.add_handler(
        CallbackQueryHandler(
            button_handler, 
            pattern='^(?!admin_|vip_dur_|cancel_manual_vip).*'
        )
    )

    # ============ معالجات الدفع ============
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    # ============ معالج الأخطاء ============
    app.add_error_handler(error_handler)

    logger.info("🚀 البوت يبدأ الآن...")
    app.run_polling(allowed_updates=['message', 'callback_query', 'pre_checkout_query'])

if __name__ == "__main__":
    main()
