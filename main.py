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

async def precheckout_handler(update, context):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update, context):
    msg = update.message.successful_payment
    user_id = update.effective_user.id
    payload = msg.invoice_payload
    days_map = {'vip_7': 7, 'vip_30': 30, 'vip_90': 90}
    days = days_map.get(payload, 30)
    await db.set_vip(user_id, days)
    await db.add_payment(user_id, msg.total_amount, msg.currency, payload, msg.telegram_payment_charge_id)
    await update.message.reply_text("✅ تم تفعيل اشتراك VIP بنجاح!")

def main():
    app = Application.builder().token(BOT_TOKEN).drop_pending_updates(True).build()

    # أوامر أساسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    # أزرار الأدمن العامة – نستثني admin_manual_vip لأن المحادثة تتولاه
    app.add_handler(CallbackQueryHandler(admin_button_handler, pattern='^admin_(?!manual_vip)'))

    # محادثة التفعيل اليدوي VIP
    manual_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(manual_vip_start, pattern='^admin_manual_vip$', per_message=True)],
        states={
            MANUAL_VIP_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_vip_user_id)],
            MANUAL_VIP_DURATION: [CallbackQueryHandler(manual_vip_duration, pattern='^vip_dur_|^cancel_manual_vip', per_message=True)],
        },
        fallbacks=[],
    )
    app.add_handler(manual_conv)

    # أزرار المستخدمين – نستثني أي شيء يبدأ بـ admin_ أو vip_dur_ أو cancel_manual_vip
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(?!admin_|vip_dur_|cancel_manual_vip).*'))

    # رسائل الدعم
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, support_message_handler))

    # بث رسالة الأدمن (يُستخدم فقط عند تفعيل awaiting_broadcast)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message_handler))

    # الدفع
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    app.run_polling()

if __name__ == "__main__":
    main()