import asyncio
from telegram import Bot

# Tambahkan fungsi ini di atas main()
async def auto_job(application: ApplicationBuilder):
    # Ganti dengan Chat ID Telegram kamu (bisa berupa angka chat pribadi atau ID grup)
    target_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not target_chat_id:
        print("TELEGRAM_CHAT_ID belum diset di environment variables!")
        return
    
    bot = Bot(token=TELEGRAM_TOKEN)
    data = get_comprehensive_market_data()
    
    if data:
        for item in data:
            p = item['price']
            ema9 = item['ema9']
            ema21 = item['ema21']
            rsi = item['rsi']
            atr = item['atr']
            dec = 2 if "USD" in item['symbol'] or "Gold" in item['symbol'] else 4

            if ema9 > ema21 and rsi < 70:
                action, icon, bias = "BUY", "🟢", "Bullish Momentum"
                tp1 = round(p + (atr * 1.5), dec)
                sl = round(p - (atr * 1.5), dec)
            elif ema9 < ema21 and rsi > 30:
                action, icon, bias = "SELL", "🔴", "Bearish Momentum"
                tp1 = round(p - (atr * 1.5), dec)
                sl = round(p + (atr * 1.5), dec)
            else:
                continue # Kalau pasaran WAIT / Konsolidasi, bot tidak spam chat otomatis

            now_time = datetime.datetime.now().strftime("%H:%M:%S")
            msg = f"""🚨 **AUTO SCALPING SIGNAL** 🚨
### {icon} {action} - {item['symbol']}
*Waktu: {now_time} WIB*
• **Bias Tren:** {bias} | **RSI:** {rsi}
• **Harga Running:** {p}
• **Take Profit (TP):** {tp1}
• **Stop Loss (SL):** {sl}
"""
            await bot.send_message(chat_id=target_chat_id, text=msg, parse_mode="Markdown")

def main():
    # Jalankan Flask Server di Background Thread
    Thread(target=run_flask, daemon=True).start()

    # Inisialisasi Bot Telegram
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("scan", scan_command))
    
    # ── SETTING AUTO SCHEDULER (OTOMATIS KIRIM INFO) ──
    scheduler = AsyncIOScheduler()
    # Atur interval waktu otomatis (Contoh: Setiap 15 menit sekali)
    scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(auto_job(app), app.bot.loop), 'interval', minutes=15)
    scheduler.start()
    # --------------------------------------------------

    print("🚀 Bot Siap Berjalan Otomatis...")
    app.run_polling(drop_pending_updates=True)
    
