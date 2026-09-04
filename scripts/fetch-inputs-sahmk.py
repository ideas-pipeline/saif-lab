#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch-inputs-sahmk.py — جالب المنصة القائمة بذاتها (sahmk-direct-v3)
====================================================================
المرجع الحاكم: docs/requirements-v3.md — سهمك مصدر الحقيقة الوحيد، لا legacy،
لا دمج Yahoo، لا ظلية. مصفوفة المطابقة: docs/mapping-v3.md.

التشغيل
-------
    SAHMK_KEY=xxx python3 scripts/fetch-inputs-sahmk.py --data stocks-data.json [أوضاع]
      (افتراضي)            يومي: quotes + شموع 1d تزايدية + اشتقاق أسبوعي + Z + تاسي/نظام
      --weekly             يضيف: ratios + financials + company (+sector/industry) + dividends
      --maintain-universe  صيانة الكون من /companies/ (شهري): جديد يُضاف، مشطوب يُوسم delisted
                           وتُغلق توصياته المفتوحة بوسم delisted (بوابة تشغيلة أولى — شكل
                           النقطة غير مؤكد بالفحص)
      --symbols 1010,2222  حصر (استطلاع) — قرارات الكون الكامل (deScale/equitySource) تُقرأ
                           من المثبت ولا يعاد حسمها (درس هشاشة العينات)
      --probe-financials / --probe-ratios   استكشاف أشكال (أبقيا عمداً: أثبتا نفعهما مرتين
                           عند تغير سلوك الواجهة — قرار معماري معلن)

عمق التأسيس (محدّث بقرار المحلل 05-08 بعد حقيقة العمق)
--------------------------------------------------------
    حقيقة مقيسة: تاريخ سهمك يبدأ ~2022-06 (~210 أسابيع) — Z الأسبوعي القديم أنتج
    «قادرو Z: 0» فأُعيد تصميمه **يومياً** (§3.4 المحدثة): يحتاج 199+100=299 جلسة
    كحد أدنى، ونافذته الكاملة 199+756=955 جلسة ≈ 1340 يوماً تقويمياً — ضمن المتاح.
    **التأسيس يجلب 2600 يوم تقويمي** (سقف طموح: يخدم نمو SMA200W الأسبوعي المتزايد
    مع السنين ونافذة Z الكاملة)، ثم **تزايدي يومياً** من آخر تاريخ مخزن
    (مخزن الشموع: candles/{sym}.json بجوار --data، كتابة ذرية).
    توزيع العمق الفعلي (أسابيع/جلسات) يُطبع نهاية كل تشغيلة — قرارات العتبات بالأرقام.

اصطلاحات السلاسل (§6 — تغييرها = وسم نسخة)
-------------------------------------------
    - الأسبوعية مشتقة محلياً من 1d **المعدل**: أسبوع تداول أحد-خميس (مفتاح الأسبوع =
      isocalendar(التاريخ+يوم) — الأحد ينزاح لاثنين ISO)، إغلاق الأسبوع = آخر جلسة فيه،
      والمؤشرات على **الأسابيع المكتملة فقط** (تفعيل حتمي: كل مجموعة أسبوع عدا الأخيرة
      في السلسلة تعد مكتملة — الأخيرة غير مكتملة دوماً، تحفظاً).
    - لكل غرض سلسلته: الاتجاه/الامتداد/Z على المعدل؛ القوة النسبية على **الخام** مقابل
      تاسي السعري؛ ATR وقيمة التداول على الخام.
    - dailyChange من change_percent مباشرة — لا اشتقاق previous_close (§6-5).
    - شمعة اليوم غير النهائية (is_final/partial، واحتياطياً: تاريخ اليوم قبل 15:10
      الرياض) تُستبعد من التخزين والمؤشرات اليومية — الأسبوعي محمي بإسقاط أسبوعه الأخير.
    - Z يومي (قرار محلل 05-08): سعر/SMA200D−1 معايراً بسلسلة النسبة اليومية،
      نافذة ≤756 وحد أدنى 100 مشاهدة — العتبات (|Z|<1/2/3) كما هي.
    - RSI ‏Wilder حصراً في الإطارين؛ MACD ‏12/26/9 بإشارة EMA9 (بذرة SMA9).
    - 3م=63، 6م=126، 12م=250 جلسة؛ ‏12-1 = من t−250 إلى t−21.

حراس المعقولية (§8 — جزء من العقد): الراسب = null + تسجيل في stock.guardRejected
(تُعاد بناؤها كل تشغيلة بمرفوضات التشغيلة نفسها). بوابات الفشل الموحدة (§7):
فشل >10% لأي نوع، غياب عوائد تاسي، انهيار تغطية (قادرو SMA200W أو Z ينخفضون >10%
عن التشغيلة السابقة — العدادان يثبتان في data.coverage)، حارس الانزياح الجماعي
(حقل مالي يتغير باتجاه واحد لدى >80% من فئة ≥5) ⇒ خروج 1 **قبل الكتابة**.

قرارات مثبتة بين التشغيلات: data.deScaleDecision (§6-8ب) وdata.equitySource (§6-8أ) —
تُحسم على الكون الكامل مرة واحدة (equitySource: الحقل الصريح إن حضر ≥90% وطابق
الاشتقاق أصول−مطلوبات بوسيط فرق <2%، وإلا derived).

تساهل موثق (تحسين الناقد ج): liquidityGate الغائبة (فشل جلب يومية السهم) تُعامل
fail-open لدى المستهلكين (`passed`, True) — عمداً: الغياب عارض جلب لا حكم سيولة،
وحجب سهم كان سليماً لعطل شبكة عابر أسوأ من عرضه؛ أول يومية ناجحة تعيد الحكم الفعلي.

