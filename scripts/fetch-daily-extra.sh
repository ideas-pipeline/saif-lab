#!/bin/bash
# fetch-daily-extra.sh — كاتب البيانات اليومية (dailyExtra + relativeStrength + dailyTechnical)
# المرحلة 0: يكتب نفس المفاتيح الموجودة حصراً + ختم updatedAt لكل كتلة
# لا rsTasi12m ولا zscores هنا (مرحلة 3 — قرار منهجية)
#
# قرار موثق (مطلوب اعتماده): العوائد return3m/6m/12m تُحسب من adjclose
# (ذاتي الشفاء ضد التقسيمات، يشمل التوزيعات = عائد شبه كلي)
# بينما المؤشرات الفنية (ATR, RSI, EMA) من close/high/low الخام
# ومقارنة TASI من tasi-history.json (سعري) — انظر CHANGELOG
#
# الاستخدام: bash fetch-daily-extra.sh DATA_FILE
# لا مسار افتراضي — يرفض العمل بلا معامل صريح (حماية من الكتابة على الإنتاج سهواً)

DATA_FILE="${1:?خطأ: مطلوب مسار ملف البيانات صراحةً}"

python3 - "$DATA_FILE" << 'PYCODE'
import json, urllib.request, urllib.error, time, sys
from datetime import datetime, timezone

DATA_FILE = sys.argv[1]
STAMP = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

with open(DATA_FILE) as f:
    data = json.load(f)

# --- عوائد TASI من التاريخ المحلي (سعري) ---
with open('/srv/ideas/tasi-history.json') as f:
    tasi = json.load(f)['data']
tasi_closes = [d['close'] for d in tasi]

def period_return(closes, days):
    # days = أيام تداول تقريبية: 3م=63، 6م=126، 12م=250
    if len(closes) < days + 1:
        return None
    old, cur = closes[-(days+1)], closes[-1]
    if not old:
        return None
    return round((cur - old) / old * 100, 2)

tasi_r3 = period_return(tasi_closes, 63)
tasi_r6 = period_return(tasi_closes, 126)
tasi_r12 = period_return(tasi_closes, 250)
print(f"TASI: 3م {tasi_r3}% | 6م {tasi_r6}% | 12م {tasi_r12}%")

# --- مؤشرات فنية ---
def calc_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 4)

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        ch = prices[i] - prices[i-1]
        gains.append(max(ch, 0)); losses.append(max(-ch, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period-1) + gains[i]) / period
        avg_l = (avg_l * (period-1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - 100 / (1 + rs), 1)

def calc_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow + signal:
        return None, None, None
    k_f, k_s = 2/(fast+1), 2/(slow+1)
    ema_f = sum(prices[:fast]) / fast
    ema_s = sum(prices[:slow]) / slow
    macd_line = []
    for i, p in enumerate(prices):
        if i >= fast:
            ema_f = p*k_f + ema_f*(1-k_f)
        if i >= slow:
            ema_s = p*k_s + ema_s*(1-k_s)
            macd_line.append(ema_f - ema_s)
    if len(macd_line) < signal:
        return None, None, None
    k_sig = 2/(signal+1)
    sig = sum(macd_line[:signal]) / signal
    for m in macd_line[signal:]:
        sig = m*k_sig + sig*(1-k_sig)
    macd = macd_line[-1]
    return round(macd, 4), round(sig, 4), round(macd - sig, 4)

def calc_atr(highs, lows, closes, period=14):
    n = len(closes)
    if n < period + 1 or len(highs) != n or len(lows) != n:
        return None
    trs = []
    for i in range(1, n):
        trs.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr*(period-1) + tr) / period
    return round(atr, 4)

def fetch_chart(sym, retries=2):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.SR?interval=1d&range=1y"
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.load(urllib.request.urlopen(req, timeout=15))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            if attempt < retries:
                time.sleep(2 * (attempt + 1))  # backoff: 2ث ثم 4ث
            else:
                return None

updated = errors = 0
total = len(data['stocks'])

