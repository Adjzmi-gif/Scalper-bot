import os
import datetime
import asyncio
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from openai import OpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yfinance as yf
import ccxt

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = OpenAI(api_key=OPENAI_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

SYSTEM_PROMPT_V4 = """
Bertindaklah sebagai Senior Institutional Scalper, Order Flow Specialist, & Quantitative Risk Engine Bot.
Tugas utamamu adalah menganalisis data pasar otomatis secara ketat (Volume Profile, Delta Imbalance, & Net R:R Check).
Jika kondisi pasar Sideways, Spread Lebar, atau Net R:R < 1:1.5, KELUARKAN KEPUTUSAN: 🟡 WAIT (NO TRADE CLEAR).

Format Respons Wajib Bot Telegram:
---
### 🟢/🔴/🟡 [PILIH: BUY / SELL / WAIT] - {ticker_symbol}
*Waktu Rilis Sinyal: {time_stamp} WIB*
*Status Sinyal: 🟢 VALID (Kadaluarsa Otomatis dalam 3 Menit)*

1. ZONA EKSEKUSI & NET RISK-REWARD (POST-FEE):
   • Entry Area         : [Angka Presisi / Rentang]
   • Max Slippage Price : [Batas Harga Maksimal Entry]
   • Take Profit 1      : [Angka] (Quick Scalp - Net R:R min 1:1.5)
   • Take Profit 2      : [Angka] (Extended Target - Net R:R 1:2.5+)
   • Stop Loss (SL)     : [Angka Presisi] (Strict: Max 1-2% ATR Volatility)

2. LOT CALCULATOR & RISK MANAGEMENT:
   • Modal $100 - $500   : Rekomendasi [0.01 - 0.02 Lot / 1-2% Equity Crypto]
   • Modal $1.000       : Rekomendasi [0.05 Lot / 5% Equity Crypto]

3. TEMPORAL WINDOW & TIME INVALIDATION:
   • Max Hold Duration  : [10 - 25 Menit]
   • Time-Out Action    : "Jika dalam 15 menit TP1 tidak tersentuh, EXIT MANUAL/BEP."

4. AMBANG BATAS BATAL (INVALIDATION RULE):
   • "Sinyal BATAL jika dibaca >3 menit sejak waktu rilis di atas."
---
"""

def fetch_market_data():
    market_summary = []
    try:
        exchange = ccxt.binance()
        for sym in ['BTC/USDT', 'ETH/USDT']:
            ticker = exchange.fetch_ticker(sym)
            market_summary.append({"symbol": sym, "price": ticker['last'], "high": ticker['high'], "low": ticker['low'], "volume": ticker['baseVolume']})
    except Exception as e:
        print(f"Error Crypto: {e}")

    try:
        yf_tickers = {"XAUUSD (Gold)": "GC=F", "EURUSD": "EURUSD=X"}
        for name, symbol in yf_tickers.items():
            data = yf.Ticker(symbol).history(period="1d", interval="5m")
            if not data.empty:
                latest = data.iloc[-1]
                market_summary.append({"symbol": name, "price": round(latest['Close'], 2), "high": round(latest['High'], 2), "low": round(latest['Low'], 2), "volume": latest['Volume']})
    except Exception as e:
        print(f"Error YFinance: {e}")

    return market_summary

async def analyze_and_send(target_chat_id, is_manual=False):
    now_wib = datetime.datetime.now().strftime("%H:%M:%S")
    all_data = fetch_market_data()

    if not all_data:
        if is_manual:
            await bot.send_message(chat_id=target_chat_id, text="❌ Gagal mengambil data pasar saat ini.")
        return

    for asset in all_data:
        prompt_input = f"Aset: {asset['symbol']}\nHarga Saat Ini: {asset['price']}\nHigh 5m: {asset['high']}, Low 5m: {asset['low']}\nVolume: {asset['volume']}\nLakukan analisis V4. Berikan keputusan BUY / SELL / WAIT."
        try:
            formatted_system = SYSTEM_PROMPT_V4.format(ticker_symbol=asset['symbol'], time_stamp=now_wib)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": formatted_system}, {"role": "user", "content": prompt_input}],
                temperature=0.2
            )
            ai_signal = response.choices[0].message.content
            if is_manual or "🟢 BUY" in ai_signal or "🔴 SELL" in ai_signal:
                sent_msg = await bot.send_message(chat_id=target_chat_id, text=f"🚨 **SCALPING SIGNAL ({'MANUAL SCAN' if is_manual else 'AUTO SCAN'})** 🚨\n\n{ai_signal}", parse_mode="Markdown")
                asyncio.create_task(auto_expire_message(sent_msg, ai_signal))
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
    await update.message.reply_text("🟢 **Status Bot:** ONLINE & RUNNING\n⚡ **Engine:** V4 Institutional Connected", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📖 **Panduan Bot Scalper V4:**\n\nBot memindai pasar otomatis tiap 15 menit atau via `/scan`. Sinyal memiliki batas waktu kadaluarsa **3 menit**."
    await update.message.reply_text(text, parse_mode="Markdown")

async def scheduled_job():
    if CHAT_ID:
        await analyze_and_send(int(CHAT_ID), is_manual=False)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help", help_command))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_job, 'interval', minutes=15)
    scheduler.start()

    print("🚀 Bot Interaktif & Auto-Scanner Siap Berjalan...")
    app.run_polling()

if __name__ == '__main__':
    main()
  
