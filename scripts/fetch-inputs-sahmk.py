#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch-inputs-sahmk.py — جالب مدخلات المختبر المباشر من واجهة سهمك (sahmk-direct-v1)
=================================================================================
القرار: استقلال المختبر نهائياً عن مزامنة المشروع الأصلي — هذا السكربت يبني/يحدّث
stocks-data.json بعقد الحقول القائم نفسه (docs/platform-anatomy.md §3) بحيث يعمل عليه
scripts/scoring-engine.py (criteria v2.1) بلا أي تعديل.

التشغيل
-------
    SAHMK_KEY=xxxx python3 scripts/fetch-inputs-sahmk.py --data stocks-data.json
    python3 scripts/fetch-inputs-sahmk.py --data stocks-data.json --key-file /path/.sahmk.key

    الأوضاع:
      (افتراضي)          يومي: أسعار + شموع 1d (فنية يومية + قوة نسبية) + TASI + نظام السوق
      --weekly           يضيف: شموع 1w (weeklyTechnical) + الأساسيات (ratios/company/dividends)
      --symbols 1010,2222  حصر التشغيل برموز محددة (للاختبار المحدود)
      --probe-financials   تجربة 8 تركيبات معاملات على /financials/ لرمزين وطباعة أول
                           تركيبة تنجح مع شجرة مفاتيحها — ثم خروج (لحل الـ400)
      --tasi-history PATH  مسار ملف تاريخ TASI (افتراضي: tasi-history.json بجوار --data)

المفتاح: متغير البيئة SAHMK_KEY أو --key-file. يُمنع منعاً باتاً وضعه في الكود أو المستودع.

ميزانية الطلبات (تُحسب وتُطبع قبل التشغيل — الحصة 5000/يوم)
-----------------------------------------------------------
    يومي  (248 سهماً): quotes 5 دفعات + historical-1d 248 + TASI 1 + summary 1  ≈ 255
    أسبوعي (--weekly): + historical-1w 248 + ratios 248 + company 248 + dividends 248 ≈ 1247
    ملاحظة: تقدير المنسق «الأسبوعي +248» غطى الشموع فقط؛ الأساسيات لا بد أن تُجلب
    دورياً فضُمت لوضع --weekly (إيقاع الإنتاج القائم للماليات) — القرار موثق.

عقود سهمك المؤكدة بالفحص الفعلي (scripts/sahmk-probe.py — لا اجتهاد خلافها)
--------------------------------------------------------------------------
    القاعدة: https://api.sahmk.sa/api/v1 بترويسة X-API-Key
    /quotes/?identifiers=A,B (دفعات 50): ask/bid/change/change_percent/high/low/name/
        net_liquidity/price/symbol/updated_at/volume + is_delayed — لا previous_close
        (يُشتق: price − change بتقريب هللة)
    /historical/{sym}/?interval=1d|1w&from=&to=: شموع adjusted_close/close/date/high/low/
        open/turnover/volume — historical/TASI يعمل (تاريخ المؤشر)
    /analytics/ratios/{sym}/?history=latest&period=annual&metrics=all:
        ratios.roe/roa/net_margin/operating_margin/debt_to_equity
        key_metrics.total_revenue/operating_income/total_debt
        لا cost_to_income ولا EV/EBITDA ولا current_ratio
    /company/{sym}/: fundamentals (basic_eps/beta/book_value/…/forward_pe والأرجح
        pe_ratio/price_to_book/market_cap/shares_outstanding)
    /financials/{sym}/?history=latest: يعيد 400 — يُحل بوضع --probe-financials
    /dividends/{sym}/: trailing_12m_yield + history بتواريخ الاستحقاق
    /market/summary/: index_value/advancing/declining/market_mood

ما يبقى مفتوحاً (لا يُختلق — الغياب null والمحرك يتعامل معه كعادته)
------------------------------------------------------------------
    - /financials 400: يمنع currentRatio وcashflow.ocf ومصروفات البنوك — بعد حل
      التركيبة بوضع --probe-financials تُضاف خطوة جلبها.
    - Cost/Income للبنوك: operating_income == total_revenue في ratios (لا تفصيل
      مصروفات) → sectorFinancials.costToIncome = null (المفتاح حاضر لمسار البنوك
      في المحرك، والقيمة الغائبة = 0 نقاط كقاعدة الغياب).
    - EV/EBITDA وP/E: يُخزنان كمدخلات حية في valuationInputs فقط — خارج مقام
      المحرك (criteria v2.1) حتى قرار تفعيل موسوم من المالك. P/B وعائد التوزيعات
      يمران عبر المسار القائم: valuationInputs ← compute-valuation.py (بحارس الاتساق).
    - مقياس debt_to_equity (نسبة أم ٪) غير مؤكد من الفحص: كشف آلي عبر وسيط القيم
      المقطعي (وسيط < 10 → نسبة فتُضرب ×100 لعقد المحرك؛ وإلا تُعتمد ٪ كما هي)
      — القرار يُطبع بصوت عالٍ ويُختم في _labNote، ويُراجع يدوياً في أول تشغيلة.

السلوك — بوابات الفشل (مراجعة الناقد 2026-08-03):
    - فشل TASI الحاكم (عوائد 3م/6م غير قابلة للحساب) = إجهاض بخروج 1 قبل أي كتابة
      للملف الرئيسي — وإلا خسرت كل الأسهم rsTasi3m/6m (7/11 من الزخم) بصمت.
    - عتبة الفشل >10% لأي نوع بيانات تُفحص قبل الكتابة — الملف لا يُكتب أصلاً عندها.
    - سقوط adjusted_close→close معدود ومعلن؛ وقوعه في 1w = إنذار اصطلاح صريح
      (ملحق 24-07: ترحيل السلسلة الأسبوعية إلى خام يستلزم وسم نسخة معايير).
    - مقياس D/E يُحسم على الكون الكامل فقط ويثبَّت في data.deScaleDecision؛ وضع
      --symbols يقرأ القرار المثبت أو يرفض التطبيق بإنذار.
    - company.current_price غير مؤكد بالفحص: غيابه = pbConsistent=None («غير قابل
      للتحقق» لا «فاشل») مع عدّ صريح وتحذير حاكم إن غاب في >50% من الردود.
    - weeklyTechnical تحمل updatedAt لكل سهم — الخلط الأسبوعي الجزئي موسوم.
    - كتابة ذرية (tmp ثم os.replace)، لا كتابة إن فشل جلب الأسعار كلياً.
