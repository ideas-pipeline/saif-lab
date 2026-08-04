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
    أسبوعي (--weekly): + historical-1w 248 + ratios 248 + financials 248 + company 248
                       + dividends 248 ≈ 1495 — ما زال مريحاً تحت الحصة.
    التقدير happy-path: إعادات 429/الأخطاء قد ترفع المستهلك الفعلي (تشغيلة 04-08: 1342
    لميزانية 1247). الإيقاع الذاتي ~2.5 طلب/ث + احترام Retry-After + جولة التقاط 429
    لكل نوع — الهدف صفر فشل بسبب 429.

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

سياسة المصادر — data-source v3 (قرار المحلل ج-2، 2026-08-04): «الجالب لا يختم إلا ما جلب»
----------------------------------------------------------------------------------------
    - دمج حافظ دائماً: يُمنع استبدال قيمة صالحة بـnull، ويُمنع تجديد ختم على قيمة
      لم تُجلب في التشغيلة نفسها. الانتقال متعادل النقاط تماماً (لا criteria جديد).
    - debtHealth: لا يكتبها الجالب إطلاقاً — الكتل القائمة تبقى محتسبة، موسومة
      بالترحيل source=yfinance-legacy + asOf (من liquidityDebtUpdated الفعلي).
    - sectorFinancials (بنوك): دمج بمستوى الحقل — ROA/الإيرادات حية من سهمك،
      costToIncome القديمة تُحفظ وتبقى محتسبة، sahmkFields/legacyFields يعددان المصدر.
    - financials: خريطة financialsParts لكل حقل {source, asOf} (تعميم نمط valuationParts)؛
      financialsSource لا يدعي سهمك لحقل لم يأت منه، وfinancialsUpdated يصدق على المجلوب فقط.
    - cashflow: موسومة بالترحيل source=legacy-unknown, asOf=null — تبقى محتسبة.
    - valuationInputs: دمج بمجموعات متماسكة (company/dividends) بختمي companyAsOf/divsAsOf.

معيار القبول الحاكم — التشغيلة الظلية (قرار المحلل بند 7)
--------------------------------------------------------
    اعتماد الجالب مشروط بتشغيل المحرك على ناتجه وعلى آخر ناتج مزامنة لنفس اليوم
    المرجعي ثم: **صفر فرق في total واسم التصنيف لكل الأسهم الـ248**. أي فرق غير
    صفري = خلل يوقف الاعتماد حتى تفسيره. أداة الفحص مدمجة:
        python3 scripts/fetch-inputs-sahmk.py --shadow-compare ناتج-الجالب.json ناتج-المزامنة.json
    (محلية خالصة — بلا شبكة ولا مفتاح؛ خروج 0 = متطابق، 1 = فروق مطبوعة)

مستجدات تشغيلة 04-08 (مدمجة)
----------------------------
    - /financials/{sym}/ يعمل **بلا معاملات** (اكتشاف --probe-financials): income_statements/
      balance_sheets/cash_flows (4 عناصر: report_date/statement_period/fiscal_year/
      is_full_year + الحقول) + reporting(reporting_cadence/quarterly_income_convention).
      استُثمر: cashflow.ocf/netIncome/fcf حية (اصطلاح موثق: **آخر سنة مالية كاملة**
      is_full_year=true الأحدث — يطابق سنوية باقي النسب؛ TTM من الأرباع مؤجل حتى تحقق
      quarterly_income_convention؛ netIncome الغائب من القوائم مع بقاء قديم = وسم
      netIncomeSource صريح — لا خلط عمرين تحت وسم واحد)، وrevenueGrowth من سنتين
      كاملتين **متتاليتين فعلاً** (تحقق تتالي fiscal_year — فجوة سنة = لا نمو).
    - **C/I البنوك — الاشتقاق مجمد بقرار المحلل (الخيار ب، 04-08):** المشتق
      (rev−opi)/rev يُحسب ويُخزن معلوماتياً في sectorFinancials.costToIncomeDerived
      (المحرك لا يقرؤه) **ولا يُكتب في costToIncome إطلاقاً** — legacy تبقى المحتسبة.
      جدول مقارنة العشرة (legacy | مشتق | الفرق) يُطبع كل تشغيلة أساسيات وفي تقرير
      الظلية الأسبوعي — القرار النهائي (اعتماد بوسم تعريفي / معايرة عتبات موسومة /
      بقاء legacy لبند 27) يُتخذ على فروق أول تشغيلة الفعلية.
    - سلطة الإنذارات (شرط الناقد — الخيار الموثق: صياغة تطابق الواقع، لا سلطات جديدة):
      فقد adjusted_close الكامل لسهم = تخطٍّ معدود (weekly_fail) والكتلة القديمة باقية —
      لا تغيير اصطلاح يقع فلا سلطة إيقاف؛ وغياب current_price الواسع = «تحذير جسيم
      بتدهور آمن» (تجميد P/B محافظ) — إسقاط التشغيلة له عقوبة غير متناسبة.
    - ratios: التركيبة المؤكدة حصراً history=latest&period=annual&metrics=all —
      history=3y أُسقط نهائياً (HTTP 400 مؤكد إنتاجياً)؛ فشل التفكيك يُعدّ فشلاً
      مسموعاً بأسبابه (أول 3 لكل نوع) لا عدّاداً صامتاً.

ما يبقى مفتوحاً (لا يُختلق — الغياب null والمحرك يتعامل معه كعادته)
------------------------------------------------------------------
    - currentRatio: يبقى موروثاً نهائياً من هذا المصدر — balance_sheets إجماليات فقط
      (total_assets/total_liabilities) بلا شق متداول.
    - Cost/Income للبنوك: الاشتقاق **مجمد بقرار المحلل (الخيار ب)** حتى مراجعة فروق
      العشرة من أول تشغيلة؛ والقيمة المحتسبة تبقى legacy. إن أثبتت القوائم
      operating_income == total_revenue فالاشتقاق مستحيل أصلاً (يُعدّ في bank_cti_flat).
    - ترحيل الوسوم يجري في الذاكرة كل تشغيلة؛ إن حجبت بوابة فشل الكتابة ضاع معها —
      سلوك صحيح: يعاد آلياً في التشغيلة التالية بحكم idempotent.
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

RATE_PER_SEC = 2.5   # حد الإيقاع الذاتي: ~2-3 طلبات/ثانية (رشقات 429 = حد دقيقة لا حصة)