ما بقي من v2.1 (بنص §9-4): الإيقاع 2.5ط/ث + Retry-After + جولة التقاط 429، أجساد
الأخطاء (أول 3 لكل نوع)، الكتابة الذرية، «لا كتابة عند فشل الأسعار كلياً»،
تاسي: الفراغ المشروع (200 بلا شموع + محلي ≤4 أيام) ليس فشلاً.
"""
import json, math, os, sys, time, argparse, tempfile, statistics
import urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

BASE = "https://api.sahmk.sa/api/v1"
RIYADH = timezone(timedelta(hours=3))
RATE_PER_SEC = 1.5   # مواءمة 16-08: حد Starter الموثق 100/دقيقة (جدول الخطط في
                     # docs/sahmk-api-docs-snapshot.md) — كان 2.5/ث=150/د فوق الحد
                     # (جذر أسراب 429 التاريخية)؛ 1.5/ث=90/د بهامش أمان لأن الخنق
                     # «على مستوى المفتاح والحساب معاً» (شرط الناقد — لا 1.6).
                     # القياس: شموع 248: ~99ث→~165ث | اليومي الكامل ~503 طلباً ≈
                     # ‏5.6 دقيقة صافي إيقاع — مقبول لتشغيلة إقفال مجدولة.
FOUNDING_CAL_DAYS = 2600          # ~7.1 سنة — انظر «عمق التأسيس» أعلاه
LIQUIDITY_GATE_SAR = 1_000_000    # §2 بوابة السيولة (وسيط قيمة تداول 20 جلسة)
Z_MIN_OBS, Z_WINDOW = 100, 756    # §3.4 بعد قرار المحلل 05-08: Z على الإطار اليومي
                                  # (سعر/SMA200D−1؛ 100 مشاهدة ≈ 300 جلسة، نافذة 3 سنوات)
PARTIAL_CUTOFF_RIYADH = (15, 10)  # قاعدة الشمعة الجزئية الاحتياطية (نقاش المالك 05-08)
DIVCAL_WINDOW_DAYS = 45           # نافذة مفكرة التوزيعات (عقد المحلل 14-08)


# ═══════════════════ دوال نقية: مؤشرات ═══════════════════

def calc_sma(vals, period):
    if len(vals) < period:
        return None
    return round(sum(vals[-period:]) / period, 2)


def calc_ema(vals, period, dp=2):
    if len(vals) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(vals[:period]) / period
    for p in vals[period:]:
        ema = p * k + ema * (1 - k)
    return round(ema, dp)


def calc_rsi_wilder(vals, period=14):
    """RSI بتنعيم Wilder — الاصطلاح الموحد للإطارين (§6-3)"""
    if len(vals) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(vals)):
        ch = vals[i] - vals[i - 1]
        gains.append(max(ch, 0)); losses.append(max(-ch, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_g / avg_l), 1)


def calc_macd(vals, fast=12, slow=26, signal=9, dp=4):
    """MACD سلسلة كاملة + إشارة EMA9 ببذرة SMA9 (§6-3)"""
    if len(vals) < slow + signal:
        return None, None, None
    k_f, k_s = 2 / (fast + 1), 2 / (slow + 1)
    ema_f = sum(vals[:fast]) / fast
    ema_s = sum(vals[:slow]) / slow
    line = []
    for i, p in enumerate(vals):
        if i >= fast:
            ema_f = p * k_f + ema_f * (1 - k_f)
        if i >= slow:
            ema_s = p * k_s + ema_s * (1 - k_s)
            line.append(ema_f - ema_s)
    if len(line) < signal:
        return None, None, None
    k = 2 / (signal + 1)
    sig = sum(line[:signal]) / signal
    for m in line[signal:]:
        sig = m * k + sig * (1 - k)
    return round(line[-1], dp), round(sig, dp), round(line[-1] - sig, dp)


def calc_atr(highs, lows, closes, period=14):
    n = len(closes)
    if n < period + 1 or len(highs) != n or len(lows) != n:
        return None
    trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
           for i in range(1, n)]
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return round(atr, 4)


def calc_sma_slope_weekly(weeks, period=200, lag=4):
    if len(weeks) < period + lag:
        return None
    now = sum(weeks[-period:]) / period
    prev = sum(weeks[-(period + lag):-lag]) / period
    return round((now - prev) / prev * 100, 2) if prev else 0


def period_return(vals, days):
    if len(vals) < days + 1 or not vals[-(days + 1)]:
        return None
    return round((vals[-1] - vals[-(days + 1)]) / vals[-(days + 1)] * 100, 2)


def return_12_1(vals):
    """اصطلاح 12-1: العائد من t−250 إلى t−21 (§6-8)"""
    if len(vals) < 251 or not vals[-251] or not vals[-21]:
        return None
    return round((vals[-21] - vals[-251]) / vals[-251] * 100, 2)


# ═══════════════════ دوال نقية: الاشتقاق الأسبوعي وZ ═══════════════════

def week_key(date_str):
    """مفتاح أسبوع التداول السعودي (أحد-خميس): إزاحة يوم ثم أسبوع ISO —
    الأحد+1=اثنين يفتتح أسبوع ISO، والخميس+1=جمعة يبقى فيه (§6-1)"""
    d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    iso = d.isocalendar()
    return (iso[0], iso[1])


def derive_weekly(dates, values):
    """يشتق إغلاقات الأسابيع **المكتملة** (كل مجموعة عدا الأخيرة — تحفظ حتمي).
    يعيد (قائمة الإغلاقات الأسبوعية بترتيب زمني، عددها)"""
    if not dates:
        return [], 0
    weeks = []
    cur_key, cur_val = None, None
    for d, v in zip(dates, values):
        k = week_key(d)
        if k != cur_key:
            if cur_key is not None:
                weeks.append(cur_val)
            cur_key = k
        cur_val = v      # آخر جلسة في الأسبوع = إغلاقه
    # المجموعة الأخيرة غير مكتملة دوماً — لا تُضاف
    return weeks, len(weeks)


def derive_weekly_pairs(dates, values):
    """كأعلاه لكن يعيد أزواج (تاريخ آخر جلسة في الأسبوع، الإغلاق) للأسابيع المكتملة —
    لسلاسل الرسم (نحتاج تاريخ البداية)."""
    if not dates:
        return []
    out = []
    cur_key, cur_d, cur_v = None, None, None
    for d, v in zip(dates, values):
        k = week_key(d)
        if k != cur_key:
            if cur_key is not None:
                out.append((cur_d, cur_v))
            cur_key = k
        cur_d, cur_v = d, v
    return out


def shift_months(date_str, n):
    """يزيح YYYY-MM-DD بعدد أشهر (تقريب اليوم إلى 28 كحد — كافٍ لاشتقاق فهرسي تقريبي)"""
    y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])
    m2 = m - 1 + n
    return "%04d-%02d-%02d" % (y + m2 // 12, m2 % 12 + 1, min(d, 28))


def build_series(dates, raw, adj_pairs):
    """سلاسل الرسم المضغوطة (الموجة 1 — تفعيل الرسم التفاعلي): لكل مدة {start, p[, iv]}
    بلا تواريخ لكل نقطة — الواجهة تشتق التواريخ بالفهرس التقريبي (العقد في mapping §3):
      d30/d90: إغلاقات يومية **خام** (جلسات تداول)
      w52/w156: أسبوعية مشتقة **معدلة** (أسابيع مكتملة — اصطلاح §6-1 نفسه، تتسق مع SMA200W)
      mAll: آخر إغلاق **خام** لكل شهر ميلادي للتاريخ كله (iv: M — وقد تصير Q بميزانية الحجم)
    قواعد الغياب: سهم بلا مخزن كافٍ → المدد المتاحة فقط (d30≥5 جلسات، d90>30،
    ‏w52≥8 أسابيع، w156>52، mAll≥6 أشهر).
    التقريب: منزلتان، وثلاث لسهم سعره < 1 ريال."""
    # (كان TODO-SR): حقل `levels` نُفذ بمواصفة §4-ب المختومة — انظر build_levels أدناه.
    if not dates:
        return None
    nd = 3 if raw[-1] < 1 else 2
    R = lambda seq: [round(v, nd) for v in seq]
    out = {}
    n = len(dates)
    if n >= 5:
        w = min(30, n)
        out["d30"] = {"start": dates[-w], "p": R(raw[-w:])}
    if n > 30:
        w = min(90, n)
        out["d90"] = {"start": dates[-w], "p": R(raw[-w:])}
    wk = derive_weekly_pairs([d for d, _ in adj_pairs], [v for _, v in adj_pairs])
    if len(wk) >= 8:
        w = min(52, len(wk))
        out["w52"] = {"start": wk[-w][0], "p": R([v for _, v in wk[-w:]])}
    if len(wk) > 52:
        w = min(156, len(wk))
        out["w156"] = {"start": wk[-w][0], "p": R([v for _, v in wk[-w:]])}
    months = []   # (تاريخ آخر جلسة في الشهر، إغلاقها الخام)
    cur_m, cur_d, cur_v = None, None, None
    for d, v in zip(dates, raw):
        if d[:7] != cur_m:
            if cur_m is not None:
                months.append((cur_d, cur_v))
            cur_m = d[:7]
        cur_d, cur_v = d, v
    if cur_m is not None:
        months.append((cur_d, cur_v))   # الشهر الجاري بآخر إغلاق متاح (مبسطة — معلن)
    if len(months) >= 6:
        out["mAll"] = {"start": months[0][0], "p": R([v for _, v in months]), "iv": "M"}
    return out or None


# ═══════════ الدعم والمقاومة الإرشادية (§4-ب المختوم — عرض إرشادي محض) ═══════════
# حوكمة صريحة: صفر نقاط، صفر فلاتر، صفر أثر على criteria v3 — المحرك لا يقرأ levels.

LEVELS_K = 5              # fractal swings (Williams)
LEVELS_WINDOW = 500       # نافذة الكشف ~سنتان
LEVELS_MIN_SESSIONS = 250 # دونه: الكبرى فقط أو «تاريخ غير كافٍ»
CAPACT_THRESHOLD = 0.15   # فرق عائد خام/معدل > 15% = إجراء رأسمالي شبه يقيني (حد التذبذب ±10%)


def derive_capadj(rows):
    """السلسلة «الخام المعدل للإجراءات الرأسمالية فقط» (§4-ب ش-1) — مشتقة محلياً:
    فرق العائد اليومي الخام عن المعدل > 15% بين إغلاقين = إجراء رأسمالي؛ عامل
    التعديل = نسبة الفرق نفسها مطبقاً على كل ما قبل يوم الإجراء. التوزيعات النقدية
    (فرق ≤ 15%) تبقى غير معدلة — السوق يتذكر السعر الاسمي.
    الكشف الملتبس (عامل خارج [0.2، 5] أو قفزة > 15% بلا معدل للمقارنة) → يعاد
    بفهرسه لتقييد النافذة لما بعده (الحارس ب).
    **قيد معرفي معلن (ملاحظة الناقد 5):** توزيع نقدي استثنائي يفوق 15% من السعر
    سيُقرأ هنا إجراءً رأسمالياً زوراً (الكاشف لا يفرق بنيوياً) — الحالة نادرة في
    السوق السعودي (العوائد المعتادة 1-8%) وبوابة التشغيلة الأولى (طباعة كل
    المكتشفين للتحقق اليدوي) هي صمام الأمان.
    يعيد (closes, highs, lows, vols, dates, actions[(date, factor, idx)], ambiguous[(date, idx)])"""
    n = len(rows)
    closes = [r[1] for r in rows]
    highs = [r[3] for r in rows]
    lows = [r[4] for r in rows]
    actions, ambiguous = [], []
    for i in range(1, n):
        r0, r1 = rows[i - 1][1], rows[i][1]
        a0, a1 = rows[i - 1][2], rows[i][2]
        if not r0 or not r1:
            continue
        raw_ret = r1 / r0
        if a0 and a1:
            adj_ret = a1 / a0
            if adj_ret and abs(raw_ret / adj_ret - 1) > CAPACT_THRESHOLD:
                f = raw_ret / adj_ret
                if 0.2 <= f <= 5:
                    actions.append((rows[i][0], round(f, 4), i))
                else:
                    ambiguous.append((rows[i][0], i))
        elif abs(raw_ret - 1) > CAPACT_THRESHOLD:
            ambiguous.append((rows[i][0], i))   # قفزة فوق حد التذبذب بلا معدل يحسمها
    for _, f, idx in actions:
        for j in range(idx):
            closes[j] *= f
            highs[j] *= f
            lows[j] *= f
    return (closes, highs, lows, [r[5] for r in rows], [r[0] for r in rows],
            actions, ambiguous)


def _round_step(p):
    """سلم الأرقام المستديرة المنصوص: ≥20→مضاعفات 5 | ‏5-20→1 | ‏<5→0.5"""
    return 5.0 if p >= 20 else 1.0 if p >= 5 else 0.5


def build_levels(rows, atr14, prev, stamp):
    """§4-ب حرفياً: swings ‏k=5 على نافذة 500 + كبرى + حجم-عند-سعر على شبكة 1.01^n
    مطلقة + دمج بسماحية max(2%، 0.5×ATR14) بسقف عرض 2×السماحية + قوة ثلاثية +
    أرقام مستديرة توسيماً + مانع الرفرفة ضد **المعروض** المخزن (prev)."""
    if not rows:
        return None
    closes, highs, lows, vols, dates, actions, ambiguous = derive_capadj(rows)
    out = {"updatedAt": stamp, "basis": "raw-capadj", "since": dates[0]}
    if actions:
        out["capActions"] = [{"date": d, "factor": f} for d, f, _ in actions]
    start = 0
    if ambiguous:
        start = ambiguous[-1][1] + 1
        out["restricted"] = True
        out["restrictedFrom"] = dates[start] if start < len(dates) else dates[-1]
        out["since"] = dates[start] if start < len(dates) else dates[-1]
    price = closes[-1]
    nd = 3 if price < 1 else 2
    R = lambda v: round(v, nd)
    # ── الكبرى (المكوّن 3): 52أ بأعلى high/أدنى low + أقصى المتاح بوسم since الصادق ──
    # حارس بيانات: قيم غير موجبة (صفوف معطوبة low=0 مرصودة في الخام) لا تدخل الحساب
    h_all = [v for v in highs[start:] if v and v > 0]
    l_all = [v for v in lows[start:] if v and v > 0]
    if h_all and l_all:
        out["majors"] = {"high52": R(max(h_all[-251:])), "low52": R(min(l_all[-251:])),
                         "maxAvail": R(max(h_all)), "minAvail": R(min(l_all))}
    n_eff = len(closes) - start
    if n_eff < LEVELS_MIN_SESSIONS:
        out["insufficientHistory"] = True
        if not out.get("majors"):
            out["note"] = "التاريخ غير كافٍ لمستويات موثوقة"
        out["price"] = R(price)
        return out
    # ── نافذة العمل: آخر 500 جلسة (بعد أي تقييد) ──
    w0 = max(start, len(closes) - LEVELS_WINDOW)
    wH, wL, wV, wC = highs[w0:], lows[w0:], vols[w0:], closes[w0:]
    k = LEVELS_K
    sH = [v if (v and v > 0) else float("-inf") for v in wH]   # المعطوب لا يكون قمة
    sL = [v if (v and v > 0) else float("inf") for v in wL]    # ولا قاعاً
    pts = []   # (سعر، حجم الجلسة)
    for i in range(k, len(sH) - k):
        if sH[i] > max(sH[i - k:i]) and sH[i] > max(sH[i + 1:i + k + 1]) and sH[i] > 0:
            pts.append((sH[i], wV[i]))
        if sL[i] < min(sL[i - k:i]) and sL[i] < min(sL[i + 1:i + k + 1]) and sL[i] != float("inf"):
            pts.append((sL[i], wV[i]))
    # ── حجم-عند-سعر: سلال 1% لوغاريتمية مرساة على 1.01^n من 1 ريال ──
    LN = math.log(1.01)
    bins = {}
    for i in range(len(wC)):
        lo_, hi_ = wL[i], wH[i]
        if not lo_ or not hi_ or lo_ <= 0:
            continue
        b0, b1 = int(math.log(lo_) / LN), int(math.log(hi_) / LN)
        share = (wV[i] or 0) / (b1 - b0 + 1)
        for b in range(b0, b1 + 1):
            bins[b] = bins.get(b, 0) + share
    node_bins = {b for b in bins
                 if bins[b] > bins.get(b - 1, 0) and bins[b] > bins.get(b + 1, 0)}
    def hits_node(lo_, hi_):
        b0, b1 = int(math.log(lo_) / LN), int(math.log(hi_) / LN)
        return any(b in node_bins for b in range(b0, b1 + 1))
    # ── الدمج بوصلة مفردة مسقوفاً: سماحية max(2%، 0.5×ATR14)، عرض ≤ 2×السماحية ──
    zones = []
    for p, v in sorted(pts):
        if zones:
            z = zones[-1]
            tol = max(0.02 * z["c"], 0.5 * (atr14 or 0))
            if abs(p - z["c"]) <= tol and (max(z["hi"], p) - min(z["lo"], p)) <= 2 * tol:
                z["lo"], z["hi"] = min(z["lo"], p), max(z["hi"], p)
                z["sumv"] += (v or 1)
                z["sumpv"] += p * (v or 1)
                z["c"] = z["sumpv"] / z["sumv"]
                z["t"] += 1
                continue
        zones.append({"lo": p, "hi": p, "c": p, "t": 1, "sumv": v or 1, "sumpv": p * (v or 1)})
    # ── القوة والوسوم — التأكيد الأدنى للعرض: لمستان ──
    final = []
    for z in zones:
        if z["t"] < 2:
            continue
        node = hits_node(z["lo"], z["hi"])
        strength = ("strong" if (z["t"] >= 3 or (z["t"] >= 2 and node)) else "medium")
        tags = []
        step = _round_step(z["c"])
        if abs(z["c"] - round(z["c"] / step) * step) <= 0.005 * z["c"]:
            tags.append("round")
        if node:
            tags.append("volnode")
        final.append({"lo": R(z["lo"]), "hi": R(z["hi"]), "c": R(z["c"]),
                      "strength": strength, "touches": z["t"], "tags": tags})
    # ── مانع الرفرفة (ش-3): الثبات ضد المعروض المخزن — استبدال فقط عند ابتعاد >1% ──
    prev_zones = []
    if prev:
        for key in ("supports", "resistances"):
            prev_zones.extend(prev.get(key) or [])
        if prev.get("inside"):
            prev_zones.append(prev["inside"])
    used_prev = set()   # (ملاحظة الناقد 2) منطقة معروضة «تُستهلك» بأول مطابقة —
    for z in final:     # فلا تثبّت منطقتين محسوبتين مختلفتين على المركز القديم نفسه
        for j, pz in enumerate(prev_zones):
            if j in used_prev:
                continue
            pc = pz.get("c")
            if pc and abs(z["c"] - pc) <= 0.01 * pc:
                z["lo"], z["hi"], z["c"] = pz["lo"], pz["hi"], pc
                used_prev.add(j)
                break
    # ── الاختيار (ش-2): داخل المنطقة لا يُعد؛ أقرب دعمين/مقاومتين من خارجها ──
    inside = next((z for z in final if z["lo"] <= price <= z["hi"]), None)
    sup = sorted((z for z in final if z is not inside and z["hi"] < price),
                 key=lambda z: -z["hi"])[:2]
    res = sorted((z for z in final if z is not inside and z["lo"] > price),
                 key=lambda z: z["lo"])[:2]
    out["supports"], out["resistances"] = sup, res
    if inside:
        out["inside"] = inside            # «السعر داخل منطقة تقريبية الآن»
    # الجانب الفارغ (ش-2-2) يشترط تجاوز الكبرى أيضاً — «فوق كل مستويات التاريخ المتاح».
    # هامش 2% لأن high الجلسة الجارية نفسها يتجاوز إغلاقها دوماً («عند أعلى المتاح»)
    mj = out.get("majors") or {}
    if not res and (not mj or price >= mj.get("maxAvail", price) * 0.98):
        out["noResistanceAbove"] = True   # «لا مقاومة معروفة فوق السعر (عند أعلى المتاح)»
    if not sup and (not mj or price <= mj.get("minAvail", price) * 1.02):
        out["noSupportBelow"] = True
    # جملة السياق العرضية الوحيدة: سعر ضمن 1×ATR من حافة أقرب منطقة
    if atr14:
        if sup and price - sup[0]["hi"] <= atr14:
            out["nearZone"] = "support"
        elif res and res[0]["lo"] - price <= atr14:
            out["nearZone"] = "resistance"
    out["price"] = R(price)
    return out


def series_bytes(stocks):
    return sum(len(json.dumps(s.get("series"), separators=(",", ":")).encode())
               for s in stocks if s.get("series"))


def enforce_series_budget(stocks, cap_bytes=800 * 1024):
    """ميزانية حجم صارمة لسلاسل الرسم: السقف الافتراضي +800KB للإضافة الكلية.
    التقليص بالترتيب المعلن: mAll→ربع سنوي (iv=Q) ثم إسقاط w156 ثم إسقاط mAll.
    يعيد (الحجم النهائي بالبايت، مستوى التقليص المطبق)."""
    size = series_bytes(stocks)
    level = 0
    if size > cap_bytes:
        level = 1
        for s in stocks:
            m = (s.get("series") or {}).get("mAll")
            if m and m.get("iv") == "M":
                keep = list(range(len(m["p"]) - 1, -1, -3))[::-1]
                m["start"] = shift_months(m["start"], keep[0])
                m["p"] = [m["p"][i] for i in keep]
                m["iv"] = "Q"
        size = series_bytes(stocks)
        print("📉 ميزانية series: تجاوز — قُلّصت mAll إلى ربع سنوية (iv=Q) → %.0fKB" % (size / 1024))
    if size > cap_bytes:
        level = 2
        for s in stocks:
            (s.get("series") or {}).pop("w156", None)
        size = series_bytes(stocks)
        print("📉 ميزانية series: ما زال متجاوزاً — أُسقطت w156 → %.0fKB" % (size / 1024))
    if size > cap_bytes:
        level = 3
        for s in stocks:
            (s.get("series") or {}).pop("mAll", None)
        size = series_bytes(stocks)
        print("📉 ميزانية series: ما زال متجاوزاً — أُسقطت mAll → %.0fKB" % (size / 1024))
    return size, level


def z_extension(daily_adj):
    """Z-امتداد — **الإطار اليومي** (قرار محلل 05-08 بعد حقيقة العمق: تاريخ سهمك يبدأ
    ~2022-06 فالأسبوعي أنتج «قادرو Z: 0»): ‏Z = (آخر إغلاق معدل/SMA200D − 1) معايراً
    بوسط وانحراف (pstdev) سلسلة النسبة اليومية نفسها؛ نافذة ≤756 جلسة (~3 سنوات)،
    حد أدنى 100 مشاهدة (≈300 جلسة) وإلا null؛ العتبات في المحرك كما هي.
    (تحسين الناقد ب باقٍ) سقف عرض ±10 — sd شبه صفري كان يسرب 2.4×10^15.
    يعيد (z, obs_count, sma200d_current)"""
    n = len(daily_adj)
    if n < 200:
        return None, 0, None
    prefix = [0.0]
    for v in daily_adj:
        prefix.append(prefix[-1] + v)
    ratios = []
    for i in range(199, n):
        sma_i = (prefix[i + 1] - prefix[i - 199]) / 200
        if sma_i:
            ratios.append(daily_adj[i] / sma_i - 1)
    obs = ratios[-Z_WINDOW:]
    sma_now = round((prefix[n] - prefix[n - 200]) / 200, 2)
    if len(obs) < Z_MIN_OBS:
        return None, len(obs), sma_now
    mu = statistics.mean(obs)
    sd = statistics.pstdev(obs)
    if sd == 0:
        return None, len(obs), sma_now
    z = (daily_adj[-1] / sma_now - 1 - mu) / sd
    return round(max(-10.0, min(10.0, z)), 2), len(obs), sma_now


# ═══════════════════ الشبكة ═══════════════════

class Api:
    def __init__(self, key):
        self.key = key
        self.requests_made = 0
        self.hits_429 = 0
        self._gap = 1.0 / RATE_PER_SEC
        self._last = 0.0

    def get(self, path, tries=3, timeout=25):
        url = BASE + path
        err = "unknown"
        for attempt in range(tries):
            w = self._gap - (time.monotonic() - self._last)
            if w > 0:
                time.sleep(w)
            self._last = time.monotonic()
            self.requests_made += 1
            try:
                req = urllib.request.Request(url, headers={"X-API-Key": self.key, "User-Agent": "Mozilla/5.0"})
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
                body = ""
                try:
                    body = e.read().decode("utf-8", "replace").strip()[:300]
                except Exception:
                    pass
                if body:
                    err = "%s — %s" % (err, body)
                if e.code in (400, 401, 403, 404):
                    return None, err
            except Exception as e:
                err = type(e).__name__
            if attempt < tries - 1:
                time.sleep(2 * (attempt + 1))
        return None, err


def unwrap_ratios(r):
    """(استعادة إصلاح d36fc83 الضائع في إعادة كتابة v3 + حارس نوع نهائي)
    نزول ratios الموحد: غلاف data/results ← قائمة جذرية ← «ratios» قد تكون
    **قائمة فترات** (الشكل المؤكد إنتاجياً: ratios[0].ratios.roe) → أحدث فترة
    (بreport_date/fiscal_year وإلا الأولى) → قاموس النسب المتداخل → شكل مسطح.
    يعيد (rat_dict, None) أو (None, وصف مسموع) — لا انهيار على أي نوع."""
    body = r
    if isinstance(body, dict):
        for k in ("data", "results"):
            if isinstance(body.get(k), (dict, list)):
                body = body[k]
                break
    if isinstance(body, list):
        dicts = [e for e in body if isinstance(e, dict)]
        if not dicts:
            return None, "قائمة جذرية بلا عناصر قاموسية"
        def _pd(e):
            return str(e.get("report_date") or e.get("fiscal_year") or e.get("period") or "")
        body = max(dicts, key=_pd) if any(_pd(e) for e in dicts) else dicts[0]
    if not isinstance(body, dict):
        return None, "بنية غير متوقعة (نوع %s)" % type(body).__name__
    rat = body.get("ratios")
    if isinstance(rat, list):
        dicts = [e for e in rat if isinstance(e, dict)]
        if dicts:
            def _pd2(e):
                return str(e.get("report_date") or e.get("fiscal_year") or "")
            rat = max(dicts, key=_pd2) if any(_pd2(e) for e in dicts) else dicts[0]
        else:
            rat = None
    if isinstance(rat, dict) and isinstance(rat.get("ratios"), dict):
        rat = rat["ratios"]
    if not isinstance(rat, dict) or not rat:
        if any(k in body for k in ("roe", "roa", "net_margin", "debt_to_equity")):
            rat = body   # شكل مسطح
    if not isinstance(rat, dict) or not rat:
        return None, "بنية غير متوقعة — مفاتيح: %s" % sorted(body.keys())[:8]
    # (تحسين الناقد 05-08) قاموس بلا أي مفتاح نسبة معروف = شكل مجهول — فشل مسموع
    # بدل قيم None صامتة تختم financialsUpdated بلا جديد
    if not any(k in rat for k in ("roe", "roa", "net_margin", "operating_margin", "debt_to_equity")):
        return None, "قاموس بلا مفاتيح نسب معروفة — مفاتيحه: %s" % sorted(rat.keys())[:8]
    return rat, None


def rows_of(resp, *keys):
    if resp is None:
        return []
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for k in keys:
            if isinstance(resp.get(k), list):
                return resp[k]
    return []


def note_fail(counters, key, label, sym, err, limit=3):
    counters[key] = counters.get(key, 0) + 1
    if counters[key] <= limit:
        print("  ✗ %s %s: %s" % (sym, label, err))
    elif counters[key] == limit + 1:
        print("  ✗ %s: ... (أول %d أسباب فقط)" % (label, limit))


def reject(st, field, value, reason, today):
    """حارس معقولية راسب → null موسوم (§8)"""
    st.setdefault("guardRejected", []).append(
        {"field": field, "value": value, "reason": reason, "date": today})
    return None


def run_with_429_sweep(stocks, process, counters, ok_key, fail_key, label):
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
        print("  🔁 التقاط 429 (%s): %d" % (label, len(victims)))
        time.sleep(20)
        for st in victims:
            ok, err = process(st)
            if ok:
                counters[ok_key] += 1
            else:
                note_fail(counters, fail_key, label + " (التقاط)", st["symbol"], err)


# ═══════════════════ مخزن الشموع (تزايدي) ═══════════════════

def candle_dir(data_path):
    d = os.path.join(os.path.dirname(os.path.abspath(data_path)), "candles")
    os.makedirs(d, exist_ok=True)
    return d


def load_candles(cdir, sym):
    p = os.path.join(cdir, sym + ".json")
    if os.path.exists(p):
        try:
            return json.load(open(p)).get("rows", [])
        except Exception:
            return []
    return []


def save_candles(cdir, sym, rows):
    p = os.path.join(cdir, sym + ".json")
    fd, tmp = tempfile.mkstemp(dir=cdir, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump({"symbol": sym, "rows": rows}, f)
    os.replace(tmp, p)


def parse_candles(resp):
    """صف الشمعة المخزن: [date, close, adjusted|null, high, low, volume] —
    المعدل الغائب يبقى null (لا خلط — يسقط من السلسلة المعدلة عند الاستهلاك).
    **قاعدة الشمعة الجزئية (نقاش المالك 05-08 — تشغيلة تفعيل والسوق مفتوح):**
    شمعة اليوم غير النهائية تُستبعد كلياً (لا تُخزن ولا تدخل المؤشرات اليومية) —
    أولاً بعلمي العقد is_final/partial (على الصف أو غلاف الرد للشمعة الأخيرة)،
    وإن غابا فالقاعدة الاحتياطية: شمعة بتاريخ اليوم والوقت قبل 15:10 الرياض.
    الاستبعاد يومي فقط — الاشتقاق الأسبوعي محمي أصلاً بإسقاط الأسبوع الأخير،
    والجلب التزايدي التالي (من آخر تاريخ مخزن) يلتقط الشمعة النهائية.
    يعيد (rows, partial_excluded)"""
    out = []
    env_final = resp.get("is_final") if isinstance(resp, dict) else None
    rows = rows_of(resp, "data", "candles", "history", "results")
    max_date = max((r.get("date", "") for r in rows if r.get("date")), default="")
    now_r = datetime.now(RIYADH)
    today_r = now_r.strftime("%Y-%m-%d")
    before_cutoff = (now_r.hour, now_r.minute) < PARTIAL_CUTOFF_RIYADH
    partial_excluded = 0
    for r in rows:
        if r.get("close") is None or r.get("high") is None or r.get("low") is None:
            continue
        d = r.get("date", "")
        row_flag = (r.get("is_final") is False) or (r.get("partial") is True)
        env_flag = (env_final is False and d == max_date)          # علم الغلاف يخص الأخيرة
        fallback = (r.get("is_final") is None and r.get("partial") is None
                    and env_final is None and d == today_r and before_cutoff)
        if row_flag or env_flag or fallback:
            partial_excluded += 1
            continue
        out.append([d, r["close"], r.get("adjusted_close"),
                    r["high"], r["low"], r.get("volume") or 0])
    out.sort(key=lambda x: x[0])
    return out, partial_excluded


# ═══════════════════ مراحل الجلب ═══════════════════

def fetch_quotes(api, stocks, counters, now_str, today):
    by = {s["symbol"]: s for s in stocks}
    syms = list(by)
    got = {}
    for i in range(0, len(syms), 50):
        batch = syms[i:i + 50]
        resp, err = api.get("/quotes/?identifiers=" + ",".join(batch))
        if resp is None:
            counters["quotes_batch_fail"] += 1
            print("  ✗ دفعة quotes: %s" % err)
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
        cp = q.get("change_percent")
        if cp is None:
            st["dailyChange"] = None   # (تحسين ج) لا يُترك قديم تحت سعر جديد — يُمسح صراحة
        if cp is not None:
            # حارس حد التذبذب ±10%+1 (§8) — الخرق شبهة بيانات لا حركة
            if abs(cp) > 11:
                st["dailyChange"] = reject(st, "dailyChange", cp, "تغير يومي خارج حد ±10%+1", today)
            else:
                st["dailyChange"] = round(cp, 2)
        if q.get("net_liquidity") is not None:
            st["netLiquidity"] = q["net_liquidity"]
        # عمود بحثي صامت (شرط الناقد 16-08 — نمط sma100w المختوم حرفياً): bid/ask صارا
        # في الاستجابة الدفعية الموثقة مجاناً — صفر طلبات إضافية. لا يستهلكه المحرك
        # ولا الواجهة؛ غرضه بناء تاريخ السبريد لمراجعة بوابة السيولة المسجلة (بعد 20 مغلقة).
        bid, ask = q.get("bid"), q.get("ask")
        if bid and ask and bid > 0 and ask > 0 and ask >= bid:
            st["bidAsk"] = {"bid": bid, "ask": ask,
                            "spreadPct": round((ask - bid) / ((ask + bid) / 2) * 100, 3),
                            "at": now_str}
        if q.get("volume") is not None:
            st["volume"] = q["volume"]
        st["priceUpdatedAt"] = now_str
        st["priceSource"] = "sahmk"
        counters["quotes_ok"] += 1
    return counters["quotes_ok"]


def fetch_candles_paged(api, sym, frm, to, counters):
    """مواءمة 16-08 (بتر /historical الصامت): الوثيقة الرسمية تنص «limit default 500,
    maximum 2000» مع has_more/offset — جلب تأسيسي (~1800 صف) بلا ترقيم يُبتر عند 500
    صامتاً. يمرر limit=2000 ويرقّم حتى اكتمال النطاق (سقف أمان 10 صفحات = 20 ألف صف).
    يعيد (rows, err, partial_excluded)."""
    rows_all, partial_total, offset = [], 0, 0
    err = None
    for _pg in range(10):
        resp, err = api.get("/historical/%s/?interval=1d&from=%s&to=%s&limit=2000&offset=%d"
                            % (sym, frm, to, offset))
        if resp is None:
            break
        page_rows, np_ = parse_candles(resp)
        partial_total += np_
        rows_all.extend(page_rows)
        raw_n = (resp.get("count") if isinstance(resp, dict) and resp.get("count") is not None
                 else len(rows_of(resp, "data", "candles", "history", "results")))
        if not (isinstance(resp, dict) and resp.get("has_more") is True) or not raw_n:
            break
        offset += raw_n
    return (rows_all if rows_all else None), err, partial_total


def fetch_daily_and_derive(api, stocks, counters, cdir, tasi, stamp, today):
    """1d تزايدي → الفنية اليومية + الاشتقاق الأسبوعي + Z + القوة النسبية + بوابة السيولة"""
    def process(st):
        sym = st["symbol"]
        rows = load_candles(cdir, sym)
        if not rows:
            # مسار التأسيس: نافذة كبيرة > 500 صف متوقعة → ترقيم إلزامي (مواءمة 16-08)
            frm = (datetime.now(timezone.utc) - timedelta(days=FOUNDING_CAL_DAYS)).strftime("%Y-%m-%d")
            new, err, n_partial = fetch_candles_paged(api, sym, frm, today, counters)
            resp = {} if new is not None else None
            new = new or []
        else:
            # التزايدي اليومي: نافذة صغيرة — نداء واحد بlimit=2000، وحارس فجوة مسموع
            frm = rows[-1][0]
            resp, err = api.get("/historical/%s/?interval=1d&from=%s&to=%s&limit=2000" % (sym, frm, today))
            new, n_partial = parse_candles(resp)
            if isinstance(resp, dict) and resp.get("has_more") is True:
                counters["hist_gap_truncated"] += 1
                if counters["hist_gap_truncated"] <= 3:
                    print("  ⚠️⚠️ %s: التزايدي أعاد has_more=true (فجوة > 2000 صف؟!) —"
                          " بتر محتمل، يحتاج جلباً تأسيسياً يدوياً" % sym)
        if n_partial:
            counters["partial_excluded"] += n_partial
        if resp is None and not rows:
            return False, err
        if new:
            new_dates = {r2[0] for r2 in new}
            rows = [r2 for r2 in rows if r2[0] not in new_dates] + new
            rows.sort(key=lambda x: x[0])
            save_candles(cdir, sym, rows)
        if len(rows) < 60:
            return False, (err or "شموع قليلة (%d)" % len(rows))

        dates = [r2[0] for r2 in rows]
        raw = [r2[1] for r2 in rows]
        highs = [r2[3] for r2 in rows]
        lows = [r2[4] for r2 in rows]
        vols = [r2[5] for r2 in rows]
        adj_pairs = [(d, r2[2]) for d, r2 in zip(dates, rows) if r2[2] is not None]
        counters["adj_dropped_rows"] += len(rows) - len(adj_pairs)

        last_close = raw[-1]
        # ── يومية على الخام (§6-2) ──
        atr = calc_atr(highs[-251:], lows[-251:], raw[-251:])
        tv = sorted(v * c for v, c in zip(vols[-20:], raw[-20:]))
        tv_med = round(tv[len(tv) // 2]) if tv else None
        m, s_, h = calc_macd(raw[-251:], dp=4)
        st["dailyExtra"] = {
            "lastClose": last_close, "lastDate": dates[-1],
            "ema50d": calc_ema(raw[-251:], 50, dp=4),
            "rsi14d": calc_rsi_wilder(raw[-251:]),
            "macdD": m, "macdSignalD": s_, "macdHistD": h,
            "atr14": atr,
            "atrPct": round(atr / last_close * 100, 2) if atr and last_close else None,
            "high52wClose": round(max(raw[-251:]), 2),
            "low20Close": round(min(raw[-20:]), 2),
            "avgVol20": int(sum(vols[-20:]) / min(20, len(vols))) if vols else None,
            "avgVol50": int(sum(vols[-50:]) / min(50, len(vols))) if vols else None,
            "tradingValueMedian20": tv_med,
            "sessions": len(rows),
            "updatedAt": stamp,
        }
        # بوابة السيولة (§2)
        st["liquidityGate"] = {"valueSar": tv_med, "threshold": LIQUIDITY_GATE_SAR,
                               "passed": bool(tv_med and tv_med >= LIQUIDITY_GATE_SAR)}
        # ── Z-الامتداد اليومي (قرار محلل 05-08) على المعدل ──
        adj_series = [round(a, 4) for _, a in adj_pairs]
        z, z_obs, sma200d = z_extension(adj_series)
        st["dailyExtra"]["zExt"] = z
        st["dailyExtra"]["zObs"] = z_obs
        st["dailyExtra"]["sma200d"] = sma200d
        # ── الأسبوعية المشتقة على المعدل (بلا Z — انتقل لليومي) ──
        weeks, n_weeks = derive_weekly([d for d, _ in adj_pairs], adj_series)
        last_adj = adj_pairs[-1][1] if adj_pairs else last_close
        wm, ws, wh = calc_macd(weeks, dp=3)
        st["weeklyTechnical"] = {
            "sma200w": calc_sma(weeks, 200),
            # عمود بحثي صامت (قرار المالك 13-08) — لا يستهلكه المحرك ولا الواجهة؛
            # غرضه قراءة افتراضية عند م-3: من كان سيدخله فلتر 100 أسبوع.
            # نفس اصطلاح الأسابيع المكتملة والحد الأدنى (≥100 أسبوعاً وإلا null)
            "sma100w": calc_sma(weeks, 100),
            "ema40w": calc_ema(weeks, 40, dp=2),
            "rsi14w": calc_rsi_wilder(weeks),
            "macdW": wm, "macdSignalW": ws, "macdHistW": wh,
            "sma200wSlope": calc_sma_slope_weekly(weeks),
            "priceRef": round(last_adj, 2),   # آخر إغلاق يومي — سعر الفلتر والمحاور (§6-1)
            "weeks": n_weeks,
            "derived": True, "updatedAt": stamp,
        }
        # ── سلاسل الرسم (الموجة 1) + مستويات §4-ب — من المخزن وقت الجلب ──
        st["series"] = build_series(dates, raw, adj_pairs)
        st["levels"] = build_levels(rows, atr, st.get("levels"), stamp)
        # ── القوة النسبية على الخام مقابل تاسي السعري (§3.3) ──
        r3, r6 = period_return(raw, 63), period_return(raw, 126)
        r121 = return_12_1(raw)
        rs = {"return3m": r3, "return6m": r6, "return12_1": r121,
              "basis": "raw-close vs tasi-price", "updatedAt": stamp}
        if r3 is not None and tasi.get("3m") is not None:
            rs["rsTasi3m"] = round(r3 - tasi["3m"], 2)
        if r6 is not None and tasi.get("6m") is not None:
            rs["rsTasi6m"] = round(r6 - tasi["6m"], 2)
        if r121 is not None and tasi.get("12_1") is not None:
            rs["rsTasi12_1"] = round(r121 - tasi["12_1"], 2)
        st["relativeStrength"] = rs
        return True, None

    run_with_429_sweep(stocks, process, counters, "daily_ok", "daily_fail", "شموع يومية")


def _fs_val(e, key, *nests):
    if isinstance(e, dict):
        if e.get(key) is not None:
            return e[key]
        for nkey in nests:
            d = e.get(nkey)
            if isinstance(d, dict) and d.get(key) is not None:
                return d[key]
    return None


def _latest_full_year(elements, nests):
    fy = [e for e in elements if _fs_val(e, "is_full_year", *nests) is True]
    return max(fy, key=lambda e: str(_fs_val(e, "report_date", *nests) or "")) if fy else None


def parse_financials(f):
    """/financials/ بلا معاملات — اصطلاح «آخر سنة مالية كاملة» لكل القوائم (§6-4)،
    والنمو من سنتين كاملتين متتاليتين فعلاً (fiscal_year فرق 1 وإلا سنة report_date)"""
    if not isinstance(f, dict):
        return None
    body = f
    for k in ("data", "results"):
        if isinstance(body.get(k), dict):
            body = body[k]
    inc = body.get("income_statements") or []
    cfs = body.get("cash_flows") or []
    bals = body.get("balance_sheets") or []
    if not isinstance(inc, list) or (not inc and not cfs and not bals):
        return {"_shape_error": "مفاتيح: %s" % sorted(body.keys())[:8]}
    NI, NC, NB = ("income",), ("cash_flows", "cash_flow"), ("balance",)
    out = {}
    li = _latest_full_year(inc, NI)
    if li:
        out["totalRevenue"] = _fs_val(li, "total_revenue", *NI)
        out["netIncome"] = _fs_val(li, "net_income", *NI)
        out["reportDate"] = _fs_val(li, "report_date", *NI)
        out["fiscalYear"] = _fs_val(li, "fiscal_year", *NI)
    lc = _latest_full_year(cfs, NC)
    if lc:
        out["ocf"] = _fs_val(lc, "operating_cash_flow", *NC)
        out["fcf"] = _fs_val(lc, "free_cash_flow", *NC)
        out["cfReportDate"] = _fs_val(lc, "report_date", *NC)
    lb = _latest_full_year(bals, NB)
    if lb:
        out["totalAssets"] = _fs_val(lb, "total_assets", *NB)
        out["totalLiabilities"] = _fs_val(lb, "total_liabilities", *NB)
        out["equityExplicit"] = _fs_val(lb, "stockholders_equity", *NB)
    fy_inc = sorted((e for e in inc if _fs_val(e, "is_full_year", *NI) is True),
                    key=lambda e: str(_fs_val(e, "report_date", *NI) or ""), reverse=True)
    if len(fy_inc) >= 2:
        def _yr(e):
            fy = _fs_val(e, "fiscal_year", *NI)
            try:
                return int(fy)
            except (TypeError, ValueError):
                rd = str(_fs_val(e, "report_date", *NI) or "")[:4]
                return int(rd) if rd.isdigit() else None
        y0, y1 = _yr(fy_inc[0]), _yr(fy_inc[1])
        r0 = _fs_val(fy_inc[0], "total_revenue", *NI)
        r1 = _fs_val(fy_inc[1], "total_revenue", *NI)
        if y0 is not None and y1 is not None and y0 - y1 == 1 and r0 is not None and r1:
            out["revenueGrowthRaw"] = round((r0 - r1) / abs(r1) * 100, 1)
    return out


def is_bank(st):
    """تعريف موحد (§3.1ب): sector مالي + نشاط بنكي — مطابقة متسامحة لتصنيفات سهمك
    (قيمها غير مؤكدة — بوابة تشغيلة أولى: طباعة عدد البنوك، المتوقع 10)"""
    sec = (st.get("sector") or "").lower()
    ind = (st.get("industry") or "").lower()
    sec_fin = ("financ" in sec) or ("مالية" in sec) or ("مصارف" in sec) or ("بنوك" in sec)
    ind_bank = ("bank" in ind) or ("بنك" in ind) or ("مصرف" in ind)
    return (sec_fin and ind_bank) if sec else ind_bank


def fetch_fundamentals(api, data, stocks, counters, today, full_universe):
    """ratios(core) + financials + company(+sector/industry) + dividends — أسبوعي"""
    de_raw = {}
    scratch = {}
    sector_changes = []

    def do_ratios(st):
        sym = st["symbol"]
        r, err = api.get("/analytics/ratios/%s/?history=latest&period=annual&metrics=core" % sym)
        if r is None:
            return False, err
        rat, uerr = unwrap_ratios(r)   # النزول الموحد (استعادة d36fc83) — فشله مسموع لا انهيار
        if rat is None:
            return False, uerr
        sc = scratch.setdefault(sym, {})
        sc["ratios"] = {k: rat.get(k) for k in ("roe", "roa", "net_margin", "operating_margin", "debt_to_equity")}
        if rat.get("debt_to_equity") is not None:
            de_raw[sym] = rat["debt_to_equity"]
        return True, None

    def do_financials(st):
        sym = st["symbol"]
        f, err = api.get("/financials/%s/" % sym)
        if f is None:
            return False, err
        p = parse_financials(f)
        if p is None or "_shape_error" in p:
            return False, (p or {}).get("_shape_error", "غير قابل للتفكيك")
        scratch.setdefault(sym, {})["fs"] = p
        return True, None

    def do_company(st):
        sym = st["symbol"]
        c, err = api.get("/company/%s/" % sym)
        if c is None:
            return False, err
        fn = c.get("fundamentals") or {}
        sc = scratch.setdefault(sym, {})
        sc["company"] = {"eps": fn.get("eps_ttm") if fn.get("eps_ttm") is not None else fn.get("eps"),
                         "bookValue": fn.get("book_value"), "peSource": fn.get("pe_ratio"),
                         "beta": fn.get("beta")}
        # sector/industry — العمود الفقري التصنيفي (§7): تغيره بين تشغيلتين = إنذار
        for fld in ("sector", "industry"):
            newv = c.get(fld)
            if newv:
                old = st.get(fld)
                if old and old != newv:
                    sector_changes.append((sym, fld, old, newv))
                st[fld] = newv
        return True, None

    def do_dividends(st):
        sym = st["symbol"]
        dv, err = api.get("/dividends/%s/?limit=50" % sym)
        if dv is None:
            return False, err
        now = datetime.now(timezone.utc)
        d365 = (now - timedelta(days=365)).strftime("%Y-%m-%d")
        rows = []
        for h2 in rows_of(dv, "history", "data"):
            ed = h2.get("eligibility_date") or h2.get("due_date") or h2.get("date")
            val = h2.get("value") if h2.get("value") is not None else h2.get("amount")
            if ed and val and val > 0:
                rows.append((ed, val))
        tot = sum(v for e, v in rows if d365 <= e <= today)
        # §3.5: العائد = مجموع 12 شهراً حصراً؛ لا توزيع خلال 18 شهراً → «لا يوزع»
        d548 = (now - timedelta(days=548)).strftime("%Y-%m-%d")
        basis = ("ttm12m" if tot > 0 else
                 "none-recent18m" if any(d548 <= e <= today for e, _ in rows) else "none")
        scratch.setdefault(sym, {})["div"] = (round(tot, 4), basis)
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
                victims.append((st, label, okk, failk, fn))
            else:
                note_fail(counters, failk, label, st["symbol"], err)
        if (i + 1) % 25 == 0:
            print("  ... %d/%d أساسيات" % (i + 1, len(stocks)))
    if victims:
        print("  🔁 التقاط 429 (أساسيات): %d" % len(victims))
        time.sleep(20)
        for st, label, okk, failk, fn in victims:
            ok, err = fn(st)
            if ok:
                counters[okk] += 1
            else:
                note_fail(counters, failk, label + " (التقاط)", st["symbol"], err)

    # ── حسم equitySource (§6-8أ) — كون كامل فقط، يثبت ──
    eq_src = (data.get("equitySource") or {}).get("choice")
    if full_universe:
        pres, diffs, n_fs = 0, [], 0
        for st in stocks:
            p = (scratch.get(st["symbol"]) or {}).get("fs")
            if not p:
                continue
            n_fs += 1
            a, l, e = p.get("totalAssets"), p.get("totalLiabilities"), p.get("equityExplicit")
            if e is not None:
                pres += 1
                if a is not None and l is not None and (a - l):
                    diffs.append(abs(e - (a - l)) / abs(a - l) * 100)
        if n_fs:
            pct = pres / n_fs * 100
            med = round(statistics.median(diffs), 2) if diffs else None
            eq_src = "explicit" if (pct >= 90 and med is not None and med < 2) else "derived"
            data["equitySource"] = {"choice": eq_src, "presentPct": round(pct, 1),
                                    "medianDiffPct": med, "checkedAt": today}
            print("⚖️ equitySource: %s (حاضر %.0f%%، وسيط فرق %s%%) — مثبت" % (eq_src, pct, med))
    if not eq_src:
        eq_src = "derived"
        print("⚠️ equitySource غير مثبت (جزئية قبل أول كاملة) — الاشتقاق أصول−مطلوبات مؤقتاً")

    # ── حسم مقياس D/E (§6-8ب) — مثبت ──
    dec = data.get("deScaleDecision")
    if full_universe and de_raw:
        vals = sorted(de_raw.values())
        med = vals[len(vals) // 2]
        dec = {"scale": "ratio×100" if med < 10 else "percent",
               "median": round(med, 3), "n": len(vals), "decidedAt": today}
        data["deScaleDecision"] = dec
        print("⚖️ deScaleDecision: %s (وسيط %.2f على %d) — مثبت" % (dec["scale"], med, len(vals)))
    as_ratio = bool(dec and dec.get("scale") == "ratio×100")
    if not dec and de_raw:
        print("⚠️ D/E: لا قرار مثبت (جزئية قبل كاملة) — لا يُكتب debtToEquity")

    # ── كتابة financials الموحدة + الحراس (§8) ──
    for st in stocks:
        sym = st["symbol"]
        sc = scratch.get(sym) or {}
        p = sc.get("fs")
        rat = sc.get("ratios") or {}
        if not p and not rat:
            continue   # فشل كلا المصدرين — الكتلة القديمة تبقى بختمها (لا ختم زور)
        bank = is_bank(st)
        fin = {}
        if p:
            a, l = p.get("totalAssets"), p.get("totalLiabilities")
            e = (p.get("equityExplicit") if eq_src == "explicit"
                 else ((a - l) if (a is not None and l is not None) else p.get("equityExplicit")))
            if a is not None and a <= 0:
                a = reject(st, "totalAssets", a, "أصول ≤ 0", today)
            if e is not None and a and abs(e) > a * 2:
                e = reject(st, "equity", e, "|ملكية| > أصول×2 — مصيدة وحدات", today)
            fin.update({"totalAssets": a, "totalLiabilities": l, "equity": e,
                        "ocf": p.get("ocf"), "fcf": p.get("fcf"), "netIncome": p.get("netIncome"),
                        "fiscalYear": p.get("fiscalYear"), "reportDate": p.get("reportDate"),
                        "cfReportDate": p.get("cfReportDate")})
            rg = p.get("revenueGrowthRaw")
            if rg is not None:
                if bank and not (-50 < rg < 50):
                    rg = reject(st, "revenueGrowth", rg, "حارس بنوك (−50،+50)", today)
                elif not bank and not (-100 < rg <= 500):
                    rg = reject(st, "revenueGrowth", rg, "خارج (−100،+500]", today)
            fin["revenueGrowth"] = rg
            if not bank:
                if fin.get("ocf") is not None and l and l > 0:
                    fin["ocfLiabilities"] = round(fin["ocf"] / l, 4)   # ‏Beaver — بسط ومقام من السنة نفسها
                elif l is not None and l <= 0:
                    reject(st, "ocfLiabilities", l, "مطلوبات ≤ 0", today)
            else:
                if e is not None and a and a > 0:
                    fin["equityAssets"] = round(e / a * 100, 2)        # رفع البنوك الرأسمالي
        for src_k, dst_k, dp in (("net_margin", "profitMargins", 1), ("roe", "returnOnEquity", 1),
                                 ("roa", "returnOnAssets", 2), ("operating_margin", "operatingMargin", 1)):
            v = rat.get(src_k)
            if v is not None:
                if dst_k in ("profitMargins", "returnOnEquity") and abs(v) > 1000:
                    v = reject(st, dst_k, v, "خارج ±1000% — مصيدة وحدات", today)
                fin[dst_k] = round(v, dp) if v is not None else None
        if fin.get("returnOnEquity") is not None and fin.get("equity") is not None and fin["equity"] <= 0:
            fin["returnOnEquity"] = reject(st, "returnOnEquity", fin["returnOnEquity"],
                                           "ملكية سالبة — غير معرف", today)
        if dec and de_raw.get(sym) is not None:
            de_v = round(de_raw[sym] * 100, 2) if as_ratio else round(de_raw[sym], 2)
            if fin.get("equity") is not None and fin["equity"] <= 0:
                de_v = reject(st, "debtToEquity", de_v, "ملكية سالبة — غير معرف", today)
            fin["debtToEquity"] = de_v
        merged = dict(st.get("financials") or {})
        merged.update(fin)
        st["financials"] = merged
        st["financialsSource"] = "sahmk (ratios+financials)"
        st["financialsUpdated"] = today
        comp = sc.get("company") or {}
        div = sc.get("div")
        vi = dict(st.get("valuationInputs") or {})
        if comp:
            vi.update({"eps": comp.get("eps"), "bookValue": comp.get("bookValue"),
                       "peSource": comp.get("peSource"), "beta": comp.get("beta"),
                       "companyAsOf": today})
        if div:
            vi["divTtm12m"], vi["divBasis"] = div
            vi["divsAsOf"] = today
        vi["updatedAt"] = today
        vi["source"] = "sahmk-direct"
        st["valuationInputs"] = vi

    # ── حارس الانزياح الجماعي (§8): فئة ≥5 يتغير حقلها باتجاه واحد >80% ──
    drift = []
    groups = {"البنوك": [s for s in stocks if is_bank(s)]}
    for sec in {s.get("sector") for s in stocks if s.get("sector")}:
        groups["قطاع " + str(sec)] = [s for s in stocks if s.get("sector") == sec]
    for gname, members in groups.items():
        if len(members) < 5:
            continue
        for fld in ("revenueGrowth", "profitMargins", "returnOnEquity", "debtToEquity"):
            deltas = []
            for s in members:
                ov = (s.get("_prevFinancials") or {}).get(fld)
                nv = (s.get("financials") or {}).get(fld)
                if isinstance(ov, (int, float)) and isinstance(nv, (int, float)) and ov != nv:
                    deltas.append(nv - ov)
            if deltas and len(deltas) >= 0.8 * len(members):
                same = max(sum(1 for d in deltas if d > 0), sum(1 for d in deltas if d < 0))
                if same > 0.8 * len(members):
                    drift.append("%s/%s: %d من %d بإشارة واحدة" % (gname, fld, same, len(members)))
    if sector_changes:
        print("⚠️ تغير sector/industry (إنذار): %s" % sector_changes[:10])
        data["sectorChanges"] = [{"symbol": s, "field": f, "old": o, "new": nv, "date": today}
                                 for s, f, o, nv in sector_changes]
    return drift


def fetch_upcoming_dividends(api, data, stocks, counters, today):
    """مفكرة التوزيعات (عقد المحلل 14-08) — كتلة عرض علوية `upcomingDividends`:
    الأحداث القادمة في نافذة 45 يوماً (أحقية أو إيداع). القواعد الملزمة:
      - أحقية null + إيداع قادم → يُبقى (الواجهة تعرض «الأحقية: لم تُعتمد بعد»)
      - أحقية ماضية + إيداع قادم → يدخل بإيداعه (حالة علم)
      - أحقية null وإيداع null، أو ماضٍ كلياً، أو بعد النافذة → يسقط
    **عزل القياس الصارم:** كتلة عرض فقط — divsSince في سكربت الدقة يبقى من أحقية
    فعلية ≤ تاريخ التشغيلة حصراً (فلتره القائم يستوفيه)، وL1 يدقق سجل مصدره.
    **قرار هندسي موثق:** ‏?upcoming=true يومياً للكون كله (+248 طلباً ≈ 503/5000 —
    قياس الميزانية في sahmk-divcal-probe.py) — النضارة اليومية أرجح من تحسين
    «كامل أسبوعياً + قريب يومياً» الذي يفوّت إعلانات بين التشغيلتين ويعقّد الحالة؛
    وفشل الكتلة لا يحجب بيانات التقييم (fail-open معلن كصيانة الكون): فشل >10%
    أو كلي → تبقى الكتلة السابقة بختمها القديم + إنذار عالٍ، ولا تدخل بوابة §7."""
    horizon = (datetime.strptime(today, "%Y-%m-%d")
               + timedelta(days=DIVCAL_WINDOW_DAYS)).strftime("%Y-%m-%d")
    out = []

    def process(st):
        sym = st["symbol"]
        # مواءمة 16-08: النداء القياسي الموثق (المعامل الوحيد limit) وقراءة مصفوفة
        # `upcoming` من الدرجة الأولى — بدل ?upcoming=true الذي نجح حياً لكنه غير معقود.
        # حقول upcoming الموثقة أربعة فقط {value, period, eligibility_date,
        # distribution_date} (التقاطة الناقد: بلا announcement_date ولا fiscal_year) —
        # يُضمّان من سجل history المطابق (القيمة+الفترة) وإلا null بصدق.
        r, err = api.get("/dividends/%s/?limit=50" % sym)
        if r is None:
            return False, err
        hist = r.get("history") if isinstance(r, dict) else None
        upc = r.get("upcoming") if isinstance(r, dict) else None
        if not isinstance(upc, list):
            # تحوط عقدي: غياب المصفوفة (خادم أقدم؟) → اشتقاق من سجلات history المستقبلية
            counters["divcal_noupc"] = counters.get("divcal_noupc", 0) + 1
            upc = [h for h in (hist or [])
                   if isinstance(h, dict) and ((h.get("eligibility_date") or "") >= today
                                               or (h.get("distribution_date") or "") >= today)]
        def _join(rec):
            """ضم fy/annDate من history بالمطابقة (القيمة + الفترة)"""
            for h in (hist or []):
                if (isinstance(h, dict) and h.get("value") == rec.get("value")
                        and h.get("period") == rec.get("period")):
                    return (h.get("fiscal_year") or h.get("fy"),
                            h.get("announcement_date") or None)
            return None, None
        seen_sigs = set()   # إزالة تكرار **داخل الرمز الواحد فقط** — التوقيع عبر الرموز شأن حارس 2060/2080
        def _emit(rec, fy, ann):
            elig = (rec.get("eligibility_date") or None)
            dist = (rec.get("distribution_date") or None)
            val = rec.get("value", rec.get("amount"))
            if val is None:
                return
            in_elig = bool(elig) and today <= str(elig)[:10] <= horizon
            in_dist = bool(dist) and today <= str(dist)[:10] <= horizon
            if not (in_elig or in_dist):
                return   # يشمل: null+null، الماضي كلياً، وما بعد النافذة
            sig = (val, str(elig)[:10] if elig else None, str(dist)[:10] if dist else None)
            if sig in seen_sigs:
                return   # سجل انتقالي ظهر في upcoming وhistory معاً — مرة واحدة
            seen_sigs.add(sig)
            out.append({"sym": sym, "name": st.get("name", ""), "value": val,
                        "period": rec.get("period"), "fy": fy, "annDate": ann,
                        "eligDate": str(elig)[:10] if elig else None,
                        "distDate": str(dist)[:10] if dist else None})
        for rec in upc:
            if isinstance(rec, dict):
                fy, ann = _join(rec)
                _emit(rec, fy, ann)
        # (إصلاح 21-08 — العلة المثبتة بجرير/أرامكو/الحمادي): المصدر يُسقط السجل من
        # upcoming بعد مرور أحقيته ولو كان إيداعه قادماً، فتفقد المفكرة «يوم وصول
        # النقد» في أقرب لحظاته. الإكمال من history (نفس النداء — صفر طلبات إضافية):
        # كل سجل إيداعه مستقبلي يدخل بحقوله الكاملة (أحقية ماضية، إعلان، fy أصليان).
        for h in (hist or []):
            if isinstance(h, dict) and str(h.get("distribution_date") or "")[:10] >= today:
                _emit(h, h.get("fiscal_year") or h.get("fy"), h.get("announcement_date") or None)
        return True, None

    run_with_429_sweep(stocks, process, counters, "divcal_ok", "divcal_fail", "مفكرة التوزيعات")
    ok, fl = counters["divcal_ok"], counters["divcal_fail"]
    if ok == 0 or (ok + fl and fl / (ok + fl) > 0.10):
        print("  ⚠️⚠️ مفكرة التوزيعات: فشل %d/%d — الكتلة السابقة تبقى بختمها القديم"
              " (عرض لا يحجب التقييم)" % (fl, ok + fl))
        return
    # ── حارسا حادثة 2060/2080 (17-08 — إسناد المصدر الآلي حدثاً لرمز دخيل) ──
    # 1) التكرار عبر الرموز: توقيع {value, eligDate, distDate} لدى أكثر من رمز =
    #    شبهة خلط اسمي في تحليل المصدر — الحامل الشاذ (عائده الفردي >8% أو ≥3×وسيط
    #    حملة التوقيع، أو سعره غائب فلا يُرجّح) يوسم suspectDup؛ كل الأسعار غائبة → الجميع.
    # 2) العائد الاستثنائي المستقل: عائد فردي >8% → highYield ولو بلا توأم
    #    (التوزيع الخاص الحقيقي يستحق تنبيهاً أيضاً).
    price_of = {s["symbol"]: s.get("currentPrice") for s in stocks}
    def _yield(u):
        p = price_of.get(u["sym"])
        return (u["value"] / p * 100) if (p and u.get("value")) else None
    for u in out:
        y = _yield(u)
        if y is not None and y > 8.0:
            u["highYield"] = True
    sig_map = {}
    for u in out:
        sig_map.setdefault((u["value"], u["eligDate"], u["distDate"]), []).append(u)
    suspects = []
    for sig, holders in sig_map.items():
        if len(holders) < 2:
            continue
        ys = [(u, _yield(u)) for u in holders]
        known = [y for _, y in ys if y is not None]
        if not known:
            for u, _ in ys:
                u["suspectDup"] = True
                suspects.append(u["sym"])
            continue
        # ملزمة الناقد 17-08ب (ببرهانه الجبري، واعتماد المحلل «3× للزوج»):
        # وسيط الزوج يجعل ≥3×الوسيط مستحيلاً جبرياً (y_max ≤ 2×وسيط الزوج دوماً) —
        # فللحملة الثنائية حصراً: نسبة الزوج y_max ≥ 3×y_min توسم الأعلى.
        # الحملات ≥3 على منطق الوسيط؛ فرعا 8% المطلق وغياب السعر كما هما في الكل.
        if len(holders) == 2 and len(known) == 2:
            y_min, y_max = min(known), max(known)
            pair_bad = y_min > 0 and y_max >= 3 * y_min
            for u, y in ys:
                if y > 8.0 or (pair_bad and y == y_max):
                    u["suspectDup"] = True
                    suspects.append(u["sym"])
            continue
        med = statistics.median(known)
        for u, y in ys:
            if y is None or y > 8.0 or (med > 0 and y >= 3 * med):
                u["suspectDup"] = True
                suspects.append(u["sym"])
    counters["divcal_suspect"] = len(suspects)
    if suspects:
        print("  🚨 مفكرة التوزيعات: %d صفاً مشبوه الإسناد (توقيع مكرر عبر رموز — سابقة"
              " 2060/2080): %s — موسومة suspectDup للعرض الحذر وبلاغ المصدر" % (len(suspects), suspects[:8]))
    out.sort(key=lambda x: (x["eligDate"] or x["distDate"] or "9999", x["sym"]))
    data["upcomingDividends"] = out
    data["upcomingDividendsAt"] = today
    print("  📅 مفكرة التوزيعات: %d حدثاً قادماً في نافذة %d يوماً (نجح %d | فشل %d)"
          % (len(out), DIVCAL_WINDOW_DAYS, ok, fl))


def divcal_only_run(api, data_path, data, stocks):
    """وضع divcal الخفيف (طلب المالك 21-08 — مفكرة تتحدث كل الأسبوع شاملاً الويكند):
    يجلب التوزيعات فقط (~عدد الأسهم طلباً بإيقاع 1.5/ث) ويحدّث **حصراً** كتلتي
    upcomingDividends/upcomingDividendsAt. **حارس صريح**: أي فرق خارج الكتلتين
    (أسعار/محرك/مغذٍ/عينة/أي شيء) = إجهاض بصوت عالٍ بلا كتابة. ‏fail-open القائم
    يسري (فشل الجلب = الكتلة السابقة بختمها + إنذار — وعندها لا شيء يتغير أصلاً)."""
    import copy as _copy
    KEYS = ("upcomingDividends", "upcomingDividendsAt")
    orig = _copy.deepcopy(data)
    counters = {"divcal_ok": 0, "divcal_fail": 0}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print("📅 وضع divcal الخفيف: %d طلباً بإيقاع %.1f/ث ≈ %.1f دقيقة — الكتلتان فقط"
          % (len(stocks), RATE_PER_SEC, len(stocks) / RATE_PER_SEC / 60))
    fetch_upcoming_dividends(api, data, stocks, counters, today)
    a = json.dumps({k: v for k, v in orig.items() if k not in KEYS}, sort_keys=True, ensure_ascii=False)
    b = json.dumps({k: v for k, v in data.items() if k not in KEYS}, sort_keys=True, ensure_ascii=False)
    if a != b:
        print("⛔⛔ حارس divcal: رُصد تغير خارج كتلتي المفكرة — إجهاض بلا أي كتابة")
        sys.exit(1)
    out_dir = os.path.dirname(os.path.abspath(data_path)) or "."
    fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, data_path)
    try:
        os.chmod(data_path, 0o664)
    except OSError:
        pass
    print("✅ divcal: كُتبت كتلتا المفكرة حصراً (%d صفاً، ختم %s) — %s"
          % (len(data.get("upcomingDividends") or []), data.get("upcomingDividendsAt"), data_path))
    sys.exit(0)


def fetch_tasi(api, counters, hist_file, data):
    hist = []
    if os.path.exists(hist_file):
        try:
            hist = json.load(open(hist_file))["data"]
        except Exception:
            hist = []
    last = hist[-1]["date"] if hist else (datetime.now(timezone.utc) - timedelta(days=FOUNDING_CAL_DAYS)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def once():
        resp, err = api.get("/historical/TASI/?interval=1d&from=%s&to=%s" % (last, today))
        rows, _ = parse_candles(resp)   # قاعدة الجزئية تسري على المؤشر أيضاً
        if rows:
            return rows, None, False
        if err:
            return [], err, False
        return [], "استجابة 200 بلا شموع — الشكل: %s" % (sorted(resp.keys())[:6] if isinstance(resp, dict) else type(resp).__name__), True

    def fresh():
        if not hist:
            return False
        try:
            return (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(hist[-1]["date"], "%Y-%m-%d")).days <= 4
        except ValueError:
            return False

    rows, reason, e200 = once()
    if not rows and e200 and fresh():
        print("  ✅ تاسي: لا شموع جديدة — المحلي محدّث (آخره %s)" % hist[-1]["date"])
    elif not rows:
        print("  ⚠️ تاسي بلا بيانات (%s) — متباعدة 10ث..." % reason)
        time.sleep(10)
        rows, reason, e200 = once()
        if not rows and not (e200 and fresh()):
            if not hist:
                counters["tasi_fail"] += 1
                print("  ✗ تاسي: %s — لا محلي: فشل حاكم" % reason)
                return None
            counters["tasi_api_stale"] += 1
            print("  ⚠️ تاسي فشلت (%s) — نكمل بالمحلي (%d)" % (reason, len(hist)))
    known = {h2["date"] for h2 in hist}
    for r in rows:
        if r[0] and r[0] not in known:
            hist.append({"date": r[0], "close": round(r[1], 2)})
        elif r[0] in known:
            for h2 in hist:
                if h2["date"] == r[0]:
                    h2["close"] = round(r[1], 2)
    hist.sort(key=lambda h2: h2["date"])
    tmp = hist_file + ".tmp"
    json.dump({"data": hist}, open(tmp, "w"))
    os.replace(tmp, hist_file)
    counters["tasi_ok"] += 1
    closes = [h2["close"] for h2 in hist]
    t = {"3m": period_return(closes, 63), "6m": period_return(closes, 126),
         "12_1": return_12_1(closes)}
    data["tasiReturns"] = t
    data["tasi"] = {"current": closes[-1], "ret3m": t["3m"], "ret6m": t["6m"], "ret12_1": t["12_1"]}
    # نظام السوق (§2 — عرض ووسم فقط، لا نقاط ولا فلاتر)
    s, serr = api.get("/market/summary/")
    if s is None or s.get("index_value") is None:
        counters["regime_fail"] += 1
        print("  ✗ market/summary: %s" % (serr or "حقول ناقصة"))
    else:
        val, adv, dcl = s["index_value"], s.get("advancing"), s.get("declining")
        day = str(s.get("timestamp") or today)[:10]
        if hist and hist[-1]["date"] == day:
            hist[-1]["close"] = val
            closes[-1] = val
        else:
            hist.append({"date": day, "close": val})
            closes.append(val)
        tmp = hist_file + ".tmp"
        json.dump({"data": hist}, open(tmp, "w"))
        os.replace(tmp, hist_file)
        sma200 = sum(closes[-200:]) / min(200, len(closes))
        sma_prev = sum(closes[-220:-20]) / min(200, len(closes[:-20])) if len(closes) > 220 else sma200
        slope = (sma200 - sma_prev) / sma_prev * 100
        pct_vs = (val - sma200) / sma200 * 100
        breadth = adv / dcl if dcl else 1.0
        if val > sma200 and slope > 0:
            regime, icon, advice = "صاعد", "🟢", "بيئة داعمة — مراكز كاملة"
        elif val > sma200 or (pct_vs > -2 and breadth > 0.9):
            regime, icon, advice = "حذر", "🟡", "بيئة مختلطة — نصف مركز وتدرّج"
        else:
            regime, icon, advice = "هابط", "🔴", "بيئة ضاغطة — الأفضلية للانتظار"
        prev_close = closes[-2] if len(closes) >= 2 else val
        data["marketRegime"] = {
            "date": day, "indexValue": val, "prevClose": round(prev_close, 2),
            "change": round(val - prev_close, 2),
            "changePct": round((val - prev_close) / prev_close * 100, 2),
            "sma200d": round(sma200, 2), "pctVsSma": round(pct_vs, 2),
            "smaSlope": round(slope, 2), "advancing": adv, "declining": dcl,
            "breadth": round(breadth, 2), "mood": s.get("market_mood", ""),
            "regime": regime, "icon": icon, "advice": advice}
        counters["regime_ok"] += 1
        print("  %s نظام السوق: %s | تاسي %.0f (%+.1f%%)" % (icon, regime, val, pct_vs))
    return t


def maintain_universe(api, data, counters, today, dry_run=False):
    """صيانة الكون من /companies/ (§7).
    (ش-3) عتبة أمان: شطب >10% من الكون في تشغيلة واحدة = تخطٍّ كامل بإنذار صارخ
    (شبهة قائمة مبتورة). لا تكتب watchlist-config هنا — تعيد الإغلاقات المعلقة
    والكتابة تُنفذ في main **بعد** كل بوابات الفشل.

    حادثة 01-09 (تعطل الخط يومين): النداء كان بلا مرشِّح، و/companies/ توثق صراحةً
    أنها تضم نمو والصكوك وصناديق المؤشرات والصناديق المغلقة — فقفز الكون 248→519
    وسقط الجلب التالي على 271 كياناً ليست أسهماً رئيسية حتى رفضت بوابة الفشل الحاكم
    الكتابة، فمات الخط يومياً. الإصلاح المزدوج:
      (أ) نطاق صريح: market=TASI + security_type=Equity + غير ETF + status=active
      (ب) بوابة نمو متماثلة لبوابة الشطب: إضافة >10% = تخطٍّ كامل بإنذار."""
    # (إصلاح 05-08ب) /companies/ مصفّحة (limit افتراضي ~100 بتر الكون إلى 94/248) —
    # نصفّح بـlimit/offset حتى النهاية (has_more/total إن وُجدا، وإلا صفحة أقصر من limit)
    rows = []
    err = None
    LIMIT = 100
    total_declared = None
    for page in range(30):   # سقف أمان
        # market=TASI: السوق الرئيسي حصراً — نمو خارج نطاق المنصة بالتصميم (حادثة 01-09)
        resp, err = api.get("/companies/?market=TASI&limit=%d&offset=%d" % (LIMIT, page * LIMIT))
        if resp is None:
            break
        batch = rows_of(resp, "companies", "data", "results")
        rows.extend(batch)
        if isinstance(resp, dict):
            total_declared = resp.get("total") if resp.get("total") is not None else resp.get("count", total_declared)
            if resp.get("has_more") is False:
                break
        if len(batch) < LIMIT:
            break
    if not rows:
        print("  ✗ /companies/: %s — الصيانة تتخطى (بوابة تشغيلة أولى)" % (err or "شكل غير معروف"))
        counters["universe_fail"] += 1
        return None
    have_n = sum(1 for s in data["stocks"] if not s.get("delisted"))
    # فحص اكتمال الترقيم يسبق الترشيح (يقارن الخام بالمعلن)
    if total_declared is not None and len(rows) < total_declared:
        print("  ✗ /companies/: جمعنا %d من %d معلنة — قائمة مبتورة، الصيانة تتخطى" % (len(rows), total_declared))
        counters["universe_fail"] += 1
        return None
    # ترشيح الأدوات (حادثة 01-09): أسهم السوق الرئيسي النشطة حصراً — لا صكوك ولا
    # صناديق مؤشرات ولا صناديق مغلقة ولا نمو. الحقول موثقة رسمياً في /companies/.
    raw_n = len(rows)
    def _is_main_equity(r):
        st = str(r.get("security_type") or "Equity")
        if st != "Equity":
            return False
        if r.get("is_etf") is True:
            return False
        if str(r.get("status") or "active") != "active":
            return False
        mk = r.get("market") or r.get("market_segment")
        return not mk or str(mk).upper().startswith("TASI")
    rows = [r for r in rows if _is_main_equity(r)]
    if raw_n != len(rows):
        print("  🧹 ترشيح الأدوات: %d ← %d (استُبعد %d: نمو/صكوك/صناديق/غير نشط)"
              % (raw_n, len(rows), raw_n - len(rows)))
    if not rows:
        print("  ✗ /companies/: صفر أسهم رئيسية بعد الترشيح — الصيانة تتخطى")
        counters["universe_fail"] += 1
        return None
    if len(rows) < have_n:
        print("  ✗ /companies/: العد النهائي %d < الكون %d — شبهة بتر، الصيانة تتخطى قبل أي مقارنة شطب"
              % (len(rows), have_n))
        counters["universe_fail"] += 1
        return None
    listed = {str(r.get("symbol")): r for r in rows if r.get("symbol")}
    have = {s["symbol"] for s in data["stocks"]}
    added = [s for s in listed if s not in have]
    gone = [s for s in have if s not in listed]
    if have and len(gone) > 0.10 * len(have):
        print("⛔⛔ عتبة الشطب الجماعي (ش-3): /companies/ تسقط %d من %d (%.0f%% > 10%%) —"
              % (len(gone), len(have), len(gone) / len(have) * 100))
        print("   شبهة قائمة مبتورة — الصيانة تتخطى كلياً بلا أي وسم أو إغلاق. تحقق يدوياً.")
        counters["universe_fail"] += 1
        return None
    # بوابة النمو المتماثلة (حادثة 01-09): كانت بوابة الشطب بلا نظير للإضافة،
    # فمرّ +271 (+109%) بصمت وقتل الخط يومين. إضافة >10% = تخطٍّ كامل بإنذار.
    if have and len(added) > 0.10 * len(have):
        print("⛔⛔ عتبة الإضافة الجماعية: /companies/ تضيف %d على %d (%.0f%% > 10%%) —"
              % (len(added), len(have), len(added) / len(have) * 100))
        print("   شبهة اتساع نطاق غير مقصود — الصيانة تتخطى كلياً بلا أي إضافة. تحقق يدوياً.")
        print("   عينة المضاف: %s" % (added[:10],))
        counters["universe_fail"] += 1
        return None
    if dry_run:
        print("  🔎 وضع جاف — لا كتابة | مدرج %d | سيضاف %d %s | سيُشطب %d %s"
              % (len(listed), len(added), added[:10], len(gone), gone[:10]))
        counters["universe_ok"] += 1
        return None
    for sym in added:
        r = listed[sym]
        data["stocks"].append({"symbol": sym,
                               "name": r.get("name_ar") or r.get("name") or r.get("name_en") or sym,
                               "sector": r.get("sector"), "industry": r.get("industry"),
                               "listedAt": today})
    for s in data["stocks"]:
        if s["symbol"] in gone and not s.get("delisted"):
            s["delisted"] = True
            s["delistedAt"] = today
    data["universeUpdated"] = today
    counters["universe_ok"] += 1
    print("  🌐 الكون: مدرج %d | أضيف %d %s | delisted ‏%d %s | إغلاق التوصيات مؤجل لما بعد البوابات"
          % (len(listed), len(added), added[:5], len(gone), gone[:5]))
    return gone


def close_delisted_recs(config_path, gone, price_map, today):
    """كتابة إغلاقات delisted في watchlist-config — تُستدعى بعد اجتياز كل البوابات فقط (ش-3)"""
    if not gone or not os.path.exists(config_path):
        return []
    cfg = json.load(open(config_path))
    closed = []
    for e in cfg.get("stocks", []):
        if e.get("symbol") in gone and e.get("status", "open") == "open":
            e["status"] = "closed"
            e["closeDate"] = today
            e["closePrice"] = price_map.get(e["symbol"])
            e["closeReason"] = "delisted"   # قاعدة الإغلاق ج (§6-10)
            closed.append(e["symbol"])
    if closed:
        tmp = config_path + ".tmp"
        json.dump(cfg, open(tmp, "w"), ensure_ascii=False, indent=1)
        os.replace(tmp, config_path)
    return closed


# ═══════════════════ الاستكشاف ═══════════════════

def key_tree(obj, depth=3, indent=""):
    lines = []
    if depth < 0:
        return lines
    if isinstance(obj, dict):
        for k, v in obj.items():
            lines.append("%s%s (%s)" % (indent, k, type(v).__name__))
            if isinstance(v, (dict, list)):
                lines += key_tree(v, depth - 1, indent + "  ")
    elif isinstance(obj, list) and obj:
        lines.append("%s[%d — الأول:]" % (indent, len(obj)))
        lines += key_tree(obj[0], depth - 1, indent + "  ")
    return lines


def probe_financials(api):
    for sym in ("2222", "1180"):
        print("═" * 40, "\n/financials/%s/" % sym)
        resp, err = api.get("/financials/%s/" % sym)
        if resp is None:
            print("  ✗", err)
            continue
        for line in key_tree(resp, 3, "  "):
            print(line)
        p = parse_financials(resp) or {}
        print("  💵", {k: p.get(k) for k in ("totalRevenue", "netIncome", "ocf", "totalAssets",
                                             "totalLiabilities", "equityExplicit", "revenueGrowthRaw", "reportDate")})
    print("طلبات:", api.requests_made)


def probe_ratios(api):
    combos = ["", "?metrics=core", "?history=latest&period=annual&metrics=core"]
    for sym in ("2222", "1180"):
        print("═" * 40, "\n/analytics/ratios/%s/" % sym)
        for c in combos:
            resp, err = api.get("/analytics/ratios/%s/%s" % (sym, c))
            if resp is None:
                print("  %-40s ✗ %s" % (c or "(بلا معاملات)", err))
                continue
            print("  %-40s ✅" % (c or "(بلا معاملات)"))
            for line in key_tree(resp, 3, "    "):
                print(line)
            rat, uerr = unwrap_ratios(resp)   # نفس نزول do_ratios — لا افتراض شكل
            if rat is None:
                print("  ⚠️ النزول الموحد فشل: %s" % uerr)
            else:
                print("  💵 القيم: roe=%s roa=%s net_margin=%s d/e=%s"
                      % (rat.get("roe"), rat.get("roa"), rat.get("net_margin"), rat.get("debt_to_equity")))
            break
    print("طلبات:", api.requests_made)


# ═══════════════════ main ═══════════════════

def main():
    ap = argparse.ArgumentParser(description="جالب المنصة القائمة بذاتها (sahmk-direct-v3)")
    ap.add_argument("--data", default="", help="مسار stocks-data.json (إلزامي للجلب)")
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--maintain-universe", action="store_true")
    ap.add_argument("--universe-dry-run", action="store_true",
                    help="يطبع ما ستفعله صيانة الكون بلا أي كتابة (تحقق آمن — حادثة 01-09)")
    ap.add_argument("--symbols", default="")
    ap.add_argument("--probe-financials", action="store_true")
    ap.add_argument("--probe-ratios", action="store_true")
    ap.add_argument("--divcal-only", action="store_true",
                    help="وضع الويكند الخفيف: تحديث كتلتي المفكرة حصراً")
    ap.add_argument("--key-file", default="")
    ap.add_argument("--tasi-history", default="")
    ap.add_argument("--watchlist-config", default="", help="لإغلاق delisted (افتراضي بجوار --data)")
    args = ap.parse_args()

    key = os.environ.get("SAHMK_KEY", "")
    if not key and args.key_file:
        key = open(args.key_file).read().strip()
    if not key:
        sys.exit("⛔ لا مفتاح: SAHMK_KEY أو --key-file (يُمنع في الكود/المستودع)")
    api = Api(key)
    if args.probe_financials:
        return probe_financials(api)
    if args.probe_ratios:
        return probe_ratios(api)
    if not args.data:
        sys.exit("⛔ --data إلزامي")

    with open(args.data) as f:
        data = json.load(f)
    if args.universe_dry_run:
        # مسار مستقل مبكر: نداء واحد لـ/companies/ وطباعة الفرق — صفر كتابة وصفر جلب
        _c = {"universe_ok": 0, "universe_fail": 0}
        _today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print("🔎 صيانة الكون — وضع جاف (لا كتابة) | الكون الحالي: %d"
              % sum(1 for s in data.get("stocks", []) if not s.get("delisted")))
        maintain_universe(api, data, _c, _today, dry_run=True)
        sys.exit(0 if _c["universe_fail"] == 0 else 1)
    stocks = [s for s in data.get("stocks", []) if s.get("symbol") and not s.get("delisted")]
    if args.symbols:
        want = {x.strip() for x in args.symbols.split(",") if x.strip()}
        stocks = [s for s in stocks if s["symbol"] in want]
    if not stocks:
        sys.exit("⛔ لا أسهم مطابقة")
    if args.divcal_only:
        divcal_only_run(api, args.data, data, stocks)   # يخرج داخلياً — لا يصل لبقية الخط
    for s in stocks:   # لقطة الماليات السابقة لحارس الانزياح — لا تُكتب للملف
        s["_prevFinancials"] = dict(s.get("financials") or {})
        s["guardRejected"] = []   # §8: تُعاد بناؤها كل تشغيلة بمرفوضات التشغيلة نفسها

    hist_file = args.tasi_history or os.path.join(os.path.dirname(os.path.abspath(args.data)), "tasi-history.json")
    cfg_path = args.watchlist_config or os.path.join(os.path.dirname(os.path.abspath(args.data)), "watchlist-config.json")
    cdir = candle_dir(args.data)
    n = len(stocks)
    batches = (n + 49) // 50
    budget = (batches + n + 2 + (n * 4 if args.weekly else 0) + (1 if args.maintain_universe else 0)
              + (n if not args.symbols else 0))   # +n: مفكرة التوزيعات اليومية (عقد المحلل 14-08)
    print("═" * 60)
    print("سيف تداول — sahmk-direct-v3 | أسهم: %d | %s" % (n, "أسبوعي" if args.weekly else "يومي"))
    print("ميزانية ~%d (quotes %d + 1d %d + تاسي/ملخص 2%s) — happy-path، إيقاع %.1fط/ث، حصة 5000/يوم"
          % (budget, batches, n, " + أساسيات %d×4" % n if args.weekly else "", RATE_PER_SEC))
    print("═" * 60)

    counters = {k: 0 for k in (
        "quotes_ok", "quotes_fail", "quotes_batch_fail", "daily_ok", "daily_fail",
        "ratios_ok", "ratios_fail", "financials_ok", "financials_fail",
        "company_ok", "company_fail", "dividends_ok", "dividends_fail",
        "adj_dropped_rows", "partial_excluded", "tasi_ok", "tasi_fail", "tasi_api_stale",
        "regime_ok", "regime_fail", "universe_ok", "universe_fail",
        "divcal_ok", "divcal_fail", "hist_gap_truncated")}
    now_riyadh = datetime.now(RIYADH).strftime("%Y-%m-%d %H:%M")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("📈 تاسي ونظام السوق...")
    tasi = fetch_tasi(api, counters, hist_file, data) or {}
    if tasi.get("3m") is None or tasi.get("6m") is None:
        sys.exit("⛔ فشل تاسي حاكم: عوائد المرجع غير قابلة للحساب — لا كتابة (§7)")

    print("💰 الأسعار...")
    if fetch_quotes(api, stocks, counters, now_riyadh, today) == 0:
        sys.exit("⛔ فشل الأسعار كلياً — لا كتابة")

    print("📊 شموع 1d (تزايدي) + اشتقاق أسبوعي + Z + سيولة...")
    fetch_daily_and_derive(api, stocks, counters, cdir, tasi, stamp, today)

    if not args.symbols:
        print("📅 مفكرة التوزيعات (upcoming، نافذة %d يوماً)..." % DIVCAL_WINDOW_DAYS)
        fetch_upcoming_dividends(api, data, stocks, counters, today)
    else:
        print("📅 مفكرة التوزيعات: تخطٍ — تشغيلة --symbols جزئية (كتلة سوقية لا تُبنى من جزء)")

    drift = []
    if args.weekly:
        print("🏦 الأساسيات...")
        drift = fetch_fundamentals(api, data, stocks, counters, today,
                                   full_universe=not args.symbols)
        print("  🏦 بنوك مكتشفة بالتعريف الموحد: %d (المتوقع ~10 — بوابة تشغيلة أولى)"
              % sum(1 for s in stocks if is_bank(s)))
    gone_pending = None
    if args.maintain_universe:
        print("🌐 صيانة الكون...")
        gone_pending = maintain_universe(api, data, counters, today)

    # ── التغطية وبوابة الانهيار (§7) ──
    sma_cap = sum(1 for s in stocks if (s.get("weeklyTechnical") or {}).get("sma200w"))
    z_cap = sum(1 for s in stocks if (s.get("dailyExtra") or {}).get("zExt") is not None)
    prev_cov = data.get("coverage") or {}
    cov_fail = []
    if not args.symbols:
        for cname, now_v, prev_v in (("SMA200W", sma_cap, prev_cov.get("smaCapable")),
                                     ("Z", z_cap, prev_cov.get("zCapable"))):
            if prev_v and now_v < prev_v * 0.9:
                cov_fail.append("%s: ‏%d→%d (انهيار >10%%)" % (cname, prev_v, now_v))

    # ── الخلاصة وبوابات الفشل — قبل الكتابة ──
    print("═" * 60)
    print("طلبات: %d/~%d | ‏429: %d" % (api.requests_made, budget, api.hits_429))
    fail_types = []
    for label, okk, failk in (("أسعار", "quotes_ok", "quotes_fail"), ("شموع يومية", "daily_ok", "daily_fail"),
                              ("نسب مالية", "ratios_ok", "ratios_fail"), ("قوائم مالية", "financials_ok", "financials_fail"),
                              ("company", "company_ok", "company_fail"), ("توزيعات", "dividends_ok", "dividends_fail")):
        ok, fl = counters[okk], counters[failk]
        if ok + fl == 0:
            continue
        pct = fl / (ok + fl) * 100
        print("%s %s: نجح %d | فشل %d (%.0f%%)" % ("⚠️" if pct > 10 else "✅", label, ok, fl, pct))
        if pct > 10:
            fail_types.append(label)
    rejected = sum(len(s.get("guardRejected") or []) for s in stocks)
    print("تغطية: SMA200W %d | ‏Z(يومي) %d | حراس رفضوا %d | شموع بلا معدل %d | جزئية مستبعدة %d"
          % (sma_cap, z_cap, rejected, counters["adj_dropped_rows"], counters["partial_excluded"]))
    # (البند 4) توزيع العمق — أرضية قرارات المحلل بالأرقام، يطبع كل تشغيلة
    wk_depths = sorted((s.get("weeklyTechnical") or {}).get("weeks") or 0
                       for s in stocks if s.get("weeklyTechnical"))
    ses_depths = sorted((s.get("dailyExtra") or {}).get("sessions") or 0
                        for s in stocks if s.get("dailyExtra"))
    if wk_depths:
        print("عمق الأسابيع المشتقة: وسيط %d | أدنى %d | أعلى %d | ‏≥200: %d | ‏≥240: %d (من %d)"
              % (wk_depths[len(wk_depths)//2], wk_depths[0], wk_depths[-1],
                 sum(1 for w in wk_depths if w >= 200), sum(1 for w in wk_depths if w >= 240), len(wk_depths)))
    if ses_depths:
        print("عمق الجلسات: وسيط %d | أدنى %d | ‏≥300 (قادرو Z نظرياً): %d (من %d)"
              % (ses_depths[len(ses_depths)//2], ses_depths[0],
                 sum(1 for x in ses_depths if x >= 300), len(ses_depths)))
    if drift:
        print("⛔ حارس الانزياح الجماعي (§8): %s" % drift)
        fail_types.append("انزياح جماعي")
    if cov_fail:
        print("⛔ بوابة انهيار التغطية (§7): %s" % cov_fail)
        fail_types.append("تغطية")
    if fail_types:
        print("⛔ لا كتابة — فشل حاكم في: %s" % "، ".join(fail_types))
        sys.exit(1)

    # (ش-3) إغلاقات delisted تُكتب الآن فقط — بعد اجتياز كل بوابات الفشل
    if gone_pending:
        closed = close_delisted_recs(cfg_path, gone_pending,
                                     {s["symbol"]: s.get("currentPrice") for s in data["stocks"]}, today)
        print("  🌐 أُغلقت توصيات المشطوبين (بعد البوابات): %s" % closed)
    data["coverage"] = {"smaCapable": sma_cap, "zCapable": z_cap, "at": today}
    # قائمة أسهم المحفظة لشارة «في محفظتك» (موجة مفكرة التوزيعات 14-08):
    # رموز track=legacy من watchlist-config — الصفحة تجدها في stocks-data مباشرة
    try:
        with open(cfg_path, encoding="utf-8") as _cf:
            _cfg = json.load(_cf)
        data["portfolioSymbols"] = sorted({e["symbol"] for e in _cfg.get("stocks", [])
                                           if e.get("track") == "legacy" and e.get("symbol")})
        print("👜 portfolioSymbols: %d رمزاً (legacy) من %s" % (len(data["portfolioSymbols"]), cfg_path))
    except Exception as _e:
        print("⚠️ portfolioSymbols: تعذر قراءة config (%s) — الكتلة السابقة تبقى" % _e)
    for s in stocks:
        s.pop("_prevFinancials", None)
    data["lastUpdated"] = now_riyadh + " الرياض"
    data["priceSource"] = "sahmk-direct-v3"
    data["criteriaVersion"] = "v3"
    # ── ختم نوع التشغيلة (شرط المحلل 2 — قاعدة الإقفال الحصرية، اعتماد 05-08ب):
    # ‏close = بعد ~15:10 الرياض في يوم تداول، أو يوم غير تداولي (أسعار الملف أسعار إقفال)
    # ‏intraday = سوق مفتوح — المغذي وسكربتا الإغلاق يرفضان العمل عليه
    now_r_dt = datetime.now(RIYADH)
    trading_day = now_r_dt.weekday() in (6, 0, 1, 2, 3)   # الأحد-الخميس
    after_close = (now_r_dt.hour, now_r_dt.minute) >= PARTIAL_CUTOFF_RIYADH
    data["runType"] = "close" if (after_close or not trading_day) else "intraday"
    data["runTypeAt"] = now_riyadh
    # (06-08) ختما الحقبة القديمة البائتان — «الوسم لا يكذب»: lastUpdated كان يُختم
    # أصلاً (أعلاه)، أما هذان فبقيا بقيم 04-08 فعرضت الواجهة «أسبوعية» بعمر كاذب
    data["lastRunAt"] = now_riyadh + " الرياض"          # الدلالة التاريخية للحقل
    data["weeklyTechnicalUpdated"] = now_riyadh         # الاشتقاق الأسبوعي يجري كل تشغيلة
    print("🏷️ نوع التشغيلة: %s (%s)" % (data["runType"],
          "أسعار إقفال — العينة تعمل" if data["runType"] == "close"
          else "سوق مفتوح — لا مدخلات ولا إغلاقات للعينة"))
    # ── §4-ب: بوابة تشغيلة أولى — الإجراءات الرأسمالية المكتشفة تُطبع كلها للتحقق
    # اليدوي (سهم معروف المنحة يُقارن بإعلانات تداول)، والمقيدون يُسمّون ──
    cap_lines, restricted_syms = [], []
    for s in stocks:
        lv = s.get("levels") or {}
        for a in lv.get("capActions") or []:
            cap_lines.append("%s: ‏%s عامل %s" % (s["symbol"], a["date"], a["factor"]))
        if lv.get("restricted"):
            restricted_syms.append("%s (من %s)" % (s["symbol"], lv.get("restrictedFrom")))
    if cap_lines:
        print("🏗️ إجراءات رأسمالية مكتشفة (%d — تحقق يدوي لسهم معروف المنحة، بوابة أولى):" % len(cap_lines))
        for ln in cap_lines[:30]:
            print("   " + ln)
        if len(cap_lines) > 30:
            print("   ... و%d أخرى" % (len(cap_lines) - 30))
    if restricted_syms:
        print("⚠️ مستويات مقيدة التاريخ (كشف ملتبس — مراجعة يدوية): %s" % restricted_syms[:10])
    # ── ميزانية الرسم الشاملة (الموجة 1): series+levels ≤ +800KB والملف ≤3.3MB ──
    lev_size = sum(len(json.dumps(s.get("levels"), separators=(",", ":"), ensure_ascii=False).encode())
                   for s in stocks if s.get("levels"))
    ser_size, ser_level = enforce_series_budget(stocks, cap_bytes=800 * 1024 - lev_size)
    print("📈 سلاسل الرسم: %d سهماً بسلاسل | series ‏%.0fKB + levels ‏%.0fKB = %.0fKB (سقف شامل 800) | تقليص مستوى %d"
          % (sum(1 for s in stocks if s.get("series")), ser_size / 1024, lev_size / 1024,
             (ser_size + lev_size) / 1024, ser_level))
    out_dir = os.path.dirname(os.path.abspath(args.data)) or "."
    FILE_CAP = int(3.3 * 1024 * 1024)
    for attempt in range(3):
        fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            # قرار معلن (الموجة 1): إخراج مضغوط بلا indent — قياس فعلي: ‏indent=1 يجعل
            # كلفة series ‏1238KB والملف 3.52MB؛ الضغط الكامل: الكلفة ~554KB والملف 2.40MB
            # (وحجم الصفحة المحقونة ينخفض عن الوضع القائم أصلاً). المحرك يكتب بالاصطلاح نفسه.
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        fsize = os.path.getsize(tmp)
        if fsize <= FILE_CAP or ser_level >= 3:
            break
        os.unlink(tmp)
        # الملف النهائي فوق 3.3MB → نصعّد التقليص درجة ونعيد الكتابة
        ser_size, ser_level = enforce_series_budget(stocks, cap_bytes=0 if ser_level >= 2 else ser_size - 1)
        print("📉 الملف النهائي %.2fMB > 3.3MB — صعّدنا تقليص series إلى مستوى %d" % (fsize / 1048576, ser_level))
    print("📦 حجم الملف النهائي: %.2fMB (سقف 3.30)" % (fsize / 1048576))
    if fsize > FILE_CAP:
        print("⚠️ ALERT: الملف فوق السقف حتى بعد أقصى تقليص — راجع الميزانية")
    os.replace(tmp, args.data)
    try:
        os.chmod(args.data, 0o664)
    except OSError:
        pass
    print("✅ كُتب %s (ذرياً) — التالي: python3 scripts/scoring-engine.py %s" % (args.data, args.data))


if __name__ == "__main__":
    main()
