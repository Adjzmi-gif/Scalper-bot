import os
import datetime
import asyncio
from threading import Thread
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yfinance as yf

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

# Mini Web Server untuk menjaga Railway / Render tetap aktif
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot Scalper V4 (Pure Technical) is Alive and Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

def fetch_market_data():
    market_summary = []
    # Menggunakan Yahoo Finance untuk semua Aset (Crypto, Forex, Emas) agar lolos blokir IP US
    assets = {
        "BTC/USDT": "BTC-USD",
        "ETH/USDT": "ETH-USD",
        "XAUUSD (Gold)": "GC=F",
        "EURUSD": "EURUSD=X"
    }

    for name, symbol in assets.items():
        try:
            data = yf.Ticker(symbol).history(period="1d", interval="5m")
            if not data.empty and len(data) >= 20:
                # Perhitungan Sederhana EMA 9 dan EMA 21
                data['EMA9'] = data['Close'].ewm(span=9, adjust=False).mean()
                data['EMA21'] = data['Close'].ewm(span=21, adjust=False).mean()
                
                latest = data.iloc[-1]
                prev = data.iloc[-2]
                
                market_summary.append({
                    "symbol": name,
                    "price": round(latest['Close'], 2 if "USD" in name or "Gold" in name else 4),
                    "high": round(latest['High'], 2),
                    "low": round(latest['Low'], 2),
                    "ema9": latest['EMA9'],
                    "ema21": latest['EMA21'],
                    "prev_ema9": prev['EMA9'],
                    "prev_ema21": prev['EMA21'],
                })
        except Exception as e:
            print(f"Error fetching {name}: {e}")

    return market_summary

def generate_technical_signal(asset, time_stamp):
    price = asset['price']
    ema9 = asset['ema9']
    ema21 = asset['ema21']
    prev_ema9 = asset['prev_ema9']
    prev_ema21 = asset['prev_ema21']
    
    # Logika Indikator Crossover EMA (Bullish / Bearish)
    if prev_ema9 <= prev_ema21 and ema9 > ema21:
        action = "BUY"
        icon = "🟢"
        entry_area = f"{price} - {round(price * 0.999, 2)}"
        tp1 = round(price * 1.003, 2)
        tp2 = round(price * 1.006, 2)
        sl = round(price * 0.997, 2)
    elif prev_ema9 >= prev_ema21 and ema9 < ema21:
        action = "SELL"
        icon = "🔴"
        entry_area = f"{price} - {round(price * 1.001, 2)}"
        tp1 = round(price * 0.997, 2)
        tp2 = round(price * 0.994, 2)
        sl = round(price * 1.003, 2)
    else:
        action = "WAIT"
        icon = "🟡"

    if action == "WAIT":
        return f"""
### 🟡 WAIT (NO TRADE CLEAR) - {asset['symbol']}
*Waktu Rilis Sinyal: {time_stamp} WIB*
*Status: Pasaran Konsolidasi / Belum Ada Momentum Crossover EMA.*
"""

    return f"""
### {icon} {action} - {asset['symbol']}
*Waktu Rilis Sinyal: {time_stamp} WIB*
*Status Sinyal: 🟢 VALID (Kadaluarsa Otomatis dalam 3 Menit)*

1. ZONA EKSEKUSI & NET RISK-REWARD:
   • Entry Area         : {entry_area}
   • Take Profit 1      : {tp1} (Quick Scalp)
   • Take Profit 2      : {tp2} (Extended Target)
   • Stop Loss (SL)     : {sl} (Strict Risk)

2. LOT CALCULATOR & RISK MANAGEMENT:
   • Modal $100 - $500   : Rekomendasi 0.01 - 0.02 Lot / 1-2% Equity
   • Modal $1.000       : Rekomendasi 0.05 Lot / 5% Equity

3. TEMPORAL WINDOW & TIME INVALIDATION:
   • Max Hold Duration  : 10 - 25 Menit
   • Time-Out Action    : "Jika dalam 15 menit TP1 tidak tersentuh, EXIT MANUAL/BEP."

4. AMBANG BATAS BATAL (INVALIDATION RULE):
   • "Sinyal BATAL jika dibaca >3 menit sejak waktu rilis di atas."
"""

async def analyze_and_send(target_chat_id, is_manual=False):
    now_wib = datetime.datetime.now().strftime("%H:%M:%S")
    all_data = fetch_market_data()
    
    if not all_data:
        if is_manual:
            await bot.send_message(chat_id=target_chat_id, text="❌ Gagal mengambil data pasar saat ini.")
        return

    for asset in all_data:
        try:
            signal_text = generate_technical_signal(asset, now_wib)
            
            # Jika scan manual atau jika ada sinyal BUY / SELL otomatis
            if is_manual or "🟢 BUY" in signal_text or "🔴 SELL" in signal_text:
                sent_msg = await bot.send_message(
                    chat_id=target_chat_id, 
                    text=f"🚨 **SCALPING SIGNAL ({'MANUAL SCAN' if is_manual else 'AUTO SCAN'})** 🚨\n{signal_text}", 
                    parse_mode="Markdown"
                )
                if "🟢 BUY" in signal_text or "🔴 SELL" in signal_text:
                    asyncio.create_task(auto_expire_message(sent_msg, signal_text))
        except Exception as e:
            print(f"Error processing {asset['symbol']}: {e}")

async def auto_expire_message(message, original_text):
    await asyncio.sleep(180)
    expired_text = "🔴 **[SINYAL EXPIRED / KADALUARSA]**\n⚠️ *Batas waktu eksekusi 3 menit habis. DILARANG ENTRY!*\n\n~~" + original_text[:250] + "..." + "~~"
    try:
        await message.edit_text(expired_text, parse_mode="Markdown")
    except Exception:
        pass

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🤖 **INSTITUTIONAL SCALPER BOT V4**\n\nGunakan menu perintah berikut:\n/scan - Pemindaian pasar instan\n/status - Cek kesehatan bot\n/help - Panduan penggunaan"
    await update.message.reply_text(text, parse_mode="Markdown")

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("🔍 *Memindai Multi-Market secara instan...*", parse_mode="Markdown")
    await analyze_and_send(chat_id, is_manual=True)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 **Status Bot:** ONLINE & RUNNING\n⚡ **Engine:** Technical Indicator Engine (Pure & Fast)", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📖 **Panduan Bot Scalper V4:**\n\nBot memindai pasar otomatis tiap 15 menit atau via `/scan`. Sinyal memiliki batas waktu kadaluarsa **3 menit**."
    await update.message.reply_text(text, parse_mode="Markdown")

async def scheduled_job():
    if CHAT_ID:
        await analyze_and_send(int(CHAT_ID), is_manual=False)

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help", help_command))
    
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(scheduled_job, 'interval', minutes=15)
    scheduler.start()
    
    print("🚀 Bot Interaktif & Auto-Scanner Siap Berjalan...")
    app.run_polling()

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()
    run_telegram_bot()
