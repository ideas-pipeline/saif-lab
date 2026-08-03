#!/bin/bash
# Fetch weekly technical data (4 years) using adjclose + run scoring engine + push
# Runs every Friday at 4 AM Riyadh — NO agent needed
# Usage: bash fetch-weekly-technical.sh

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/stocks-data.json"
SCRIPTS="$WORKSPACE/scripts"

echo "📊 تحديث البيانات الأسبوعية (adjclose)..."
echo "$(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Fetch weekly technical data
python3 << 'PYTHON'
import json, urllib.request, time, math

with open('/srv/ideas/stocks-data.json') as f:
    data = json.load(f)

def calc_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 2)

def calc_sma(prices, period):
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return None
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def calc_macd(prices, fast=12, slow=26, signal=9):
    # criteria v2.1 (2026-08-03): خط MACD يُبنى كسلسلة كاملة وخط الإشارة EMA9 حقيقية عليها
    # — يحل محل تقريب signal = macd × 0.8 القديم (كان موسوماً approximation).
    # الاصطلاح مطابق حرفياً لتنفيذ fetch-daily-extra.sh المجرب: بذرة SMA ثم k=2/(period+1).
    # تاريخ غير كافٍ لخط الإشارة → macdSignalW=None (مكوّن MACD في المحور 0/5 والمقام ثابت،
    # وشرط الانعكاس في الفلتر يفشل — الأكثر تحفظاً).
    if len(prices) < slow + signal:
        return None, None, None
    k_f, k_s = 2 / (fast + 1), 2 / (slow + 1)
    ema_f = sum(prices[:fast]) / fast
    ema_s = sum(prices[:slow]) / slow
    macd_line = []
    for i, p in enumerate(prices):
        if i >= fast:
            ema_f = p * k_f + ema_f * (1 - k_f)
        if i >= slow:
            ema_s = p * k_s + ema_s * (1 - k_s)
            macd_line.append(ema_f - ema_s)
    if len(macd_line) < signal:
        return None, None, None
    k_sig = 2 / (signal + 1)
    sig = sum(macd_line[:signal]) / signal
    for m in macd_line[signal:]:
        sig = m * k_sig + sig * (1 - k_sig)
    macd = macd_line[-1]
    return round(macd, 3), round(sig, 3), round(macd - sig, 3)

def calc_sma_slope(prices, period=200):
    if len(prices) < period + 4:
        return None
    sma_now = sum(prices[-period:]) / period
    sma_4w = sum(prices[-(period+4):-4]) / period
    if sma_4w == 0:
        return 0
    return round(((sma_now - sma_4w) / sma_4w) * 100, 2)

updated = 0
errors = 0
total = len(data['stocks'])

for i, stock in enumerate(data['stocks']):
    sym = stock.get('symbol', '')
    if not sym:
        continue

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.SR?interval=1wk&range=5y"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = json.load(urllib.request.urlopen(req, timeout=10))
        result = resp['chart']['result'][0]

        # adjclose — correct path
        adjclose_data = result.get('indicators', {}).get('adjclose', [{}])[0].get('adjclose', [])
        prices = [round(p, 2) for p in adjclose_data if p is not None]

        if len(prices) < 50:
            errors += 1
            continue

        current = prices[-1]
        sma200w = calc_sma(prices, 200)
        ema40w = calc_ema(prices, 40)
        rsi14w = calc_rsi(prices)
        macd_w, macd_sig_w, macd_hist_w = calc_macd(prices)
        slope = calc_sma_slope(prices, 200)

        stock['weeklyTechnical'] = {
            'sma200w': sma200w,
            'ema40w': ema40w,
            'rsi14w': rsi14w,
            'macdW': macd_w,
            'macdSignalW': macd_sig_w,
            'macdHistW': macd_hist_w,
            'sma200wSlope': slope,
            'currentPrice': current,
            'dataPoints': len(prices)
        }

        updated += 1

    except Exception as e:
        errors += 1

    if (i+1) % 50 == 0:
        print(f"  [{i+1}/{total}] تم {updated} | أخطاء {errors}")

    time.sleep(0.3)

from datetime import datetime, timezone, timedelta
riyadh = timezone(timedelta(hours=3))
data['weeklyTechnicalUpdated'] = datetime.now(riyadh).strftime('%Y-%m-%d %H:%M الرياض')

with open('/srv/ideas/stocks-data.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n✅ weeklyTechnical: {updated}/{total} سهم (adjclose)")
print(f"❌ أخطاء: {errors}")
PYTHON

# (إصلاح بند 6) أُزيلت النهاية الذاتية (محرك+نشر) — المنسق run-stocks-weekly.sh
# هو الوحيد الذي يقيّم وينشر مرة واحدة بعد اكتمال كل الجلب

echo ""
echo "✅ تم تحديث weeklyTechnical"
echo "$(date '+%Y-%m-%d %H:%M:%S')"