for i, stock in enumerate(data['stocks']):
    sym = stock.get('symbol', '')
    if not sym:
        continue
    resp = fetch_chart(sym)
    if resp is None:
        errors += 1
        print(f"  ✗ {sym}: فشل الجلب بعد المحاولات")
        continue
    try:
        result = resp['chart']['result'][0]
        q = result['indicators']['quote'][0]
        adj = result['indicators'].get('adjclose', [{}])[0].get('adjclose', [])
        rows = [(c, h, l, v, a) for c, h, l, v, a in
                zip(q['close'], q['high'], q['low'], q['volume'], adj)
                if c is not None and h is not None and l is not None]
        if len(rows) < 60:
            errors += 1
            continue
        closes = [r[0] for r in rows]
        highs  = [r[1] for r in rows]
        lows   = [r[2] for r in rows]
        vols   = [r[3] or 0 for r in rows]
        adjcls = [r[4] if r[4] is not None else r[0] for r in rows]

        price = closes[-1]
        high52 = round(max(highs), 2)
        low52 = round(min(lows), 2)
        atr = calc_atr(highs, lows, closes)
        atr_pct = round(atr / price * 100, 2) if atr and price else None
        avg20 = int(sum(vols[-20:]) / 20) if len(vols) >= 20 else None
        avg50 = int(sum(vols[-50:]) / 50) if len(vols) >= 50 else None
        ema50 = calc_ema(closes, 50)
        rsi14 = calc_rsi(closes)
        macd_d, macd_sig_d, macd_hist_d = calc_macd(closes)

        stock['dailyExtra'] = {
            'high52w': high52, 'low52w': low52,
            'atr14': atr, 'atrPct': atr_pct,
            'avgVol20': avg20, 'avgVol50': avg50,
            'ema50d': round(ema50, 2) if ema50 else None,
            'rsi14d': rsi14,
            'updatedAt': STAMP
        }
        stock['dailyTechnical'] = {
            'ema50d': ema50, 'rsi14d': rsi14,
            'macdD': macd_d, 'macdSignalD': macd_sig_d, 'macdHistD': macd_hist_d,
            'atr14': atr, 'atrPct': atr_pct,
            'high52w': high52, 'low52w': low52,
            'avgVol20d': avg20, 'avgVol50d': avg50,
            'updatedAt': STAMP
        }

        # العوائد من adjclose (قرار موثق أعلاه)
        r3  = period_return(adjcls, 63)
        r6  = period_return(adjcls, 126)
        r12 = period_return(adjcls, 250)
        rs = {'return3m': r3, 'return6m': r6, 'return12m': r12, 'updatedAt': STAMP}
        if r3 is not None and tasi_r3 is not None:
            rs['rsTasi3m'] = round(r3 - tasi_r3, 2)
        if r6 is not None and tasi_r6 is not None:
            rs['rsTasi6m'] = round(r6 - tasi_r6, 2)
        stock['relativeStrength'] = rs

        updated += 1
    except (KeyError, IndexError, TypeError):
        errors += 1
    if (i + 1) % 25 == 0:
        print(f"  ... {i+1}/{total}")
    time.sleep(0.35)

# --- إعادة حساب sectorMedians (كتلة يتيمة رابعة — اكتشاف 2026-07-04) ---
import statistics
sectors = {}
for s in data['stocks']:
    sec = s.get('sector')
    if not sec:
        continue
    agg = sectors.setdefault(sec, {'pe': [], 'pb': [], 'dy': [], 'r6': [], 'n': 0})
    agg['n'] += 1
    v = s.get('valuation', {})
    if v.get('pe') and v['pe'] > 0: agg['pe'].append(v['pe'])
    if v.get('pb') and v['pb'] > 0: agg['pb'].append(v['pb'])
    if v.get('dividendYield') and v['dividendYield'] > 0: agg['dy'].append(v['dividendYield'])
    r6 = s.get('relativeStrength', {}).get('return6m')
    if r6 is not None: agg['r6'].append(r6)

data['sectorMedians'] = {
    sec: {
        'peMedian': round(statistics.median(a['pe']), 2) if a['pe'] else None,
        'pbMedian': round(statistics.median(a['pb']), 2) if a['pb'] else None,
        'divYieldMedian': round(statistics.median(a['dy']), 4) if a['dy'] else None,
        'ret6mMedian': round(statistics.median(a['r6']), 2) if a['r6'] else None,
        'count': a['n'],
    } for sec, a in sectors.items()
}
data['sectorMediansUpdated'] = STAMP

with open(DATA_FILE, 'w') as f:
    json.dump(data, f, indent=1, ensure_ascii=False)

print(f"\n✅ dailyExtra/relativeStrength/dailyTechnical: {updated}/{total} سهم | أخطاء: {errors}")
print(f"✅ sectorMedians: {len(data['sectorMedians'])} قطاعاً أعيد حسابها")
PYCODE
