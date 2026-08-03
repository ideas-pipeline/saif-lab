#!/bin/bash
# fetch-market-regime.sh — فلتر نظام السوق (TASI vs SMA200D + Breadth)
# مصدر يومي: SAHMK (طلب واحد) | تأسيس تاريخي: Yahoo مرة واحدة
python3 << 'PYEOF'
import json, urllib.request, os
from datetime import datetime

KEY_FILE  = '/srv/ideas/.sahmk.key'
HIST_FILE = '/srv/ideas/tasi-history.json'
DATA_FILE = '/srv/ideas/stocks-data.json'

api_key = open(KEY_FILE).read().strip()

# ── تأسيس التاريخ من Yahoo (مرة واحدة) ──
if not os.path.exists(HIST_FILE):
    print("⏳ تأسيس تاريخ TASI من Yahoo (سنتان)...")
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETASI.SR?interval=1d&range=2y"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    r = json.load(urllib.request.urlopen(req, timeout=15))['chart']['result'][0]
    ts = r['timestamp']; closes = r['indicators']['quote'][0]['close']
    hist = [{"date": datetime.fromtimestamp(t).strftime('%Y-%m-%d'), "close": round(c,2)}
            for t,c in zip(ts,closes) if c is not None]
    json.dump({"data": hist}, open(HIST_FILE,'w'))
    print(f"✅ تم التأسيس: {len(hist)} يوم")

hist = json.load(open(HIST_FILE))['data']

# ── قراءة اليوم من SAHMK ──
req = urllib.request.Request("https://app.sahmk.sa/api/v1/market/summary/?index=TASI",
                             headers={"X-API-Key": api_key, "User-Agent": "Mozilla/5.0"})
s = json.load(urllib.request.urlopen(req, timeout=10))
day = s['timestamp'][:10]
val = s['index_value']

# إضافة/تحديث بدون تكرار
if hist and hist[-1]['date'] == day:
    hist[-1]['close'] = val
else:
    hist.append({"date": day, "close": val})
json.dump({"data": hist}, open(HIST_FILE,'w'))

# ── الحساب ──
closes = [h['close'] for h in hist]
sma200      = sum(closes[-200:]) / min(200, len(closes))
sma200_prev = sum(closes[-220:-20]) / min(200, len(closes[:-20])) if len(closes) > 220 else sma200
slope   = (sma200 - sma200_prev) / sma200_prev * 100
pct_vs  = (val - sma200) / sma200 * 100
adv, dec = s['advancing'], s['declining']
breadth = adv / dec if dec else 1.0

if val > sma200 and slope > 0:
    regime, icon, advice = "صاعد", "🟢", "بيئة داعمة — مراكز كاملة"
elif val > sma200 or (pct_vs > -2 and breadth > 0.9):
    regime, icon, advice = "حذر", "🟡", "بيئة مختلطة — نصف مركز وتدرّج"
else:
    regime, icon, advice = "هابط", "🔴", "بيئة ضاغطة — الأفضلية للانتظار"

# ── الكتابة في بيانات الموقع ──
prev_close = closes[-2] if len(closes) >= 2 else val
data = json.load(open(DATA_FILE))
data['marketRegime'] = {
    "date": day, "indexValue": val,
    "prevClose": round(prev_close, 2),
    "change": round(val - prev_close, 2),
    "changePct": round((val - prev_close) / prev_close * 100, 2),
    "sma200d": round(sma200,2), "pctVsSma": round(pct_vs,2),
    "smaSlope": round(slope,2), "advancing": adv, "declining": dec,
    "breadth": round(breadth,2), "mood": s['market_mood'],
    "regime": regime, "icon": icon, "advice": advice
}
json.dump(data, open(DATA_FILE,'w'), indent=2, ensure_ascii=False)

print(f"{icon} نظام السوق: {regime} | TASI {val:,.0f} ({pct_vs:+.1f}% من SMA200) | ميل {slope:+.2f}% | عرض {adv}↑/{dec}↓")
print(f"   → {advice}")
PYEOF