class Api:
    """طبقة الشبكة — تهدئة إيقاع + احترام Retry-After (تشخيص تشغيلة 04-08: رشقات 429
    من حد الدقيقة لا الحصة — المستهلك كان 1342/5000 والفشل متناثر متتالي الرموز)."""

    def __init__(self, key):
        self.key = key
        self.requests_made = 0
        self.hits_429 = 0
        self._min_gap = 1.0 / RATE_PER_SEC
        self._last = 0.0

    def get(self, path, tries=3, timeout=25):
        """GET مع: إيقاع ذاتي، إعادة محاولة بتراجع تصاعدي، واحترام Retry-After عند 429.
        يعيد (json, None) أو (None, وصف_الخطأ — آخر خطأ)"""
        url = BASE + path
        err = "unknown"
        for attempt in range(tries):
            gap = self._min_gap - (time.monotonic() - self._last)
            if gap > 0:
                time.sleep(gap)
            self._last = time.monotonic()
            self.requests_made += 1
            try:
                req = urllib.request.Request(url, headers={
                    "X-API-Key": self.key, "User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.load(resp), None
            except urllib.error.HTTPError as e:
                err = "HTTP %d" % e.code
                if e.code == 429:
                    self.hits_429 += 1
                    ra = e.headers.get("Retry-After") if e.headers else None
                    try:
                        delay = max(1.0, float(ra)) if ra else 5.0 * (attempt + 1)
                    except (TypeError, ValueError):
                        delay = 5.0 * (attempt + 1)
                    time.sleep(min(delay, 65))
                    continue
                # (تشخيص 04-08ب) جسد الرد لغير-429: سهمك يرجع error.code/message/details —
                # الرسالة الحرفية تسمي المعامل المرفوض، وبدونها كان تشخيص 400 أعمى
                body = ""
                try:
                    body = e.read().decode("utf-8", "replace").strip()[:300]
                except Exception:
                    pass
                if body:
                    err = "%s — %s" % (err, body)
                if e.code in (400, 401, 403, 404):
                    return None, err      # لا جدوى من الإعادة
            except Exception as e:
                err = type(e).__name__
            if attempt < tries - 1:
                time.sleep(2 * (attempt + 1))
        return None, err


def note_fail(counters, printed_key, label, sym, err, limit=3):
    """طباعة سبب أول N إخفاقات لكل نوع (درس تشغيلة 04-08: عدّاد بلا سبب = تشخيص مستحيل)"""
    counters[printed_key] = counters.get(printed_key, 0) + 1
    if counters[printed_key] <= limit:
        print("  ✗ %s %s: %s" % (sym, label, err))
    elif counters[printed_key] == limit + 1:
        print("  ✗ %s: ... (تُطبع أول %d أسباب فقط — الباقي في العداد)" % (label, limit))


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
    قاعدة adjusted_close (تشخيص تشغيلة 04-08، أدنى تدخلاً): الشمعة الفاقدة للمعدل
    **لا تُخلط بالخام** — تبقى في الصف بقيمة adj=None والمستهلك يقرر:
      1w: تُسقط الشمعة من السلسلة المعدلة (شرط ≥50/≥200 على المتبقي)؛ سهم فقد
          المعدل لسلسلته كلها = إنذار حاكم (تغيير اصطلاح — ملحق 24-07).
      1d: المؤشرات الخام لا تتأثر؛ تُسقط الشمعة من سلسلة العوائد المعدلة فقط.
    يعيد (rows, dropped_dates) — rows بعناصر (date, close, high, low, vol, adj|None)."""
    rows = rows_of(resp, "data", "candles", "history", "results")
    out = []
    dropped_dates = []
    for r in rows:
        if r.get("close") is None or r.get("high") is None or r.get("low") is None:
            continue
        adj = r.get("adjusted_close")
        if adj is None:
            dropped_dates.append(r.get("date", "?"))
        out.append((r.get("date", ""), r["close"], r["high"], r["low"],
                    r.get("volume") or 0, adj))
    out.sort(key=lambda x: x[0])
    return out, sorted(dropped_dates)


def fetch_daily(api, stocks, counters, tasi_returns, stamp):
    d420 = (datetime.now(timezone.utc) - timedelta(days=420)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def process(st):
        """يعيد (نجح؟، وصف الخطأ) — قابل لإعادة التمرير في جولة التقاط 429"""
        sym = st["symbol"]
        resp, err = api.get("/historical/%s/?interval=1d&from=%s&to=%s" % (sym, d420, today))
        rows, dropped = parse_candles(resp)
        if dropped:
            counters["adj_fb_rows_1d"] += len(dropped)
            counters["adj_fb_syms_1d"] += 1
        # نافذة سنة تداول: آخر 251 شمعة (اصطلاح fetch-daily-extra range=1y مع ضمان عائد 12م)
        rows = rows[-251:]
        if len(rows) < 60:
            return False, (err or "شموع قليلة (%d)" % len(rows))
        closes = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]
        vols = [r[4] for r in rows]
        # سلسلة العوائد المعدلة: الشمعة بلا adjusted_close تُسقط منها (لا خلط خام/معدل)
        adjcls = [r[5] for r in rows if r[5] is not None]

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
        return True, None

    run_with_429_sweep(stocks, process, counters, "daily_ok", "daily_fail", "شموع يومية")


def run_with_429_sweep(stocks, process, counters, ok_key, fail_key, label):
    """تمريرة أساسية ثم جولة التقاط ثانية لضحايا 429 حصراً (تشخيص تشغيلة 04-08).
    process(st) → (نجح؟، وصف الخطأ). العدادات النهائية بعد الجولتين."""
    victims = []
    for i, st in enumerate(stocks):
        ok, err = process(st)
        if ok:
            counters[ok_key] += 1
        elif "429" in str(err):
            victims.append(st)
        else:
            note_fail(counters, fail_key, label, st["symbol"], err)
        if (i + 1) % 25 == 0:
            print("  ... %d/%d %s" % (i + 1, len(stocks), label))
    if victims:
        print("  🔁 جولة التقاط 429 (%s): %d رمزاً بعد تهدئة..." % (label, len(victims)))
        time.sleep(20)
        for st in victims:
            ok, err = process(st)
            if ok:
                counters[ok_key] += 1
            else:
                note_fail(counters, fail_key, label + " (بعد الالتقاط)", st["symbol"], err)


def fetch_weekly(api, stocks, counters, stamp, adj_diag):
    d5y = (datetime.now(timezone.utc) - timedelta(days=1826)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def process(st):
        sym = st["symbol"]
        resp, err = api.get("/historical/%s/?interval=1w&from=%s&to=%s" % (sym, d5y, today))
        rows, dropped = parse_candles(resp)
        # قاعدة adjusted_close في 1w (04-08، أدنى تدخلاً): الشمعة الفاقدة تُسقط من
        # السلسلة — لا خلط خام/معدل؛ الشرطان ≥50 و(بنيوياً) ≥200 على المتبقي.
        # سهم فقد المعدل لسلسلته كلها = تغيير اصطلاح كامل → إنذار حاكم (ملحق 24-07).
        if dropped:
            counters["adj_fb_rows_1w"] += len(dropped)
            counters["adj_fb_syms_1w"] += 1
            if rows and len(dropped) >= len(rows):
                adj_diag["full"].append(sym)
            else:
                adj_diag["partial"].append("%s (شموع %s)" % (sym, "، ".join(dropped[:5])))
        prices = [round(r[5], 2) for r in rows if r[5] is not None]   # المعدلة حصراً
        if len(prices) < 50:
            return False, (err or "شموع معدلة قليلة (%d)" % len(prices))
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
        return True, None

    run_with_429_sweep(stocks, process, counters, "weekly_ok", "weekly_fail", "شموع أسبوعية")


def _fs_val(e, key, *nests):
    """قراءة متسامحة لحقل قائمة مالية: مسطّح أو متداخل تحت مفاتيح معروفة"""
    if isinstance(e, dict):
        if e.get(key) is not None:
            return e[key]
        for n in nests:
            d = e.get(n)
            if isinstance(d, dict) and d.get(key) is not None:
                return d[key]
    return None


def _latest_full_year(elements, nests):
    """آخر عنصر سنة كاملة (is_full_year=true، الأحدث بـreport_date) — اصطلاح OCF الموثق"""
    fy = [e for e in elements if _fs_val(e, "is_full_year", *nests) is True]
    if not fy:
        return None
    return max(fy, key=lambda e: str(_fs_val(e, "report_date", *nests) or ""))


def parse_financials(f):
    """تفكيك /financials/{sym}/ (بلا معاملات — البنية المؤكدة 04-08):
    income_statements/balance_sheets/cash_flows (4 عناصر لكل منها) + reporting.
    اصطلاح الفترة المقرر والموثق: **آخر سنة مالية كاملة** (is_full_year=true الأحدث
    بـreport_date) من كل قائمة — يطابق الاصطلاح السنوي لكل نسب المحور المالي.
    TTM من الأرباع مؤجل عمداً: يتطلب quarterly_income_convention=discrete وتحققاً
    لم يجر بعد؛ reporting يُقرأ ويُعاد للمستدعي للاطلاع.
    currentRatio يبقى موروثاً: balance_sheets إجماليات فقط (total_assets/liabilities)
    بلا شق متداول — موثق نهائياً."""
    if not isinstance(f, dict):
        return None
    body = f
    for k in ("data", "results"):
        if isinstance(body.get(k), dict):
            body = body[k]
    inc = body.get("income_statements") or []
    cfs = body.get("cash_flows") or []
    if not isinstance(inc, list) or not isinstance(cfs, list) or (not inc and not cfs):
        return {"_shape_error": "مفاتيح غير متوقعة: %s" % sorted(body.keys())[:8]}
    NEST_I = ("income",)
    NEST_C = ("cash_flows", "cash_flow")
    out = {"reporting": body.get("reporting") or {}}
    li = _latest_full_year(inc, NEST_I)
    if li:
        out["totalRevenue"] = _fs_val(li, "total_revenue", *NEST_I)
        out["operatingIncome"] = _fs_val(li, "operating_income", *NEST_I)
        out["grossProfit"] = _fs_val(li, "gross_profit", *NEST_I)
        out["netIncome"] = _fs_val(li, "net_income", *NEST_I)
        out["reportDate"] = _fs_val(li, "report_date", *NEST_I)
        out["fiscalYear"] = _fs_val(li, "fiscal_year", *NEST_I)
    lc = _latest_full_year(cfs, NEST_C)
    if lc:
        out["ocf"] = _fs_val(lc, "operating_cash_flow", *NEST_C)
        out["fcf"] = _fs_val(lc, "free_cash_flow", *NEST_C)
        out["cfReportDate"] = _fs_val(lc, "report_date", *NEST_C)
        out["cfFiscalYear"] = _fs_val(lc, "fiscal_year", *NEST_C)
    # الميزانية (آخر سنة كاملة) — للمسار البديل عن ratios (اشتقاق ROE/D-E) — إجماليات فقط
    bals = body.get("balance_sheets") or []
    NEST_B = ("balance",)
    lb = _latest_full_year(bals, NEST_B) if isinstance(bals, list) else None
    if lb:
        out["stockholdersEquity"] = _fs_val(lb, "stockholders_equity", *NEST_B)
        out["totalDebt"] = _fs_val(lb, "total_debt", *NEST_B)
        out["totalAssets"] = _fs_val(lb, "total_assets", *NEST_B)
    # نمو الإيرادات: آخر سنتين كاملتين **متتاليتين فعلاً** من قوائم الدخل (تحسين الناقد:
    # تحقق تتالي fiscal_year — فجوة سنة مفقودة كانت ستنتج «نمواً» على سنتين فتضلل).
    # التتالي: fiscal_year فرقهما 1 إن توفر، وإلا سنة report_date فرقهما 1، وإلا لا نمو.
    fy_inc = sorted((e for e in inc if _fs_val(e, "is_full_year", *NEST_I) is True),
                    key=lambda e: str(_fs_val(e, "report_date", *NEST_I) or ""), reverse=True)
    if len(fy_inc) >= 2:
        e0, e1 = fy_inc[0], fy_inc[1]
        revs = (_fs_val(e0, "total_revenue", *NEST_I), _fs_val(e1, "total_revenue", *NEST_I))
        def _year(e):
            fy = _fs_val(e, "fiscal_year", *NEST_I)
            if fy is not None:
                try:
                    return int(fy)
                except (TypeError, ValueError):
                    pass
            rd = str(_fs_val(e, "report_date", *NEST_I) or "")[:4]
            return int(rd) if rd.isdigit() else None
        y0, y1 = _year(e0), _year(e1)
        consecutive = (y0 is not None and y1 is not None and y0 - y1 == 1)
        if consecutive and revs[0] is not None and revs[1]:
            out["revenueGrowth"] = round((revs[0] - revs[1]) / abs(revs[1]) * 100, 1)
        elif not consecutive:
            out["revGrowthGapYears"] = (y0, y1)   # للتشخيص — سنتان غير متتاليتين
    return out


def fetch_fundamentals(api, stocks, counters, today, full_universe, stored_de_decision):
    """ratios(latest المؤكدة حصراً) + قوائم /financials/ (بلا معاملات) + company + dividends.
    - أُسقط history=3y نهائياً (400 مؤكد في تشغيلة 04-08) — النمو من القوائم مباشرة.
    - مقياس D/E: يُحسم مقطعياً على الكون الكامل فقط (م-4)؛ --symbols يقرأ المثبت أو يرفض.
    - جولة التقاط 429 لكل نقطة نهاية على حدة، وأسباب أول 3 إخفاقات تُطبع لكل نوع."""
    de_raw = {}
    de_src = {}           # sym -> مصدر قيمة D/E (ratios أم اشتقاق القوائم) — لوسم parts الصادق
    scratch = {}          # sym -> قيم تتجمع من ratios+financials لدمج sectorFinancials بعد الجولتين
    reporting_shown = [False]

    def setf(st, key, val, source):
        """كتابة حقل financials بدمج حافظ + وسم — «الجالب لا يختم إلا ما جلب»"""
        if val is not None:
            st.setdefault("financials", {})[key] = val
            st.setdefault("financialsParts", {})[key] = {"source": source, "asOf": today}

    def do_ratios(st):
        sym = st["symbol"]
        # التركيبة المؤكدة بالفحص اليدوي حرفياً — لا معاملات مجربة أخرى
        r, err = api.get("/analytics/ratios/%s/?history=latest&period=annual&metrics=all" % sym)
        if r is None:
            return False, err
        body = r
        for k in ("data", "results"):
            if isinstance(body.get(k), dict):
                body = body[k]
        if isinstance(body, list):
            body = body[0] if body else {}
        rat = body.get("ratios") or {}
        if not rat:
            # فشل تفكيك = فشل مسموع لا صامت (درس 04-08)
            return False, "بنية غير متوقعة — مفاتيح: %s" % sorted(body.keys() if isinstance(body, dict) else [])[:8]
        setf(st, "profitMargins", round(rat["net_margin"], 1) if rat.get("net_margin") is not None else None, "sahmk analytics/ratios")
        setf(st, "returnOnEquity", round(rat["roe"], 1) if rat.get("roe") is not None else None, "sahmk analytics/ratios")
        setf(st, "returnOnAssets", round(rat["roa"], 2) if rat.get("roa") is not None else None, "sahmk analytics/ratios")
        if rat.get("debt_to_equity") is not None:
            de_raw[sym] = rat["debt_to_equity"]
            de_src[sym] = "sahmk analytics/ratios"
        sc = scratch.setdefault(sym, {})
        sc["roa"] = rat.get("roa")
        sc["ratiosOk"] = True
        return True, None

    def do_financials(st):
        sym = st["symbol"]
        f, err = api.get("/financials/%s/" % sym)   # بلا معاملات — المؤكد 04-08
        if f is None:
            return False, err
        p = parse_financials(f)
        if p is None or "_shape_error" in (p or {}):
            return False, (p or {}).get("_shape_error", "استجابة غير قابلة للتفكيك")
        if not reporting_shown[0] and p.get("reporting"):
            reporting_shown[0] = True
            print("  📋 reporting: cadence=%s | quarterly_convention=%s (اصطلاح OCF: آخر سنة كاملة)"
                  % (p["reporting"].get("reporting_cadence"), p["reporting"].get("quarterly_income_convention")))
        # cashflow: إحياء OCF (3ن) — ترقية الوسم من legacy-unknown إلى sahmk بختم report_date الحقيقي.
        # (تحسين الناقد: لا خلط عمرين تحت وسم واحد) — netIncome يُكتب من القوائم مع ocf الجديد؛
        # وإن غاب net_income من القوائم مع بقاء قيمة قديمة، تُوسم القديمة صراحة netIncomeSource
        # بدل تركها توحي بأنها من sahmk بختم الكتلة الجديد. (لا تُستبدل بـnull — قاعدة الحفظ.)
        if p.get("ocf") is not None:
            cf = dict(st.get("cashflow") or {})
            cf["ocf"] = p["ocf"]
            if p.get("netIncome") is not None:
                cf["netIncome"] = p["netIncome"]
                cf.pop("netIncomeSource", None)   # صار من نفس المصدر والعمر
            elif cf.get("netIncome") is not None:
                cf["netIncomeSource"] = "legacy-unknown"   # قيمة قديمة تحت كتلة موسومة sahmk — وسم صريح
            if p.get("fcf") is not None:
                cf["fcf"] = p["fcf"]
            cf["source"] = "sahmk /financials"
            cf["asOf"] = p.get("cfReportDate") or p.get("reportDate")
            cf["convention"] = "annual-full-year"
            st["cashflow"] = cf
            counters["ocf_ok"] += 1
        # نمو الإيرادات من القوائم
        if p.get("revenueGrowth") is not None:
            setf(st, "revenueGrowth", p["revenueGrowth"], "sahmk /financials")
            counters["revgrowth_ok"] += 1
        else:
            counters["revgrowth_miss"] += 1
        # مصروفات البنوك — **الاشتقاق مجمد بقرار المحلل (الخيار ب، 04-08)**:
        # C/I المشتق (rev−opi)/rev يُحسب للمقارنة فقط ولا يُكتب في costToIncome إطلاقاً —
        # القيمة القديمة legacy تبقى هي المحتسبة، والمشتق يُخزن في حقل معلوماتي مستقل
        # (costToIncomeDerived — لا يقرؤه المحرك) ويُطبع جدول مقارنة العشرة. القرار
        # النهائي (اعتماد بوسم / معايرة موسومة / بقاء legacy لبند 27) على فروق أول تشغيلة.
        # الاشتقاق من القوائم حصراً (04-08ب: استقلال تام عن نجاح ratios) مع عدّ الحالات
        # الثلاث صراحة: مشتق | مصروفات غير مفصلة (opi>=rev) | مدخل غائب (rev أو opi null)
        if "Bank" in (st.get("industry") or ""):
            rev, opi = p.get("totalRevenue"), p.get("operatingIncome")
            sc = scratch.setdefault(sym, {})
            sc["bankRevenue"], sc["bankOpIncome"] = rev, opi
            if rev and opi is not None and 0 < opi < rev:
                cti = round((rev - opi) / rev * 100, 1)
                if 0 < cti < 100:
                    sc["ctiDerived"] = cti   # للمقارنة والتخزين المعلوماتي — لا للاحتساب
                    counters["bank_cti_ok"] += 1
            elif rev and opi is not None and opi >= rev:
                counters["bank_cti_flat"] += 1   # لا تفصيل مصروفات في القوائم أيضاً
            else:
                counters["bank_cti_na"] += 1     # rev أو opi غائب من القوائم — يُشخص بالقيم في الجدول
        # مدخلات المسار البديل عن ratios (تُستخدم فقط عند فشله — بعد الجولتين)
        sc2 = scratch.setdefault(sym, {})
        sc2["stmt"] = {k: p.get(k) for k in ("totalRevenue", "netIncome", "stockholdersEquity",
                                             "totalDebt", "reportDate")}
        return True, None

    def do_company(st):
        sym = st["symbol"]
        c, err = api.get("/company/%s/" % sym)
        if c is None:
            return False, err
        fn = c.get("fundamentals") or {}
        ptb = fn.get("price_to_book")
        bv = fn.get("book_value")
        tp = c.get("current_price")
        # (م-1) current_price غير مؤكد بعقد الفحص — عدّ صريح، وغيابه = «غير قابل للتحقق» (None)
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
        # دمج حافظ بمجموعات: مجموعة company متماسكة (قرار المحلل — قاعدة 5)
        vi = dict(st.get("valuationInputs") or {})
        vi.update({
            "priceToBook": ptb, "bookValue": bv, "theirPrice": tp,
            "marketCap": fn.get("market_cap"), "sharesOutstanding": fn.get("shares_outstanding"),
            "pbConsistent": cons,
            # مدخلات حية خارج مقام المحرك (criteria v2.1) حتى قرار تفعيل موسوم:
            "peRatio": fn.get("pe_ratio"), "epsTtm": fn.get("eps_ttm"),
            "forwardPe": fn.get("forward_pe"),
            "companyAsOf": today, "updatedAt": today, "source": "sahmk-direct",
        })
        st["valuationInputs"] = vi
        return True, None

    def do_dividends(st):
        sym = st["symbol"]
        dv, err = api.get("/dividends/%s/?limit=50" % sym)
        if dv is None:
            return False, err
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
        vi = dict(st.get("valuationInputs") or {})
        tot = sum(v for e, v in rows if d365 <= e <= today)
        if tot > 0:
            vi["divTtm12m"], vi["divBasis"] = round(tot, 4), "ttm12m"
        else:
            recent = [(e, v) for e, v in rows if d548 <= e <= today]
            if recent:
                vi["divTtm12m"], vi["divBasis"] = round(recent[0][1], 4), "last18m"
            else:
                vi["divTtm12m"], vi["divBasis"] = 0.0, "none"
        vi["divsAsOf"] = today
        vi["updatedAt"] = today
        vi["source"] = "sahmk-direct"
        st["valuationInputs"] = vi
        return True, None

    ENDPOINTS = (("ratios", "نسب مالية", "ratios_ok", "ratios_fail", do_ratios),
                 ("financials", "قوائم مالية", "financials_ok", "financials_fail", do_financials),
                 ("company", "company", "company_ok", "company_fail", do_company),
                 ("dividends", "توزيعات", "dividends_ok", "dividends_fail", do_dividends))
    victims = []
    for i, st in enumerate(stocks):
        for name, label, okk, failk, fn in ENDPOINTS:
            ok, err = fn(st)
            if ok:
                counters[okk] += 1
            elif "429" in str(err):
                victims.append((st, label, okk, failk, fn))   # تُلتقط لاحقاً — لا عدّ الآن
            else:
                note_fail(counters, failk, label, st["symbol"], err)
        if (i + 1) % 25 == 0:
            print("  ... %d/%d أساسيات" % (i + 1, len(stocks)))
    if victims:
        print("  🔁 جولة التقاط 429 (أساسيات): %d طلباً بعد تهدئة..." % len(victims))
        time.sleep(20)
        for st, label, okk, failk, fn in victims:
            ok, err = fn(st)
            if ok:
                counters[okk] += 1
            else:
                note_fail(counters, failk, label + " (بعد الالتقاط)", st["symbol"], err)

    # ── المسار البديل عن ratios من القوائم (04-08ب — خطة الاستقلال) ──
    # يُستخدم **فقط عند فشل ratios** لذلك السهم (تراجع موسوم — لا يغير مصدر القيم إن عاد
    # ratios يعمل): profitMargins = ni/rev×100 | ROE = ni/equity×100 | D/E = debt/equity
    # (يمر بكاشف المقياس القائم). جعله المسار الأساسي قرار لاحق ليس هنا.
    stmt_fb = 0
    for st in stocks:
        sym = st["symbol"]
        sc = scratch.get(sym) or {}
        if sc.get("ratiosOk") or "stmt" not in sc:
            continue   # ratios نجح (لا حاجة) أو القوائم فشلت (لا مصدر)
        m = sc["stmt"]
        ni, rev = m.get("netIncome"), m.get("totalRevenue")
        eq, debt = m.get("stockholdersEquity"), m.get("totalDebt")
        SRC = "sahmk /financials (مشتق — تراجع عن ratios)"
        wrote = False
        if ni is not None and rev:
            setf(st, "profitMargins", round(ni / rev * 100, 1), SRC)
            wrote = True
        if ni is not None and eq:
            setf(st, "returnOnEquity", round(ni / eq * 100, 1), SRC)
            wrote = True
        if debt is not None and eq:
            de_raw[sym] = debt / eq              # نسبة — تمر بكاشف المقياس القائم كبقية القيم
            de_src[sym] = SRC
            wrote = True
        if wrote:
            stmt_fb += 1
    if stmt_fb:
        print("  🔀 تراجع القوائم: %d سهماً فشل ratios له فاشتُقت نسبه من /financials (موسومة «مشتق»)" % stmt_fb)

    # ── دمج sectorFinancials للبنوك — بعد اكتمال الجولتين (ROA من ratios + C/I من القوائم) ──
    for st in stocks:
        if "Bank" not in (st.get("industry") or ""):
            continue
        sc = scratch.get(st["symbol"], {})
        if not sc:
            continue   # فشل كلا المصدرين — الكتلة القديمة تبقى بلا مساس ولا ختم
        old_sf = st.get("sectorFinancials") or {}
        sf = dict(old_sf)
        sf["type"] = "bank"
        written_now = []
        # قرار المحلل (الخيار ب): costToIncome المحتسبة لا تُكتب — legacy تبقى؛
        # المشتق يُخزن معلوماتياً في costToIncomeDerived (المحرك لا يقرؤه)
        for k, v in (("ROA", round(sc["roa"], 2) if sc.get("roa") is not None else None),
                     ("costToIncomeDerived", sc.get("ctiDerived")),
                     ("totalRevenue", sc.get("bankRevenue")),
                     ("operatingIncome", sc.get("bankOpIncome"))):
            if v is not None:
                sf[k] = v
                written_now.append(k)
        sf.setdefault("costToIncome", None)   # المفتاح لازم لمسار البنوك — القديمة إن وجدت باقية
        meta = {"type", "source", "updatedAt", "sahmkFields", "legacyFields", "error"}
        sf["sahmkFields"] = sorted(written_now)
        sf["legacyFields"] = sorted(k for k in old_sf if k not in meta and k not in written_now)
        sf["source"] = ("sahmk (ratios+financials)" if not sf["legacyFields"]
                        else "mixed: sahmk(%s) + yfinance-legacy(%s)" % (
                            "،".join(sf["sahmkFields"]), "،".join(sf["legacyFields"])))
        sf["updatedAt"] = today   # يصدق على sahmkFields حصراً
        st["sectorFinancials"] = sf
    # debtHealth: لا تُكتب إطلاقاً (قرار المحلل بند 1) — الكتل الموسومة بالترحيل تبقى محتسبة.

    # ── جدول مقارنة C/I للبنوك (قرار المحلل — الخيار ب): legacy المحتسبة مقابل المشتق ──
    # (04-08ب) المشتق من **القوائم حصراً** — مستقل عن ratios؛ وعمود rev/opi يشخص None
    # بالقيم بدل الصمت (غياب المدخل ≠ تساوي الإيراد ≠ فشل الجلب)
    bank_rows = []
    for st in stocks:
        if "Bank" not in (st.get("industry") or ""):
            continue
        sf = st.get("sectorFinancials") or {}
        sc = scratch.get(st["symbol"]) or {}
        legacy_ci = sf.get("costToIncome")
        derived = sf.get("costToIncomeDerived")
        diff = round(derived - legacy_ci, 1) if (derived is not None and legacy_ci is not None) else None
        rev, opi = sc.get("bankRevenue"), sc.get("bankOpIncome")
        why = ("" if derived is not None
               else "قوائم لم تُجلب" if "stmt" not in sc
               else "opi≥rev (لا تفصيل مصروفات)" if (rev and opi is not None and opi >= rev)
               else "rev/opi غائب من القوائم")
        bank_rows.append((st["symbol"], legacy_ci, derived, diff, rev, opi, why))
    if bank_rows:
        print("🏦 مقارنة C/I البنوك (الاشتقاق مجمد بقرار المحلل — legacy هي المحتسبة؛ المصدر: القوائم لا ratios):")
        print("   %-6s | %-14s | %-12s | %-6s | %-22s | %s" % ("بنك", "legacy (محتسب)", "مشتق سهمك", "الفرق", "rev | opi (قوائم)", "سبب الغياب"))
        for sym, lc, dv, df, rev, opi, why in bank_rows:
            print("   %-6s | %-14s | %-12s | %-6s | %-22s | %s"
                  % (sym, lc, dv, ("%+.1f" % df) if df is not None else "—",
                     "%s | %s" % (rev, opi), why))

    # تحديث وسم مصدر financials الإجمالي بعد الجولتين — يميز ratios عن تراجع القوائم
    # (04-08ب: حتى لا يتوارى مصدر القيم إن عاد ratios يعمل لاحقاً)
    for st in stocks:
        parts = st.get("financialsParts") or {}
        if not parts or not st.get("financials"):
            continue
        srcs = [str(v.get("source", "")) for v in parts.values() if isinstance(v, dict)]
        if not any(s.startswith("sahmk") for s in srcs):
            continue   # لم يُجلب شيء لهذا السهم — الوسوم القديمة كما هي
        has_ratios = any(s == "sahmk analytics/ratios" for s in srcs)
        has_stmt_fb = any("مشتق — تراجع" in s for s in srcs)
        base = ("sahmk-ratios+statements" if has_ratios and not has_stmt_fb
                else "sahmk-statements (تراجع — ratios فشل)" if has_stmt_fb and not has_ratios
                else "sahmk-ratios+statements (مختلط)" if has_ratios
                else "sahmk-statements")
        legacy_left = sorted(k for k, v in parts.items()
                             if isinstance(v, dict) and not str(v.get("source", "")).startswith("sahmk"))
        st["financialsSource"] = (base if not legacy_left
                                  else "mixed: %s + موروث (%s) — انظر financialsParts" % (base, "، ".join(legacy_left)))
        st["financialsUpdated"] = today   # يصدق على حقول sahmk في financialsParts حصراً

    # ── فحص current_price (م-1): غيابه الواسع يجمد حارس P/B للسوق كله ──
    # (اتساق سلطة الإنذارات — شرط الناقد 2ب): التسمية تطابق السلوك المختار — «تحذير
    # جسيم بتدهور آمن» لا «حاكم»: لا سلطة إيقاف له عمداً، لأن أثره الفعلي تدهور آمن
    # (pbConsistent=None → compute-valuation يجمد P/B = الوضع المحافظ)، وإسقاط التشغيلة
    # كلها لعطب مدخل تقييم عقوبة غير متناسبة تحرم الأسعار والفنية السليمة من النشر.
    cp_total = counters["company_cp_ok"] + counters["company_cp_miss"]
    if cp_total and counters["company_cp_miss"] / cp_total > 0.5:
        print("⚠️ تحذير جسيم (تدهور آمن): company.current_price غائب في %d/%d من الردود (>50%%) —"
              % (counters["company_cp_miss"], cp_total))
        print("   حارس اتساق P/B غير قابل للتحقق للسوق كله → compute-valuation سيجمد P/B للجميع (محافظ).")
        print("   pbConsistent كُتب None (غير قابل للتحقق) لا False — راجع شكل /company/ قبل اعتماد التقييم.")

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
            st.setdefault("financialsParts", {})["debtToEquity"] = {
                "source": de_src.get(st["symbol"], "sahmk analytics/ratios"), "asOf": today}
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

    def _tasi_once():
        resp, err = api.get("/historical/TASI/?interval=1d&from=%s&to=%s" % (last, today))
        rows, _ = parse_candles(resp)   # للمؤشر نستخدم close الخام — عدّاد السقوط لا يعنيه
        # (04-08ب) السبب الفعلي بدل (None): نجاح HTTP بجسد بلا شموع يُسمى باسمه
        if rows:
            return rows, None
        if err:
            return [], err              # فشل نقل — الكود وجسد الرد (من Api.get)
        shape = (sorted(resp.keys())[:6] if isinstance(resp, dict) else type(resp).__name__)
        return [], "استجابة 200 بلا شموع — الشكل: %s" % shape

    rows, reason = _tasi_once()
    if not rows:
        # فشل عرضي على الأرجح — محاولة إضافية واحدة متباعدة قبل أي حكم (تشخيص أعمى ممنوع)
        print("  ⚠️ historical/TASI بلا بيانات (%s) — محاولة متباعدة بعد 10ث..." % reason)
        time.sleep(10)
        rows, reason = _tasi_once()
    if not rows and not hist:
        counters["tasi_fail"] += 1
        print("  ✗ تاريخ TASI: %s — لا تاريخ محلي: فشل حاكم (المُستدعي يجهض قبل الكتابة)" % reason)
        return None
    if not rows:
        counters["tasi_api_stale"] += 1
        print("  ⚠️ واجهة TASI فشلت (%s) — نُكمل بالتاريخ المحلي القائم (%d يوماً، آخره %s)"
              % (reason, len(hist), hist[-1]["date"]))
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


def migrate_legacy_tags(data):
    """ترحيل وسوم المصدر لمرة واحدة (قرار المحلل ج-2 — data-source v3، idempotent):
    - debtHealth القائمة: source=yfinance-legacy + asOf=تاريخ آخر تحديث فعلي (liquidityDebtUpdated)
    - cashflow القائمة: source=legacy-unknown + asOf=null (كاتبها مجهول — لا يُختلق تاريخ)
    - financials القائمة بلا خريطة: financialsParts أولية توسم كل حقوقها موروثة بمصدرها
      وasOf الحقيقي (financialsUpdated القديم) — أساس صدق الوسم الحقلي في الدمج اللاحق.
    لا يغير أي قيمة محتسبة — وسم مصدر خالص."""
    lu = str(data.get("liquidityDebtUpdated") or "")[:10] or None
    n_dh = n_cf = n_fp = 0
    for s in data.get("stocks", []):
        dh = s.get("debtHealth")
        if dh and "source" not in dh:
            dh["source"] = "yfinance-legacy"
            dh["asOf"] = lu
            n_dh += 1
        cf = s.get("cashflow")
        if cf and "source" not in cf:
            cf["source"] = "legacy-unknown"
            cf["asOf"] = None
            n_cf += 1
        if s.get("financials") and "financialsParts" not in s:
            src = (s.get("financialsSource") or "legacy") + " (موروث)"
            asof = str(s.get("financialsUpdated") or "")[:10] or None
            s["financialsParts"] = {k: {"source": src, "asOf": asof} for k in s["financials"]}
            n_fp += 1
    if n_dh or n_cf or n_fp:
        print("🏷 ترحيل وسوم المصدر (لمرة واحدة): debtHealth %d | cashflow %d | financialsParts %d"
              % (n_dh, n_cf, n_fp))
    return n_dh + n_cf + n_fp


# القائمة المغلقة لإسناد فروق الوضع الأسبوعي (معيار المحلل المحدّث — مرحلتان)
ATTR_FIELDS = (
    ("ocf", lambda s: (s.get("cashflow") or {}).get("ocf")),
    ("revenueGrowth", lambda s: (s.get("financials") or {}).get("revenueGrowth")),
    ("profitMargins", lambda s: (s.get("financials") or {}).get("profitMargins")),
    ("roe", lambda s: (s.get("financials") or {}).get("returnOnEquity")),
    ("de", lambda s: (s.get("financials") or {}).get("debtToEquity")),
    ("costToIncome", lambda s: (s.get("sectorFinancials") or {}).get("costToIncome")),
)

# مسارات مدخلات الوضع اليومي بالترتيب — لتسمية جذر أول فرق
DAILY_INPUT_PATHS = (
    ("currentPrice",), ("previousClose",), ("dailyChange",), ("netLiquidity",),
    ("dailyExtra", "high52w"), ("dailyExtra", "atrPct"), ("dailyExtra", "avgVol20"),
    ("dailyExtra", "avgVol50"), ("dailyExtra", "ema50d"), ("dailyExtra", "rsi14d"),
    ("dailyTechnical", "macdD"), ("dailyTechnical", "macdSignalD"),
    ("relativeStrength", "return3m"), ("relativeStrength", "return6m"),
    ("relativeStrength", "return12m"), ("relativeStrength", "rsTasi3m"),
    ("relativeStrength", "rsTasi6m"),
    ("valuation", "pb"), ("valuation", "dividendYield"),
    ("weeklyTechnical", "sma200w"), ("weeklyTechnical", "ema40w"),
    ("weeklyTechnical", "rsi14w"), ("weeklyTechnical", "macdW"),
    ("weeklyTechnical", "macdSignalW"), ("weeklyTechnical", "sma200wSlope"),
    ("financials", "profitMargins"), ("financials", "returnOnEquity"),
    ("financials", "revenueGrowth"), ("financials", "debtToEquity"),
    ("financials", "currentRatio"), ("cashflow", "ocf"), ("cashflow", "netIncome"),
    ("sectorFinancials", "costToIncome"), ("sectorFinancials", "ROA"),
)


def _path_val(stock, path):
    v = stock
    for k in path:
        if not isinstance(v, dict):
            return None
        v = v.get(k)
    return v


def _first_input_diff(sa, sb):
    for path in DAILY_INPUT_PATHS:
        va, vb = _path_val(sa, path), _path_val(sb, path)
        if va != vb:
            return ".".join(path), va, vb
    return None


def shadow_compare(path_a, path_b, mode="daily"):
    """معيار القبول الحاكم (قرار المحلل بند 7 + معيار الإسناد المحدّث بمرحلتين):
      --mode daily : صفر فرق حرفي متوقع؛ أي فرق يُطبع مع جذره (أول حقل مدخلات مختلف).
      --mode weekly: فروق النقاط تُسند حصرياً للقائمة المغلقة (ocf/revenueGrowth/
                     profitMargins/roe/de/costToIncome) — فرق بلا إسناد = «غير مُسنَد» خروج 1.
    بوابة المعقولية: تغير تصنيف >25% من الكون، أو انزياح أحادي الاتجاه شاذ في حقل واحد
    (تفعيلها الرقمي الموثق: الحقل تغير عند ≥20% من الكون و≥95% من تغيراته بإشارة واحدة)
    → «⛔ توقف وتحقيق» بخروج 3 (يعلو كل شيء).
    حارس الفراغ (درس 04-08): يفحص **الأختام لا العمر** — الملفان بمسار واحد، أو الطرف
    الأول بلا ختم priceSource=sahmk-direct-v1، أو lastUpdated متطابق في الطرفين =
    «مقارنة فارغة» بخروج 2. نضارة اليوم المرجعي مسؤولية المشغل (المقارنة التاريخية
    المتعمدة مشروعة — فحص عمرٍ ضد «اليوم» كان سيرفضها زوراً).
    الخروج: 3 معقولية > 2 فراغ > 1 فروق/غير مُسنَد > 0 اعتماد."""
    a = json.load(open(path_a))
    b = json.load(open(path_b))
    # حارس الفراغ — قبل أي حكم
    empty_reasons = []
    if os.path.abspath(path_a) == os.path.abspath(path_b):
        empty_reasons.append("الملفان مسار واحد")
    if a.get("priceSource") != "sahmk-direct-v1":
        empty_reasons.append("الطرف الأول (المفترض ناتج الجالب) بلا ختم sahmk-direct-v1 — لم يُجدد")
    if a.get("lastUpdated") and a.get("lastUpdated") == b.get("lastUpdated"):
        empty_reasons.append("ختم lastUpdated متطابق في الطرفين (%s) — الهدف لم يُجدد" % a.get("lastUpdated"))
    if empty_reasons:
        print("⚠️ مقارنة فارغة — لا حكم اعتماد منها: %s" % "؛ ".join(empty_reasons))
        print("   (جدد ناتج الجالب أولاً ثم أعد المقارنة — خروج 2 كي لا يُقرأ نجاح زائف)")
        sys.exit(2)

    SA = {s["symbol"]: s for s in a.get("stocks", [])}
    SB = {s["symbol"]: s for s in b.get("stocks", [])}
    common = sorted(set(SA) & set(SB))
    only_a = sorted(set(SA) - set(SB))
    only_b = sorted(set(SB) - set(SA))
    isc = lambda s: s.get("investmentScore") or {}
    diffs = []
    for sym in common:
        ta, tb = isc(SA[sym]).get("total"), isc(SB[sym]).get("total")
        ca, cb = isc(SA[sym]).get("classification"), isc(SB[sym]).get("classification")
        if ta != tb or ca != cb:
            diffs.append((sym, ta, tb, ca, cb))
    print("المقارنة الظلية (%s): %s ↔ %s" % (mode, path_a, path_b))
    print("أسهم مشتركة: %d | في الأول فقط: %d %s | في الثاني فقط: %d %s"
          % (len(common), len(only_a), only_a[:5], len(only_b), only_b[:5]))

    # ── تعدادات العبور (بالأسماء) ──
    BUY = ("strong_buy", "buy", "conditional_buy")
    cc = lambda s: isc(s).get("classCode")
    tt = lambda s: isc(s).get("total")
    entered = [s2 for s2 in common if cc(SA[s2]) in BUY and cc(SB[s2]) not in BUY]
    left = [s2 for s2 in common if cc(SA[s2]) not in BUY and cc(SB[s2]) in BUY]
    def crossings(th):
        up = [s2 for s2 in common if tt(SB[s2]) is not None and tt(SA[s2]) is not None
              and tt(SB[s2]) < th <= tt(SA[s2])]
        dn = [s2 for s2 in common if tt(SB[s2]) is not None and tt(SA[s2]) is not None
              and tt(SA[s2]) < th <= tt(SB[s2])]
        return up, dn
    up50, dn50 = crossings(50)
    up65, dn65 = crossings(65)
    if diffs:
        print("تعدادات العبور (القديم=الطرف الثاني ← الجديد=الأول):")
        print("  عائلة الشراء: دخل %d %s | خرج %d %s" % (len(entered), entered[:8], len(left), left[:8]))
        print("  عتبة 50 (قاعدة الإغلاق): صعد %d %s | هبط %d %s" % (len(up50), up50[:8], len(dn50), dn50[:8]))
        print("  عتبة 65 (الظل): صعد %d %s | هبط %d %s" % (len(up65), up65[:8], len(dn65), dn65[:8]))

    # ── بوابة المعقولية (خروج 3 — يعلو كل شيء) ──
    plaus = []
    class_changed = [d[0] for d in diffs if d[3] != d[4]]
    if common and len(class_changed) > 0.25 * len(common):
        plaus.append("تغير تصنيف %d/%d سهماً (>25%% من الكون)" % (len(class_changed), len(common)))
    for fname, getter in ATTR_FIELDS:
        deltas = []
        for sym in common:
            va, vb = getter(SA[sym]), getter(SB[sym])
            if va is not None and vb is not None and va != vb:
                deltas.append(va - vb)
        if common and len(deltas) >= max(5, 0.2 * len(common)):
            same_dir = max(sum(1 for d in deltas if d > 0), sum(1 for d in deltas if d < 0))
            if same_dir >= 0.95 * len(deltas):
                plaus.append("انزياح أحادي الاتجاه شاذ في %s: %d تغيراً %.0f%% بإشارة واحدة"
                             % (fname, len(deltas), same_dir / len(deltas) * 100))
    if plaus:
        print("⛔ توقف وتحقيق — بوابة المعقولية:")
        for p in plaus:
            print("   • %s" % p)
        return 3

    # ── جدول البنوك العشرة (وضع أسبوعي — موحد مع جدول الجالب، قرار المحلل الخيار ب) ──
    if mode == "weekly":
        banks = [s2 for s2 in common if "Bank" in (SB[s2].get("industry") or SA[s2].get("industry") or "")]
        if banks:
            print("جدول البنوك — C/I (الاشتقاق مجمد؛ legacy هي المحتسبة):")
            print("  %-6s | %-16s | %-16s | %-22s | %s" % ("بنك", "محتسب قديم", "محتسب جديد", "مشتق سهمك (معلوماتي)", "الفرق مشتق−محتسب"))
            for s2 in banks:
                old_ci = (SB[s2].get("sectorFinancials") or {}).get("costToIncome")
                sf_new = SA[s2].get("sectorFinancials") or {}
                new_ci = sf_new.get("costToIncome")
                derived = sf_new.get("costToIncomeDerived")
                diff = round(derived - new_ci, 1) if (derived is not None and new_ci is not None) else None
                print("  %-6s | %-16s | %-16s | %-22s | %s"
                      % (s2, old_ci, new_ci, derived, ("%+.1f" % diff) if diff is not None else "—"))

    if not diffs and not only_a and not only_b:
        print("✅ صفر فرق في total والتصنيف لكل الأسهم — معيار الاعتماد متحقق")
        return 0

    # ── تقرير الفروق حسب الوضع ──
    exit_code = 1
    if mode == "daily":
        print("⛔ فروق (متوقعها صفر حرفياً في اليومي): %d سهماً — الجذر = أول حقل مدخلات مختلف" % len(diffs))
        for sym, ta, tb, ca, cb in diffs[:30]:
            root = _first_input_diff(SA[sym], SB[sym])
            root_s = ("%s: %s→%s" % (root[0], root[2], root[1])) if root else "لا فرق مدخلات مرصود في المسارات المفحوصة"
            print("   %s: total %s→%s | تصنيف %s→%s | الجذر: %s" % (sym, tb, ta, cb, ca, root_s))
    else:   # weekly — تقرير الإسناد للقائمة المغلقة
        unattributed = []
        print("فروق الأسبوعي: %d سهماً — الإسناد للقائمة المغلقة (ocf/revenueGrowth/profitMargins/roe/de/costToIncome):" % len(diffs))
        print("  %-6s | %-55s | %s" % ("سهم", "الحقول المتغيرة (قديم→جديد)", "فرق النقاط"))
        for sym, ta, tb, ca, cb in diffs:
            changed = []
            for fname, getter in ATTR_FIELDS:
                va, vb = getter(SA[sym]), getter(SB[sym])
                if va != vb:
                    changed.append("%s: %s→%s" % (fname, vb, va))
            dscore = (ta - tb) if (ta is not None and tb is not None) else None
            if changed:
                print("  %-6s | %-55s | %+d" % (sym, "؛ ".join(changed)[:55], dscore if dscore is not None else 0))
            else:
                unattributed.append(sym)
                print("  %-6s | %-55s | %+d  ⚠️ غير مُسنَد" % (sym, "—", dscore if dscore is not None else 0))
        if unattributed:
            print("⛔ فروق غير مُسنَدة حصرياً للقائمة المغلقة: %d %s — الاعتماد متوقف (خروج 1)"
                  % (len(unattributed), unattributed[:10]))
        elif diffs:
            print("✅ كل الفروق مُسنَدة للقائمة المغلقة — راجعها يدوياً ثم قرر الاعتماد")
    if len(diffs) > 30 and mode == "daily":
        print("   ... و%d فرقاً آخر" % (len(diffs) - 30))
    return exit_code


def probe_ratios(api):
    """استكشاف شكل طلب /analytics/ratios/ (تشغيلة 04-08ب: 400 لكل الرموز حتى بالتركيبة
    «المؤكدة») — بالترتيب: بلا معاملات إطلاقاً (الدرس المثبت من financials)، ثم المفردات،
    ثم الثنائيات، ثم الكاملة القديمة. يطبع أول ناجحة بقيمها وجسد الخطأ لكل فاشلة.
    الميزانية: ≤16 طلباً (8 تركيبات × رمزين، توقف عند أول نجاح لكل رمز) — إيميل جودة
    سهمك (72×400 في 24س) يوجب تقليل الضجيج: التجربة مرة واحدة بقرار، لا تكرار أعمى."""
    combos = [
        "",                                              # بلا معاملات — درس financials
        "?metrics=core",
        "?history=latest",
        "?period=annual",
        "?history=latest&period=annual",
        "?history=latest&metrics=all",
        "?period=annual&metrics=all",
        "?history=latest&period=annual&metrics=all",     # الكاملة القديمة (المرفوضة إنتاجياً)
    ]
    for sym in ("2222", "1180"):
        print("═" * 50)
        print("فحص /analytics/ratios/%s/" % sym)
        for c in combos:
            resp, err = api.get("/analytics/ratios/%s/%s" % (sym, c))
            if resp is None:
                print("  %-45s ✗ %s" % (c or "(بلا معاملات)", err))
                continue
            print("  %-45s ✅" % (c or "(بلا معاملات)"))
            body = resp
            for k in ("data", "results"):
                if isinstance(body.get(k), dict):
                    body = body[k]
            if isinstance(body, list):
                body = body[0] if body else {}
            rat = body.get("ratios") or {}
            km = body.get("key_metrics") or {}
            print("  💵 القيم: roe=%s | roa=%s | net_margin=%s | operating_margin=%s | debt_to_equity=%s"
                  % (rat.get("roe"), rat.get("roa"), rat.get("net_margin"),
                     rat.get("operating_margin"), rat.get("debt_to_equity")))
            print("     key_metrics: %s" % ({k2: km[k2] for k2 in list(km)[:6]} if km else "غائبة"))
            if not rat:
                print("     ⚠️ نجح الطلب لكن ratios غائبة — مفاتيح الجسد: %s" % sorted(body.keys())[:8])
            break
    print("طلبات مستهلكة: %d" % api.requests_made)


def probe_financials(api):
    """تجربة تركيبات معاملات /financials/ — من معاملات SDK سهمك الرسمي (v0.15.0):
    type/period/statement_period/history/metrics/result/include_partial"""
    combos = [
        "",                                   # المؤكدة 04-08: تعمل بلا معاملات
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
                # طباعة القيم لا الأنواع فقط (مطلب 04-08 — فحص مصروفات البنوك بالأرقام)
                p = parse_financials(resp) or {}
                rev, opi = p.get("totalRevenue"), p.get("operatingIncome")
                exp = (rev - opi) if (rev is not None and opi is not None) else None
                cti = round(exp / rev * 100, 1) if (exp is not None and rev) else None
                print("  💵 آخر سنة كاملة (%s / fy=%s): revenue=%s | operating_income=%s | gross_profit=%s"
                      % (p.get("reportDate"), p.get("fiscalYear"), rev, opi, p.get("grossProfit")))
                print("     مصروفات مشتقة=%s | C/I مشتق=%s%% | net_income=%s | OCF=%s | FCF=%s | نمو الإيرادات=%s%%"
                      % (exp, cti, p.get("netIncome"), p.get("ocf"), p.get("fcf"), p.get("revenueGrowth")))
                print("     reporting=%s" % (p.get("reporting"),))
                if rev is not None and opi is not None and opi >= rev:
                    print("     ⚠️ operating_income >= total_revenue — لا تفصيل مصروفات في القوائم أيضاً (توثيق الاستحالة)")
                break
    print("طلبات مستهلكة: %d" % api.requests_made)


# ═══════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="جالب مدخلات المختبر من سهمك (sahmk-direct-v1 / data-source v3)")
    ap.add_argument("--data", default="", help="مسار stocks-data.json (إلزامي لأوضاع الجلب — لا افتراضي حمايةً)")
    ap.add_argument("--weekly", action="store_true", help="جلب أسبوعي: شموع 1w + الأساسيات")
    ap.add_argument("--symbols", default="", help="رموز محددة مفصولة بفواصل (اختبار)")
    ap.add_argument("--probe-financials", action="store_true", help="فحص تركيبات /financials/ ثم خروج")
    ap.add_argument("--probe-ratios", action="store_true", help="فحص تركيبات /analytics/ratios/ بأجساد الأخطاء ثم خروج (≤16 طلباً)")
    ap.add_argument("--key-file", default="", help="ملف المفتاح (بديل SAHMK_KEY)")
    ap.add_argument("--tasi-history", default="", help="مسار tasi-history.json (افتراضي بجوار --data)")
    ap.add_argument("--shadow-compare", nargs=2, metavar=("A.json", "B.json"),
                    help="معيار الاعتماد الحاكم: مقارنة total والتصنيف بين ملفين بعد المحرك — بلا شبكة ولا مفتاح")
    ap.add_argument("--mode", choices=("daily", "weekly"), default="daily",
                    help="وضع المقارنة الظلية: daily=صفر فرق حرفي مع جذر أول فرق مدخلات | weekly=تقرير إسناد للقائمة المغلقة")
    args = ap.parse_args()

    # المقارنة الظلية: محلية خالصة — قبل أي اشتراط مفتاح
    if args.shadow_compare:
        sys.exit(shadow_compare(*args.shadow_compare, mode=args.mode))

    key = os.environ.get("SAHMK_KEY", "")
    if not key and args.key_file:
        key = open(args.key_file).read().strip()
    if not key:
        sys.exit("⛔ لا مفتاح: مرر SAHMK_KEY في البيئة أو --key-file (يُمنع وضعه في الكود/المستودع)")

    api = Api(key)

    if args.probe_financials:
        probe_financials(api)
        return
    if args.probe_ratios:
        probe_ratios(api)
        return

    if not args.data:
        sys.exit("⛔ --data إلزامي لأوضاع الجلب")
    with open(args.data) as f:
        data = json.load(f)

    # ترحيل وسوم المصدر لمرة واحدة (قرار المحلل ج-2) — وسم خالص، صفر تغيير قيم
    migrate_legacy_tags(data)

    stocks = [s for s in data.get("stocks", []) if s.get("symbol")]
    if args.symbols:
        want = {x.strip() for x in args.symbols.split(",") if x.strip()}
        stocks = [s for s in stocks if s["symbol"] in want]
    if not stocks:
        sys.exit("⛔ لا أسهم مطابقة في %s" % args.data)

    hist_file = args.tasi_history or os.path.join(os.path.dirname(os.path.abspath(args.data)), "tasi-history.json")

    n = len(stocks)
    batches = (n + 49) // 50
    budget = batches + n + 2 + (n * 5 if args.weekly else 0)
    print("═" * 60)
    print("سيف تداول — جالب سهمك المباشر (sahmk-direct-v1)")
    print("أسهم: %d | الوضع: %s" % (n, "أسبوعي (1w + أساسيات)" if args.weekly else "يومي"))
    print("ميزانية الطلبات المتوقعة: ~%d (quotes %d + 1d %d + TASI/summary 2%s) — الحصة 5000/يوم"
          % (budget, batches, n,
             " + 1w %d + ratios %d + financials %d + company %d + dividends %d" % (n, n, n, n, n) if args.weekly else ""))
    print("(التقدير happy-path — إعادات 429/الأخطاء قد تزيد المستهلك الفعلي؛ الإيقاع الذاتي ~%.1f طلب/ث)" % RATE_PER_SEC)
    print("═" * 60)

    counters = {k: 0 for k in (
        "quotes_ok", "quotes_fail", "quotes_batch_fail", "daily_ok", "daily_fail",
        "weekly_ok", "weekly_fail", "ratios_ok", "ratios_fail",
        "financials_ok", "financials_fail", "revgrowth_ok", "revgrowth_miss",
        "ocf_ok", "bank_cti_ok", "bank_cti_flat", "bank_cti_na",
        "company_ok", "company_fail", "company_cp_ok", "company_cp_miss",
        "dividends_ok", "dividends_fail",
        "adj_fb_rows_1d", "adj_fb_syms_1d", "adj_fb_rows_1w", "adj_fb_syms_1w",
        "tasi_ok", "tasi_fail", "tasi_api_stale", "regime_ok", "regime_fail")}
    adj_diag = {"partial": [], "full": []}   # تشخيص شموع 1w الفاقدة adjusted_close (رمز + تواريخ)

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
        fetch_weekly(api, stocks, counters, stamp_utc, adj_diag)
        print("🏦 الأساسيات (ratios/financials/company/dividends)...")
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
    print("الطلبات المستهلكة فعلياً: %d / ميزانية ~%d | رشقات 429 المصادفة: %d (كلها عولجت بالإيقاع/Retry-After/الالتقاط)"
          % (api.requests_made, budget, api.hits_429))
    fail_types = []
    for label, ok_k, fail_k in (
            ("أسعار", "quotes_ok", "quotes_fail"), ("شموع يومية", "daily_ok", "daily_fail"),
            ("شموع أسبوعية", "weekly_ok", "weekly_fail"), ("نسب مالية", "ratios_ok", "ratios_fail"),
            ("قوائم مالية", "financials_ok", "financials_fail"),
            ("company", "company_ok", "company_fail"), ("توزيعات", "dividends_ok", "dividends_fail")):
        ok, fl = counters[ok_k], counters[fail_k]
        if ok + fl == 0:
            continue
        pct = fl / (ok + fl) * 100
        mark = "⚠️" if pct > 10 else "✅"
        print("%s %s: نجح %d | فشل %d (%.0f%%)" % (mark, label, ok, fl, pct))
        if pct > 10:
            fail_types.append(label)
    if counters["financials_ok"] + counters["financials_fail"]:
        print("قوائم: نمو الإيرادات متاح %d | غير متاح %d (من الناجحة) | OCF حي %d | C/I بنوك مشتق %d | مصروفات غير مفصلة %d | مدخل C/I غائب %d"
              % (counters["revgrowth_ok"], counters["revgrowth_miss"], counters["ocf_ok"],
                 counters["bank_cti_ok"], counters["bank_cti_flat"], counters["bank_cti_na"]))
    print("TASI: %s%s | نظام السوق: %s" % (
        "✅" if counters["tasi_ok"] else "✗",
        " (واجهة فشلت — تاريخ محلي)" if counters["tasi_api_stale"] else "",
        "✅" if counters["regime_ok"] else "✗"))
    # قاعدة adjusted_close (04-08): الفاقدة تُسقط من السلسلة المعدلة — لا خلط خام/معدل.
    # الإسقاط الجزئي = ملاحظة معدودة بالرمز والتواريخ؛ الإنذار الحاكم فقط لسهم فقد
    # سلسلته المعدلة كلها (تغيير اصطلاح كامل — ملحق 24-07).
    if counters["adj_fb_rows_1d"]:
        print("ℹ️ 1d: %d شمعة بلا adjusted_close أُسقطت من سلسلة العوائد المعدلة عند %d سهماً (المؤشرات الخام سليمة)"
              % (counters["adj_fb_rows_1d"], counters["adj_fb_syms_1d"]))
    if adj_diag["partial"]:
        print("ℹ️ 1w: شموع بلا adjusted_close أُسقطت من السلسلة (لا خلط) عند %d سهماً:" % len(adj_diag["partial"]))
        for line in adj_diag["partial"][:10]:
            print("   • %s" % line)
        if len(adj_diag["partial"]) > 10:
            print("   • ... و%d آخرين" % (len(adj_diag["partial"]) - 10))
    if adj_diag["full"]:
        # (اتساق سلطة الإنذارات — شرط الناقد 2أ): الصياغة تطابق الواقع المختار — السهم
        # يُتخطى (يُعدّ في weekly_fail وكتلته القديمة تبقى بختمها) فلا تغيير اصطلاح يقع
        # أصلاً، ولا سلطة إيقاف للإنذار. التصعيد لقرار وسم يلزم فقط إن أريد لاحقاً
        # بديل خام لهذه الأسهم (ملحق 24-07).
        print("⚠️ %d سهماً فقد adjusted_close لسلسلته الأسبوعية كلها: %s"
              % (len(adj_diag["full"]), adj_diag["full"][:10]))
        print("   المعالجة الواقعة: تخطٍّ (ضمن عداد شموع أسبوعية الفاشلة) والكتلة القديمة باقية بختمها —")
        print("   لا خلط ولا تغيير اصطلاح. أي بديل خام مستقبلاً لهذه الأسهم = قرار وسم (ملحق 24-07)؛")
        print("   واستمرار الحالة أسابيع = مؤشر تحول مصدر يستحق تحقيقاً.")
    if fail_types:
        print("⛔ فشل يتجاوز 10%% في: %s — لا كتابة، الملف القديم يبقى كما هو" % "، ".join(fail_types))
        print("   (ترحيل الوسوم إن جرى هذه التشغيلة لم يُحفظ مع الحجب — سلوك صحيح: يعاد آلياً بحكم idempotent)")
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
