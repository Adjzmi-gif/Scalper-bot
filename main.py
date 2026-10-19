import os
import datetime
from threading import Thread
from flask import Flask
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yfinance as yf

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Web Server Flask untuk Railway
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Scalper Bot V4.2 Online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# Fungsi Ambil Data Pasar & Analisis Multi-Indikator
def get_comprehensive_market_data():
    results = []
    assets = {
        "BTC/USDT": "BTC-USD",
        "ETH/USDT": "ETH-USD",
        "XAUUSD (Gold)": "GC=F",
        "EURUSD": "EURUSD=X"
    }
    
    for name, symbol in assets.items():
        try:
            # Ambil data candle 5m
            df = yf.Ticker(symbol).history(period="2d", interval="5m")
            if not df.empty and len(df) >= 30:
                # 1. EMA 9 & 21
                df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
                df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
                
                # 2. RSI 14 Sederhana
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                # 3. ATR 14 Sederhana untuk Volatilitas / SL TP Dinamis
                high_low = df['High'] - df['Low']
                high_close = (df['High'] - df['Close'].shift()).abs()
                low_close = (df['Low'] - df['Close'].shift()).abs()
                true_range = max(high_low.iloc[-1], high_close.iloc[-1], low_close.iloc[-1])
                
                latest = df.iloc[-1]
                results.append({
                    "symbol": name,
                    "price": round(latest['Close'], 2 if "USD" in name or "Gold" in name else 4),
                    "ema9": latest['EMA9'],
                    "ema21": latest['EMA21'],
                    "rsi": round(latest['RSI'], 2) if not pd_isna(latest['RSI']) else 50.0,
                    "atr": round(true_range, 2 if "USD" in name or "Gold" in name else 4)
                })
        except Exception as e:
            print(f"Error fetching {name}: {e}")
    return results

def pd_isna(val):
    import math
    return math.isnan(val)

# Perintah /status
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 **Bot Status:** ONLINE & STABLE\n⚡ *Technical Engine Ready*", parse_mode="Markdown")

# Perintah /scan (Penyempurnaan Analisis Menyeluruh)
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 *Memindai Multi-Market & Menghitung Indikator...*", parse_mode="Markdown")
    now_time = datetime.datetime.now().strftime("%H:%M:%S")
    
    data = get_comprehensive_market_data()
    if not data:
        await update.message.reply_text("❌ Gagal mengambil data pasar saat ini. Coba beberapa saat lagi.")
        return

    for item in data:
        p = item['price']
        ema9 = item['ema9']
        ema21 = item['ema21']
        rsi = item['rsi']
        atr = item['atr']
        dec = 2 if "USD" in item['symbol'] or "Gold" in item['symbol'] else 4

        # Logika Sempurna: EMA Crossover + Filter RSI
        if ema9 > ema21 and rsi < 70:
            action, icon, bias = "BUY", "🟢", "Bullish Momentum"
            tp1 = round(p + (atr * 1.5), dec)
            tp2 = round(p + (atr * 3.0), dec)
            sl = round(p - (atr * 1.5), dec)
        elif ema9 < ema21 and rsi > 30:
            action, icon, bias = "SELL", "🔴", "Bearish Momentum"
            tp1 = round(p - (atr * 1.5), dec)
            tp2 = round(p - (atr * 3.0), dec)
            sl = round(p + (atr * 1.5), dec)
        else:
            action, icon, bias = "WAIT", "🟡", "Konsolidasi / Zona Ekstrem (Risky)"
            tp1, tp2, sl = "-", "-", "-"

        if action == "WAIT":
            msg = f"""### {icon} {action} - {item['symbol']}
*Waktu: {now_time} WIB*
• **Analisis:** {bias} (RSI: {rsi})
• **Rekomendasi:** Tahan dulu, belum ada momentum valid."""
        else:
            msg = f"""### {icon} {action} - {item['symbol']}
*Waktu: {now_time} WIB*

📊 **MATRIKS ANALISIS TEKNIKAL:**
• **Bias Tren:** {bias}
• **RSI (14):** {rsi}
• **ATR Volatilitas:** {atr}

🎯 **ZONA EKSEKUSI & TARGET:**
• **Harga Running:** {p}
• **Take Profit 1 (TP1):** {tp1}
• **Take Profit 2 (TP2):** {tp2}
• **Stop Loss (SL):** {sl}

⚠️ *Gunakan manajemen risiko ketat (Maks 1-2% modal).*"""

        await update.message.reply_text(msg, parse_mode="Markdown")

def main():
    # Jalankan Flask Server di Background Thread
    Thread(target=run_flask, daemon=True).start()

    # Inisialisasi Bot Telegram dengan Proteksi Drop Pending Updates (Anti-Freeze)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("scan", scan_command))
    
    print("🚀 Bot Siap Berjalan Sempurna...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
    