خط الإنتاج المختبري بعده: compute-valuation.py ← scoring-engine.py.
"""
import json, os, sys, time, argparse, tempfile
import urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta

BASE = "https://api.sahmk.sa/api/v1"
RIYADH = timezone(timedelta(hours=3))

# ═══════════════════════════════════════════════════════════════════
# دوال المؤشرات النقية — اصطلاحات المشروع حرفياً:
#   الأسبوعية: fetch-weekly-technical.sh (المصلح — MACD بإشارة EMA9 حقيقية)
#   اليومية:   fetch-daily-extra.sh (RSI Wilder، ATR Wilder، MACD سلسلة)
# مختبرة على بيانات حقيقية — انظر docs/implementation-notes.md
# ═══════════════════════════════════════════════════════════════════

def calc_sma(prices, period):
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)


def calc_ema(prices, period, dp=2):
    """EMA ببذرة SMA لأول period ثم k=2/(period+1) — الاصطلاح القائم في السكربتين"""
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return round(ema, dp)


def calc_rsi_simple(prices, period=14):
    """RSI أسبوعي — متوسطات بسيطة لآخر period فرقاً (اصطلاح fetch-weekly-technical.sh)"""
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
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


def calc_rsi_wilder(prices, period=14):
    """RSI يومي — تنعيم Wilder (اصطلاح fetch-daily-extra.sh)"""
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        ch = prices[i] - prices[i - 1]
        gains.append(max(ch, 0)); losses.append(max(-ch, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - 100 / (1 + rs), 1)


def calc_macd(prices, fast=12, slow=26, signal=9, dp=4):
    """MACD كسلسلة كاملة + خط إشارة EMA9 حقيقي ببذرة SMA — الاصطلاح الموحد
    (fetch-daily-extra.sh القائم = fetch-weekly-technical.sh بعد إصلاح criteria v2.1).
    dp=4 لليومي، dp=3 للأسبوعي."""
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
    return round(macd, dp), round(sig, dp), round(macd - sig, dp)


def calc_atr(highs, lows, closes, period=14):
    """ATR بتنعيم Wilder على True Range الكامل (اصطلاح fetch-daily-extra.sh)"""
    n = len(closes)
    if n < period + 1 or len(highs) != n or len(lows) != n:
        return None
    trs = []
    for i in range(1, n):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return round(atr, 4)


def calc_sma_slope(prices, period=200, lag=4):
    """ميل SMA200W: مقارنة بالمتوسط قبل lag أسابيع (اصطلاح fetch-weekly-technical.sh)"""
    if len(prices) < period + lag:
        return None
    sma_now = sum(prices[-period:]) / period
    sma_prev = sum(prices[-(period + lag):-lag]) / period
    if sma_prev == 0:
        return 0
    return round(((sma_now - sma_prev) / sma_prev) * 100, 2)


def period_return(closes, days):
    """عائد فترة بأيام تداول: 3م=63، 6م=126، 12م=250 (اصطلاح fetch-daily-extra.sh)"""
    if len(closes) < days + 1:
        return None
    old, cur = closes[-(days + 1)], closes[-1]
    if not old:
        return None
    return round((cur - old) / old * 100, 2)


def regime_from_history(closes, index_value, advancing, declining, mood):
    """نظام السوق — معادلات fetch-market-regime.sh حرفياً"""
    sma200 = sum(closes[-200:]) / min(200, len(closes))
    sma200_prev = sum(closes[-220:-20]) / min(200, len(closes[:-20])) if len(closes) > 220 else sma200
    slope = (sma200 - sma200_prev) / sma200_prev * 100
    pct_vs = (index_value - sma200) / sma200 * 100
    breadth = advancing / declining if declining else 1.0
    if index_value > sma200 and slope > 0:
        regime, icon, advice = "صاعد", "🟢", "بيئة داعمة — مراكز كاملة"
    elif index_value > sma200 or (pct_vs > -2 and breadth > 0.9):
        regime, icon, advice = "حذر", "🟡", "بيئة مختلطة — نصف مركز وتدرّج"
    else:
        regime, icon, advice = "هابط", "🔴", "بيئة ضاغطة — الأفضلية للانتظار"
    return {
        "sma200d": round(sma200, 2), "pctVsSma": round(pct_vs, 2),
        "smaSlope": round(slope, 2), "advancing": advancing, "declining": declining,
        "breadth": round(breadth, 2), "mood": mood,
        "regime": regime, "icon": icon, "advice": advice,
    }


# ═══════════════════════════════════════════════════════════════════
# الشبكة — معزولة عن الحسابات
# ═══════════════════════════════════════════════════════════════════

class Api:
    def __init__(self, key):
        self.key = key
        self.requests_made = 0

    def get(self, path, tries=3, timeout=25):
        """GET مع إعادة محاولة وتراجع تصاعدي — يعيد (json, None) أو (None, وصف_الخطأ)"""
        url = BASE + path
        err = "unknown"
        for attempt in range(tries):
            self.requests_made += 1
            try:
                req = urllib.request.Request(url, headers={
                    "X-API-Key": self.key, "User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.load(resp), None
            except urllib.error.HTTPError as e:
                err = "HTTP %d" % e.code
                if e.code in (400, 401, 403, 404):
                    return None, err      # لا جدوى من الإعادة
            except Exception as e:
                err = type(e).__name__
            if attempt < tries - 1:
                time.sleep(2 * (attempt + 1))
        return None, err


def rows_of(resp, *keys):
    """تفكيك مرن لغلاف الاستجابة: قائمة مباشرة أو dict بمفتاح معروف — وإلا []"""
    if resp is None:
        return []
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for k in keys:
            v = resp.get(k)
            if isinstance(v, list):
                return v
    return []


def key_tree(obj, depth=3, indent=""):
    """شجرة مفاتيح للاستكشاف (وضع --probe-financials)"""
    lines = []
    if depth < 0:
        return lines
    if isinstance(obj, dict):
        for k, v in obj.items():
            t = type(v).__name__
            lines.append("%s%s (%s)" % (indent, k, t))
            if isinstance(v, (dict, list)):
                lines += key_tree(v, depth - 1, indent + "  ")
    elif isinstance(obj, list) and obj:
        lines.append("%s[%d عنصراً — الأول:]" % (indent, len(obj)))
        lines += key_tree(obj[0], depth - 1, indent + "  ")
    return lines


# ═══════════════════════════════════════════════════════════════════
# مراحل الجلب
# ═══════════════════════════════════════════════════════════════════

def fetch_quotes(api, stocks, counters, now_str):
    by = {s["symbol"]: s for s in stocks}
    syms = list(by.keys())
    got = {}
    for i in range(0, len(syms), 50):
        batch = syms[i:i + 50]
        resp, err = api.get("/quotes/?identifiers=" + ",".join(batch))
        if resp is None:
            counters["quotes_batch_fail"] += 1
            print("  ✗ دفعة quotes %d-%d: %s" % (i, i + len(batch), err))
        else:
            for q in rows_of(resp, "quotes", "data", "results"):
                if q.get("symbol"):
                    got[str(q["symbol"])] = q
        time.sleep(1)
    for sym, st in by.items():
        q = got.get(sym)
        price = q.get("price") if q else None
        if not price or price <= 0:
            counters["quotes_fail"] += 1
            continue
        st["currentPrice"] = round(price, 2)
        ch = q.get("change")
        if ch is not None:
            # لا previous_close في الواجهة — يُشتق (عقد الفحص المؤكد)
            prev = round(price - ch, 2)
            st["previousClose"] = prev
            cp = q.get("change_percent")
            if cp is not None:
                st["dailyChange"] = round(cp, 2)
            elif prev > 0:
                st["dailyChange"] = round((round(price, 2) - prev) / prev * 100, 2)
        nl = q.get("net_liquidity")
        if nl is not None:
            st["netLiquidity"] = nl
        st["priceUpdatedAt"] = now_str
        st["priceSource"] = "sahmk"
        counters["quotes_ok"] += 1
    return counters["quotes_ok"]


def parse_candles(resp):
    """شموع historical: date/open/high/low/close/adjusted_close/volume — مرتبة تصاعدياً.
    يعيد (rows, adj_fallback) حيث adj_fallback = عدد الصفوف التي سقطت من adjusted_close
    إلى close (غياب المعدل) — سقوطها في 1w يمس اصطلاح SMA200W الملزم (ملحق 24-07)
    فيُعدّ ويُنذر به صراحة، لا صامتاً."""
    rows = rows_of(resp, "data", "candles", "history", "results")
    out = []
    adj_fallback = 0
    for r in rows:
        if r.get("close") is None or r.get("high") is None or r.get("low") is None:
            continue
        adj = r.get("adjusted_close")
        if adj is None:
            adj = r["close"]
            adj_fallback += 1
        out.append((r.get("date", ""), r["close"], r["high"], r["low"],
                    r.get("volume") or 0, adj))
    out.sort(key=lambda x: x[0])
    return out, adj_fallback


def fetch_daily(api, stocks, counters, tasi_returns, stamp):
    d420 = (datetime.now(timezone.utc) - timedelta(days=420)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for i, st in enumerate(stocks):
        sym = st["symbol"]
        resp, err = api.get("/historical/%s/?interval=1d&from=%s&to=%s" % (sym, d420, today))
        rows, adj_fb = parse_candles(resp)
        if adj_fb:
            counters["adj_fb_rows_1d"] += adj_fb
            counters["adj_fb_syms_1d"] += 1
        # نافذة سنة تداول: آخر 251 شمعة (اصطلاح fetch-daily-extra range=1y مع ضمان عائد 12م)
        rows = rows[-251:]
        if len(rows) < 60:
            counters["daily_fail"] += 1
            print("  ✗ %s شموع يومية: %s (%d شمعة)" % (sym, err or "قليلة", len(rows)))
            continue
        closes = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]
        vols = [r[4] for r in rows]
        adjcls = [r[5] for r in rows]

        price = closes[-1]
        high52 = round(max(highs), 2)
        low52 = round(min(lows), 2)
        atr = calc_atr(highs, lows, closes)
        atr_pct = round(atr / price * 100, 2) if atr and price else None
        avg20 = int(sum(vols[-20:]) / 20) if len(vols) >= 20 else None
        avg50 = int(sum(vols[-50:]) / 50) if len(vols) >= 50 else None
        ema50 = calc_ema(closes, 50, dp=4)
        rsi14 = calc_rsi_wilder(closes)
        macd_d, macd_sig_d, macd_hist_d = calc_macd(closes, dp=4)

        st["dailyExtra"] = {
            "high52w": high52, "low52w": low52,
            "atr14": atr, "atrPct": atr_pct,
            "avgVol20": avg20, "avgVol50": avg50,
            "ema50d": round(ema50, 2) if ema50 else None,
            "rsi14d": rsi14,
            "updatedAt": stamp,
        }
        st["dailyTechnical"] = {
            "ema50d": ema50, "rsi14d": rsi14,
            "macdD": macd_d, "macdSignalD": macd_sig_d, "macdHistD": macd_hist_d,
            "atr14": atr, "atrPct": atr_pct,
            "high52w": high52, "low52w": low52,
            "avgVol20d": avg20, "avgVol50d": avg50,
            "updatedAt": stamp,
        }
        # العوائد من adjusted_close (القرار الموثق في fetch-daily-extra.sh)
        r3 = period_return(adjcls, 63)
        r6 = period_return(adjcls, 126)
        r12 = period_return(adjcls, 250)
        rs = {"return3m": r3, "return6m": r6, "return12m": r12, "updatedAt": stamp}
        if r3 is not None and tasi_returns.get("3m") is not None:
            rs["rsTasi3m"] = round(r3 - tasi_returns["3m"], 2)
        if r6 is not None and tasi_returns.get("6m") is not None:
            rs["rsTasi6m"] = round(r6 - tasi_returns["6m"], 2)
        st["relativeStrength"] = rs
        counters["daily_ok"] += 1
        if (i + 1) % 25 == 0:
            print("  ... %d/%d يومي" % (i + 1, len(stocks)))
        time.sleep(0.15)


def fetch_weekly(api, stocks, counters, stamp):
    d5y = (datetime.now(timezone.utc) - timedelta(days=1826)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for i, st in enumerate(stocks):
        sym = st["symbol"]
        resp, err = api.get("/historical/%s/?interval=1w&from=%s&to=%s" % (sym, d5y, today))
        rows, adj_fb = parse_candles(resp)
        if adj_fb:
            counters["adj_fb_rows_1w"] += adj_fb
            counters["adj_fb_syms_1w"] += 1
        prices = [round(r[5], 2) for r in rows]   # adjusted_close (اصطلاح SMA200W المعتمد — ملحق 24-07)
        if len(prices) < 50:
            counters["weekly_fail"] += 1
            print("  ✗ %s شموع أسبوعية: %s (%d)" % (sym, err or "قليلة", len(prices)))
            continue
        macd_w, macd_sig_w, macd_hist_w = calc_macd(prices, dp=3)
        st["weeklyTechnical"] = {
            "sma200w": calc_sma(prices, 200),
            "ema40w": calc_ema(prices, 40, dp=2),
            "rsi14w": calc_rsi_simple(prices),
            "macdW": macd_w,
            "macdSignalW": macd_sig_w,
            "macdHistW": macd_hist_w,
            "sma200wSlope": calc_sma_slope(prices, 200),
            "currentPrice": prices[-1],
            "dataPoints": len(prices),
            # ختم لكل سهم (شرط الناقد م-3): الخلط الأسبوعي الجزئي يصبح موسوماً على مستوى الكتلة
            "updatedAt": stamp,
        }
        counters["weekly_ok"] += 1
        if (i + 1) % 25 == 0:
            print("  ... %d/%d أسبوعي" % (i + 1, len(stocks)))
        time.sleep(0.15)


def fetch_fundamentals(api, stocks, counters, today, full_universe, stored_de_decision):
    """ratios + company + dividends — أسبوعي.
    مقياس D/E: يُحسم مقطعياً على الكون الكامل فقط (م-4) — في وضع --symbols يُقرأ القرار
    المثبت من تشغيلة كاملة سابقة (data.deScaleDecision) أو يُرفض التطبيق بإنذار."""
    de_raw = {}
    ratios_multi_ok = None   # هل يقبل history=3y؟ يُجرب على أول رمز
    for i, st in enumerate(stocks):
        sym = st["symbol"]

        # 1) ratios — نحاول history=3y لنمو الإيرادات، وإلا latest
        r = None
        if ratios_multi_ok in (None, True):
            r, err = api.get("/analytics/ratios/%s/?history=3y&period=annual&metrics=all" % sym)
            if ratios_multi_ok is None:
                ratios_multi_ok = r is not None
                print("  ratios history=3y: %s" % ("مقبول" if ratios_multi_ok else "مرفوض (%s) — تراجع إلى latest" % err))
        if r is None:
            r, err = api.get("/analytics/ratios/%s/?history=latest&period=annual&metrics=all" % sym)
        periods = rows_of(r, "data", "results", "history")
        if not periods and isinstance(r, dict):
            periods = [r]
        if not periods:
            counters["ratios_fail"] += 1
        else:
            # الأحدث أولاً أو الأقدم أولاً؟ نرتب بتاريخ إن وجد وإلا نفترض الأحدث أولاً
            def pdate(p):
                return str(p.get("date") or p.get("period") or p.get("fiscal_year") or "")
            if len(periods) > 1 and pdate(periods[0]) and pdate(periods[0]) < pdate(periods[-1]):
                periods = list(reversed(periods))
            latest = periods[0]
            rat = latest.get("ratios") or {}
            km = latest.get("key_metrics") or {}
            fin = st.setdefault("financials", {})
            if rat.get("net_margin") is not None:
                fin["profitMargins"] = round(rat["net_margin"], 1)
            if rat.get("roe") is not None:
                fin["returnOnEquity"] = round(rat["roe"], 1)
            if rat.get("roa") is not None:
                fin["returnOnAssets"] = round(rat["roa"], 2)
            if rat.get("debt_to_equity") is not None:
                de_raw[sym] = rat["debt_to_equity"]   # الحسم المقطعي بعد الجمع
            # نمو الإيرادات من فترتين سنويتين إن توفرتا
            revs = []
            for p in periods[:2]:
                tr = (p.get("key_metrics") or {}).get("total_revenue")
                if tr:
                    revs.append(tr)
            if len(revs) == 2 and revs[1]:
                fin["revenueGrowth"] = round((revs[0] - revs[1]) / abs(revs[1]) * 100, 1)
                counters["revgrowth_ok"] += 1
            else:
                counters["revgrowth_miss"] += 1
            st["financialsSource"] = "sahmk analytics/ratios"
            st["financialsUpdated"] = today
            counters["ratios_ok"] += 1
            # بنوك: sectorFinancials بلا اختلاق — ROA متاح، Cost/Income غير متاح (عقد الفحص)
            if "Bank" in (st.get("industry") or ""):
                st["sectorFinancials"] = {
                    "type": "bank", "source": "sahmk analytics/ratios",
                    "ROA": round(rat["roa"], 2) if rat.get("roa") is not None else None,
                    "costToIncome": None,   # لا تفصيل مصروفات في الواجهة — لا يُختلق
                    "totalRevenue": km.get("total_revenue"),
                    "operatingIncome": km.get("operating_income"),
                    "updatedAt": today,
                }
                st.setdefault("debtHealth", {})
                st["debtHealth"] = {"type": "bank", "costToIncome": None,
                                    "color": "gray", "label": "غير متوفر"}
            else:
                st["debtHealth"] = {"type": "company",
                                    "totalDebt": km.get("total_debt"),
                                    "totalCash": None, "netDebt": None, "ebitda": None,
                                    "netDebtToEbitda": None,   # يحتاج نقد/EBITDA — /financials معلق
                                    "color": "gray", "label": "غير متوفر"}
        time.sleep(0.15)

        # 2) company → valuationInputs (العقد القائم لـ compute-valuation.py)
        c, cerr = api.get("/company/%s/" % sym)
        fn = ((c or {}).get("fundamentals") or {})
        ptb = fn.get("price_to_book")
        bv = fn.get("book_value")
        tp = (c or {}).get("current_price")
        # (م-1) current_price غير مؤكد بعقد الفحص — عدّ صريح، وغيابه = «غير قابل للتحقق» (None)
        # لا «فاشل الاتساق» (False): compute-valuation يجمد في الحالتين، لكن الوسم لا يكذب
        if c is not None:
            if tp is not None:
                counters["company_cp_ok"] += 1
            else:
                counters["company_cp_miss"] += 1
        if ptb and bv and tp and tp > 0:
            cons = abs((ptb * bv) / tp - 1) < 0.03   # حارس الاتساق القائم (3%)
        elif tp is None or not tp:
            cons = None                              # غير قابل للتحقق — ليس فشل اتساق
        else:
            cons = False
        vi = {
            "priceToBook": ptb, "bookValue": bv, "theirPrice": tp,
            "marketCap": fn.get("market_cap"), "sharesOutstanding": fn.get("shares_outstanding"),
            "pbConsistent": cons,
            # مدخلات حية خارج مقام المحرك (criteria v2.1) حتى قرار تفعيل موسوم:
            "peRatio": fn.get("pe_ratio"), "epsTtm": fn.get("eps_ttm"),
            "forwardPe": fn.get("forward_pe"),
            "updatedAt": today, "source": "sahmk-direct",
        }
        if c is not None:
            counters["company_ok"] += 1
        else:
            counters["company_fail"] += 1
            print("  ✗ %s company: %s" % (sym, cerr))
        time.sleep(0.15)

        # 3) dividends → divTtm12m/divBasis (خوارزمية الطبقتين القائمة)
        dv, derr = api.get("/dividends/%s/?limit=50" % sym)
        if dv is not None:
            now = datetime.now(timezone.utc)
            d365 = (now - timedelta(days=365)).strftime("%Y-%m-%d")
            d548 = (now - timedelta(days=548)).strftime("%Y-%m-%d")
            rows = []
            for h in rows_of(dv, "history", "data"):
                ed = h.get("eligibility_date") or h.get("due_date") or h.get("date")
                val = h.get("value") if h.get("value") is not None else h.get("amount")
                if ed and val and val > 0:
                    rows.append((ed, val))
            rows.sort(reverse=True)
            tot = sum(v for e, v in rows if d365 <= e <= today)
            if tot > 0:
                vi["divTtm12m"], vi["divBasis"] = round(tot, 4), "ttm12m"
            else:
                recent = [(e, v) for e, v in rows if d548 <= e <= today]
                if recent:
                    vi["divTtm12m"], vi["divBasis"] = round(recent[0][1], 4), "last18m"
                else:
                    vi["divTtm12m"], vi["divBasis"] = 0.0, "none"
            counters["dividends_ok"] += 1
        else:
            counters["dividends_fail"] += 1
        if c is not None or dv is not None:
            st["valuationInputs"] = vi
        if (i + 1) % 25 == 0:
            print("  ... %d/%d أساسيات" % (i + 1, len(stocks)))
        time.sleep(0.15)

    # ── بوابة current_price (م-1): غيابه الواسع يجمد حارس P/B للسوق كله ──
    cp_total = counters["company_cp_ok"] + counters["company_cp_miss"]
    if cp_total and counters["company_cp_miss"] / cp_total > 0.5:
        print("⛔ تحذير حاكم: company.current_price غائب في %d/%d من الردود (>50%%) —"
              % (counters["company_cp_miss"], cp_total))
        print("   حارس اتساق P/B غير قابل للتحقق للسوق كله → compute-valuation سيجمد P/B للجميع.")
        print("   pbConsistent كُتب None (غير قابل للتحقق) لا False — راجع شكل /company/ قبل الاعتماد.")

    # ── حسم مقياس debt_to_equity — على الكون الكامل فقط (م-4) ──
    if not de_raw:
        return None
    if full_universe:
        vals = sorted(de_raw.values())
        med = vals[len(vals) // 2]
        as_ratio = med < 10
        decision = {
            "scale": "ratio×100" if as_ratio else "percent",
            "median": round(med, 3), "n": len(vals), "decidedAt": today,
        }
        print("⚖️ مقياس debt_to_equity (كون كامل): الوسيط %.2f على %d سهماً → %s — القرار يُثبَّت في deScaleDecision" % (
            med, len(vals), "نسبة (يُضرب ×100 لعقد المحرك)" if as_ratio else "٪ (يُعتمد كما هو)"))
    elif stored_de_decision and stored_de_decision.get("scale"):
        decision = stored_de_decision
        as_ratio = decision["scale"] == "ratio×100"
        print("⚖️ مقياس debt_to_equity (--symbols): يُطبق القرار المثبت من تشغيلة كاملة سابقة: %s (حُسم %s على %s سهماً)" % (
            decision["scale"], decision.get("decidedAt", "?"), decision.get("n", "?")))
    else:
        print("⚠️ مقياس debt_to_equity: وضع --symbols بلا قرار مثبت من تشغيلة كاملة سابقة —"
              " يُرفض التطبيق (debtToEquity لا يُكتب لهذه العينة؛ شغّل الكون الكامل أولاً)")
        return None
    for st in stocks:
        v = de_raw.get(st["symbol"])
        if v is not None:
            st.setdefault("financials", {})["debtToEquity"] = round(v * 100, 2) if as_ratio else round(v, 2)
    return decision


def fetch_tasi(api, counters, hist_file, data):
    """تاريخ TASI من historical/TASI + نظام السوق من market/summary — عقد fetch-market-regime.sh"""
    hist = []
    if os.path.exists(hist_file):
        try:
            hist = json.load(open(hist_file))["data"]
        except Exception:
            hist = []
    last = hist[-1]["date"] if hist else (datetime.now(timezone.utc) - timedelta(days=730)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resp, err = api.get("/historical/TASI/?interval=1d&from=%s&to=%s" % (last, today))
    rows, _ = parse_candles(resp)   # للمؤشر نستخدم close الخام — عدّاد السقوط لا يعنيه
    if not rows and not hist:
        counters["tasi_fail"] += 1
        print("  ✗ تاريخ TASI: %s — لا تاريخ محلي: فشل حاكم (المُستدعي يجهض قبل الكتابة)" % err)
        return None
    if not rows:
        counters["tasi_api_stale"] += 1
        print("  ⚠️ واجهة TASI فشلت (%s) — نُكمل بالتاريخ المحلي القائم (%d يوماً، آخره %s)"
              % (err, len(hist), hist[-1]["date"]))
    known = {h["date"] for h in hist}
    added = 0
    for r in rows:
        if r[0] and r[0] not in known:
            hist.append({"date": r[0], "close": round(r[1], 2)})
            added += 1
        elif r[0] in known:
            for h in hist:
                if h["date"] == r[0]:
                    h["close"] = round(r[1], 2)
    hist.sort(key=lambda h: h["date"])
    tmp = hist_file + ".tmp"
    json.dump({"data": hist}, open(tmp, "w"))
    os.replace(tmp, hist_file)
    print("  TASI: تاريخ %d يوماً (+%d جديد)" % (len(hist), added))
    counters["tasi_ok"] += 1

    closes = [h["close"] for h in hist]
    tasi_returns = {"3m": period_return(closes, 63), "6m": period_return(closes, 126),
                    "12m": period_return(closes, 250)}
    data["tasiReturns"] = tasi_returns
    data["tasi"] = {"current": closes[-1], "ret3m": tasi_returns["3m"],
                    "ret6m": tasi_returns["6m"], "ret12m": tasi_returns["12m"]}

    # نظام السوق
    s, serr = api.get("/market/summary/")
    if s is None:
        counters["regime_fail"] += 1
        print("  ✗ market/summary: %s — marketRegime لن يُحدث" % serr)
    else:
        val = s.get("index_value")
        adv, dec = s.get("advancing"), s.get("declining")
        if val and adv is not None and dec is not None:
            day = str(s.get("timestamp") or today)[:10]
            if hist and hist[-1]["date"] == day:
                hist[-1]["close"] = val
                closes[-1] = val          # (إصلاح ت-2) تحديث القائمة الموازية — SMA200 يرى إغلاق اليوم الحي
            else:
                hist.append({"date": day, "close": val})
                closes.append(val)
            tmp = hist_file + ".tmp"
            json.dump({"data": hist}, open(tmp, "w"))
            os.replace(tmp, hist_file)
            prev_close = closes[-2] if len(closes) >= 2 else val
            mr = regime_from_history(closes, val, adv, dec, s.get("market_mood", ""))
            data["marketRegime"] = {
                "date": day, "indexValue": val,
                "prevClose": round(prev_close, 2),
                "change": round(val - prev_close, 2),
                "changePct": round((val - prev_close) / prev_close * 100, 2),
                **mr,
            }
            counters["regime_ok"] += 1
            print("  %s نظام السوق: %s | TASI %.0f (%+.1f%% من SMA200)" % (
                mr["icon"], mr["regime"], val, mr["pctVsSma"]))
        else:
            counters["regime_fail"] += 1
            print("  ✗ market/summary ناقص الحقول: %s" % list((s or {}).keys())[:8])
    return tasi_returns


def recompute_sector_medians(data, stamp):
    """إعادة حساب sectorMedians — اصطلاح fetch-daily-extra.sh حرفياً"""
    import statistics
    sectors = {}
    for s in data["stocks"]:
        sec = s.get("sector")
        if not sec:
            continue
        agg = sectors.setdefault(sec, {"pe": [], "pb": [], "dy": [], "r6": [], "n": 0})
        agg["n"] += 1
        v = s.get("valuation", {})
        if v.get("pe") and v["pe"] > 0: agg["pe"].append(v["pe"])
        if v.get("pb") and v["pb"] > 0: agg["pb"].append(v["pb"])
        if v.get("dividendYield") and v["dividendYield"] > 0: agg["dy"].append(v["dividendYield"])
        r6 = s.get("relativeStrength", {}).get("return6m")
        if r6 is not None: agg["r6"].append(r6)
    data["sectorMedians"] = {
        sec: {
            "peMedian": round(statistics.median(a["pe"]), 2) if a["pe"] else None,
            "pbMedian": round(statistics.median(a["pb"]), 2) if a["pb"] else None,
            "divYieldMedian": round(statistics.median(a["dy"]), 4) if a["dy"] else None,
            "ret6mMedian": round(statistics.median(a["r6"]), 2) if a["r6"] else None,
            "count": a["n"],
        } for sec, a in sectors.items()
    }
    data["sectorMediansUpdated"] = stamp


def probe_financials(api):
    """تجربة تركيبات معاملات /financials/ — من معاملات SDK سهمك الرسمي (v0.15.0):
    type/period/statement_period/history/metrics/result/include_partial"""
    combos = [
        "",
        "?period=annual",
        "?type=income",
        "?type=income&period=annual",
        "?type=income&period=annual&history=latest",
        "?type=cashflow&period=annual&history=latest",
        "?statement_period=annual&history=latest",
        "?period=annual&history=latest&metrics=all&include_partial=true",
    ]
    for sym in ("2222", "1180"):
        print("═" * 50)
        print("فحص /financials/%s/" % sym)
        for c in combos:
            resp, err = api.get("/financials/%s/%s" % (sym, c))
            status = "✅" if resp is not None else ("✗ " + str(err))
            print("  %-55s %s" % (c or "(بلا معاملات)", status))
            if resp is not None:
                print("  🌳 شجرة المفاتيح (أول تركيبة ناجحة):")
                for line in key_tree(resp, depth=3, indent="    "):
                    print(line)
                break
            time.sleep(0.3)
    print("طلبات مستهلكة: %d" % api.requests_made)


# ═══════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="جالب مدخلات المختبر من سهمك (sahmk-direct-v1)")
    ap.add_argument("--data", required=True, help="مسار stocks-data.json (إلزامي — لا افتراضي حمايةً)")
    ap.add_argument("--weekly", action="store_true", help="جلب أسبوعي: شموع 1w + الأساسيات")
    ap.add_argument("--symbols", default="", help="رموز محددة مفصولة بفواصل (اختبار)")
    ap.add_argument("--probe-financials", action="store_true", help="فحص تركيبات /financials/ ثم خروج")
    ap.add_argument("--key-file", default="", help="ملف المفتاح (بديل SAHMK_KEY)")
    ap.add_argument("--tasi-history", default="", help="مسار tasi-history.json (افتراضي بجوار --data)")
    args = ap.parse_args()

    key = os.environ.get("SAHMK_KEY", "")
    if not key and args.key_file:
        key = open(args.key_file).read().strip()
    if not key:
        sys.exit("⛔ لا مفتاح: مرر SAHMK_KEY في البيئة أو --key-file (يُمنع وضعه في الكود/المستودع)")

    api = Api(key)

    if args.probe_financials:
        probe_financials(api)
        return

    with open(args.data) as f:
        data = json.load(f)
    stocks = [s for s in data.get("stocks", []) if s.get("symbol")]
    if args.symbols:
        want = {x.strip() for x in args.symbols.split(",") if x.strip()}
        stocks = [s for s in stocks if s["symbol"] in want]
    if not stocks:
        sys.exit("⛔ لا أسهم مطابقة في %s" % args.data)

    hist_file = args.tasi_history or os.path.join(os.path.dirname(os.path.abspath(args.data)), "tasi-history.json")

    n = len(stocks)
    batches = (n + 49) // 50
    budget = batches + n + 2 + (n * 4 if args.weekly else 0)
    print("═" * 60)
    print("سيف تداول — جالب سهمك المباشر (sahmk-direct-v1)")
    print("أسهم: %d | الوضع: %s" % (n, "أسبوعي (1w + أساسيات)" if args.weekly else "يومي"))
    print("ميزانية الطلبات المتوقعة: ~%d (quotes %d + 1d %d + TASI/summary 2%s) — الحصة 5000/يوم"
          % (budget, batches, n, " + 1w %d + ratios %d + company %d + dividends %d" % (n, n, n, n) if args.weekly else ""))
    print("═" * 60)

    counters = {k: 0 for k in (
        "quotes_ok", "quotes_fail", "quotes_batch_fail", "daily_ok", "daily_fail",
        "weekly_ok", "weekly_fail", "ratios_ok", "ratios_fail", "revgrowth_ok", "revgrowth_miss",
        "company_ok", "company_fail", "company_cp_ok", "company_cp_miss",
        "dividends_ok", "dividends_fail",
        "adj_fb_rows_1d", "adj_fb_syms_1d", "adj_fb_rows_1w", "adj_fb_syms_1w",
        "tasi_ok", "tasi_fail", "tasi_api_stale", "regime_ok", "regime_fail")}

    now_riyadh = datetime.now(RIYADH).strftime("%Y-%m-%d %H:%M")
    stamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1) TASI أولاً (القوة النسبية تحتاج عوائده)
    print("📈 TASI ونظام السوق...")
    tasi_returns = fetch_tasi(api, counters, hist_file, data) or {}
    # (ج-1) بوابة حاكمة: فشل TASI الكامل (لا تاريخ محلي + فشل الواجهة) أو تاريخ أقصر من
    # نافذة 6م = عوائد rsTasi3m/6m مستحيلة → كل الأسهم تخسر 7/11 من الزخم بصمت لو تابعنا.
    # الأسلم المختار: إجهاض قبل أي كتابة للملف الرئيسي (خروج 1) — الملف القديم يبقى سليماً
    # بأختامه القديمة. (tasi-history قد يكون تحدّث — بيانات صالحة بذاتها، أثر جانبي مشروع.)
    if tasi_returns.get("3m") is None or tasi_returns.get("6m") is None:
        sys.exit("⛔ فشل TASI حاكم: عوائد المؤشر 3م/6م غير قابلة للحساب (تاريخ غائب/قاصر) — "
                 "لا كتابة إطلاقاً. عالج تاريخ TASI ثم أعد التشغيل.")

    # 2) الأسعار
    print("💰 الأسعار (quotes دفعات 50)...")
    q_ok = fetch_quotes(api, stocks, counters, now_riyadh)
    if q_ok == 0:
        sys.exit("⛔ فشل جلب الأسعار كلياً — لا كتابة (الملف القديم يبقى كما هو)")

    # 3) الشموع اليومية
    print("📊 الشموع اليومية (1d)...")
    fetch_daily(api, stocks, counters, tasi_returns, stamp_utc)

    # 4) الأسبوعي والأساسيات
    de_decision = None
    if args.weekly:
        print("🗓 الشموع الأسبوعية (1w)...")
        fetch_weekly(api, stocks, counters, stamp_utc)
        print("🏦 الأساسيات (ratios/company/dividends)...")
        de_decision = fetch_fundamentals(api, stocks, counters, today,
                                         full_universe=not args.symbols,
                                         stored_de_decision=data.get("deScaleDecision"))
        data["weeklyTechnicalUpdated"] = now_riyadh + " الرياض"
        if de_decision and not args.symbols:
            data["deScaleDecision"] = de_decision   # تثبيت القرار بين التشغيلات (م-4)

    # 5) وسطاء القطاعات
    recompute_sector_medians(data, stamp_utc)

    # 6) الخلاصة وبوابة الفشل — قبل أي كتابة (م-3: الملف لا يُكتب أصلاً عند فشل >10%)
    print("═" * 60)
    print("الطلبات المستهلكة فعلياً: %d / ميزانية ~%d" % (api.requests_made, budget))
    fail_types = []
    for label, ok_k, fail_k in (
            ("أسعار", "quotes_ok", "quotes_fail"), ("شموع يومية", "daily_ok", "daily_fail"),
            ("شموع أسبوعية", "weekly_ok", "weekly_fail"), ("نسب مالية", "ratios_ok", "ratios_fail"),
            ("company", "company_ok", "company_fail"), ("توزيعات", "dividends_ok", "dividends_fail")):
        ok, fl = counters[ok_k], counters[fail_k]
        if ok + fl == 0:
            continue
        pct = fl / (ok + fl) * 100
        mark = "⚠️" if pct > 10 else "✅"
        print("%s %s: نجح %d | فشل %d (%.0f%%)" % (mark, label, ok, fl, pct))
        if pct > 10:
            fail_types.append(label)
    print("نمو الإيرادات: متاح %d | غير متاح %d" % (counters["revgrowth_ok"], counters["revgrowth_miss"]))
    print("TASI: %s%s | نظام السوق: %s" % (
        "✅" if counters["tasi_ok"] else "✗",
        " (واجهة فشلت — تاريخ محلي)" if counters["tasi_api_stale"] else "",
        "✅" if counters["regime_ok"] else "✗"))
    # (م-2) السقوط adjusted_close→close معدود ومعلن — وفي 1w إنذار صريح (اصطلاح SMA200W ملزم)
    if counters["adj_fb_rows_1d"]:
        print("⚠️ 1d: %d شمعة بلا adjusted_close سقطت إلى close عند %d سهماً"
              % (counters["adj_fb_rows_1d"], counters["adj_fb_syms_1d"]))
    if counters["adj_fb_rows_1w"]:
        print("⛔ إنذار اصطلاح: 1w فيها %d شمعة بلا adjusted_close سقطت إلى close عند %d سهماً —"
              % (counters["adj_fb_rows_1w"], counters["adj_fb_syms_1w"]))
        print("   هذا يمس أساس SMA200W المعدل (ملحق 24-07: ترحيل السلسلة إلى خام = وسم نسخة معايير)")
        print("   — لا اعتماد لهذه التشغيلة قبل قرار وسم موثق.")
    if fail_types:
        print("⛔ فشل يتجاوز 10%% في: %s — لا كتابة، الملف القديم يبقى كما هو" % "، ".join(fail_types))
        sys.exit(1)

    # 7) أختام وكتابة ذرية — لا تُبلغ إلا بعد عبور البوابة
    data["lastUpdated"] = now_riyadh + " الرياض"
    data["priceSource"] = "sahmk-direct-v1"
    data.setdefault("priceSourceSince", today)
    data["_labNote"] = ("مدخلات مبنية محلياً من واجهة سهمك (fetch-inputs-sahmk.py) — "
                        "مستقلة عن مزامنة المشروع الأصلي. P/E حي في valuationInputs فقط "
                        "(خارج مقام المحرك — criteria v2.1). "
                        + ("مقياس D/E: %s (وسيط %s على %s سهماً، حُسم %s). " % (
                            de_decision["scale"], de_decision.get("median", "?"),
                            de_decision.get("n", "?"), de_decision.get("decidedAt", "?"))
                           if de_decision else "")
                        + "الخط بعده: compute-valuation.py ثم scoring-engine.py.")

    out_dir = os.path.dirname(os.path.abspath(args.data)) or "."
    fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, args.data)
    try:
        os.chmod(args.data, 0o664)
    except OSError:
        pass
    print("كُتب: %s (ذرياً) | priceSource=sahmk-direct-v1" % args.data)
    print("✅ اكتمل — الخطوة التالية: python3 scripts/compute-valuation.py ثم scripts/scoring-engine.py")


if __name__ == "__main__":
    main()
