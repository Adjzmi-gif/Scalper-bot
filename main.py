def generate_technical_signal(asset, time_stamp):
    price = asset['price']
    ema9 = asset['ema9']
    ema21 = asset['ema21']
    
    # 1. Menentukan Tren berdasarkan Posisi EMA
    if ema9 > ema21:
        action = "BUY"
        icon = "🟢"
        # Menghitung Setup Beli
        entry_area = f"{price} - {round(price * 0.9995, 2 if 'USD' in asset['symbol'] or 'Gold' in asset['symbol'] else 4)}"
        tp1 = round(price * 1.003, 2 if 'USD' in asset['symbol'] or 'Gold' in asset['symbol'] else 4)
        tp2 = round(price * 1.006, 2 if 'USD' in asset['symbol'] or 'Gold' in asset['symbol'] else 4)
        sl = round(price * 0.997, 2 if 'USD' in asset['symbol'] or 'Gold' in asset['symbol'] else 4)
    else:
        action = "SELL"
        icon = "🔴"
        # Menghitung Setup Jual
        entry_area = f"{price} - {round(price * 1.0005, 2 if 'USD' in asset['symbol'] or 'Gold' in asset['symbol'] else 4)}"
        tp1 = round(price * 0.997, 2 if 'USD' in asset['symbol'] or 'Gold' in asset['symbol'] else 4)
        tp2 = round(price * 0.994, 2 if 'USD' in asset['symbol'] or 'Gold' in asset['symbol'] else 4)
        sl = round(price * 1.003, 2 if 'USD' in asset['symbol'] or 'Gold' in asset['symbol'] else 4)

    return f"""
### {icon} {action} - {asset['symbol']}
*Waktu Rilis Sinyal: {time_stamp} WIB*
*Status Sinyal: 🟢 VALID (Kadaluarsa Otomatis dalam 3 Menit)*

1. ZONA EKSEKUSI & NET RISK-REWARD:
   • Harga Saat Ini     : {price}
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
