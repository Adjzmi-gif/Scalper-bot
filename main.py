import os
import datetime
import asyncio
from threading import Thread
from flask import Flask
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yfinance as yf

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Web Server Sederhana untuk Railway
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot Online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# Ambil Data Pasar
def get_market_data():
    results = []
    assets = {
        "BTC/USDT": "BTC-USD",
        "ETH/USDT": "ETH-USD",
        "XAUUSD (Gold)": "GC=F",
        "EURUSD": "EURUSD=X"
    }
    for name, symbol in assets.items():
        try:
            df = yf.Ticker(symbol).history(period="1d", interval="5m")
            if not df.empty and len(df) >= 21:
                ema9 = df['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                ema21 = df['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
                price = df['Close'].iloc[-1]
                results.append({
                    "symbol": name,
                    "price": round(price, 2 if "USD" in name or "Gold" in name else 4),
                    "ema9": ema9,
                    "ema21": ema21
                })
        except Exception as e:
            print(f"Error {name}: {e}")
    return results

# Perintah /status
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 **Bot Aktif & Responsif!**\nServer Railway berjalan normal.", parse_mode="Markdown")

# Perintah /scan
async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 *Memindai pasar real-time...*", parse_mode="Markdown")
    now_time = datetime.datetime.now().strftime("%H:%M:%S")
    data = get_market_data()
    
    if not data:
        await update.message.reply_text("❌ Gagal mengambil data pasar.")
        return

    for item in data:
        p = item['price']
        dec = 2 if "USD" in item['symbol'] or "Gold" in item['symbol'] else 4
        
        if item['ema9'] > item['ema21']:
            act, icon = "BUY", "🟢"
            tp1, sl = round(p * 1.003, dec), round(p * 0.997, dec)
        else:
            act, icon = "SELL", "🔴"
            tp1, sl = round(p * 0.997, dec), round(p * 1.003, dec)

        msg = f"### {icon} {act} - {item['symbol']}\n*Waktu: {now_time} WIB*\n• Harga: {p}\n• TP1: {tp1}\n• SL: {sl}"
        await update.message.reply_text(msg, parse_mode="Markdown")

def main():
    # Jalankan Flask di background
    Thread(target=
