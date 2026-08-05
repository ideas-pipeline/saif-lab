#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سيف تداول — Scoring Engine v2.0 (criteria v3)
=============================================
المرجع الحاكم: docs/requirements-v3.md — المقام 100 مباشرة (لا معايرة):
جودة 30 + اتجاه 25 + قوة نسبية 15 + مخاطر 15 + تقييم 15.

قرار معماري معلن: **منطق التقييم (compute-valuation) مدموج هنا** — P/E وP/B والعائد
تُحسب يومياً بالسعر الحي على آخر أساسيات أسبوعية (§3.5)، ووسطاء القطاعات تُحسب هنا
أيضاً (محور الجودة يحتاج وسيط الهامش ومحور التقييم وسطاءه والقوة النسبية وسيط 6م) —
مكان واحد لكل الوسطاء = صفر انزياح تشغيلي بينها. compute-valuation.py صار stub.

الطبقات (§2): فلاتر إقصائية (مالية موجودة / بوابة سيولة ≥1م ريال / فلتر SMA200W
باستثناء الانعكاس / unrated) ← المحاور ← طبقة الدخول (لا نقاط — §4) ← التصنيف السباعي.

حالات غموض حُسمت بأقرب قراءة للنص (لا اجتهاد منهجي — موثقة للمراجعة):
  غ-1: إشارات ≥3 لكن الإشارة 1 (سعر>EMA50) سالبة — الجدول لا يغطيها نصاً: 🟢 يشترط
       الإشارة 1 و🔴 يشترط ≤1. حُسمت 🟡 («المستوى مستوى استعادة») — الأقرب لدلالة
       الجدول، والمستوى المرجعي يكون فوق السعر فيصاغ استعادةً بقاعدة §4.2.
  غ-2: قطاع بأقل من 5 قيم صالحة في P/E أو P/B — الوثيقة تنص البدائل المطلقة للهامش
       فقط: حُسم استخدام وسيط السوق الكامل مرجعاً بديلاً (أقرب تعميم لروح «مرجع
       تسعير سوقي»)، موسوماً في details بـ«(مرجع السوق)».

بوابتا معقولية في المحرك (§8): قفزة وسيط P/B قطاعي ×5 عن المخزون، وتغير تصنيف
>25% من الكون عن المخزون ⇒ خروج 1 بلا كتابة.

الاستخدام: python3 scripts/scoring-engine.py [stocks-data.json]
"""
import json, sys, statistics

Q, T, R, K, V = 30, 25, 15, 15, 15   # سقوف المحاور — المجموع 100


# ═══════════════ الوسطاء (§6-7) ═══════════════

def compute_medians(stocks):
    """من الكون المدرج الكامل (غير المشطوب) — P/E وP/B والعائد من الموجبة فقط،
    الهامش وعائد 6م من كل القيم موجبها وسالبها (قواعد الإشارة المنصوصة)"""
    secs = {}
    market = {"pe": [], "pb": [], "dy": [], "margin": [], "r6": []}
    for s in stocks:
        sec = s.get("sector")
        v = s.get("valuation") or {}
        fin = s.get("financials") or {}
        agg = secs.setdefault(sec, {"pe": [], "pb": [], "dy": [], "margin": [], "r6": [], "n": 0}) if sec else None
        if agg is not None:
            agg["n"] += 1
        def push(key, val, positive_only):
            if val is None:
                return
            if positive_only and val <= 0:
                return
            market[key].append(val)
            if agg is not None:
                agg[key].append(val)
        push("pe", v.get("pe"), True)
        push("pb", v.get("pb"), True)
        push("dy", v.get("dividendYield"), True)
        push("margin", fin.get("profitMargins"), False)
        push("r6", (s.get("relativeStrength") or {}).get("return6m"), False)
    def med(lst, dp=4):
        return round(statistics.median(lst), dp) if lst else None
    out = {}
    for sec, a in secs.items():
        out[sec] = {"peMedian": med(a["pe"], 2), "pePool": len(a["pe"]),
                    "pbMedian": med(a["pb"], 2), "pbPool": len(a["pb"]),
                    "divYieldMedian": med(a["dy"], 4), "dyPool": len(a["dy"]),
                    "marginMedian": med(a["margin"], 1), "marginPool": len(a["margin"]),
                    "ret6mMedian": med(a["r6"], 2), "r6Pool": len(a["r6"]),
                    "count": a["n"]}
    out["_market"] = {"peMedian": med(market["pe"], 2), "pbMedian": med(market["pb"], 2),
                      "marginMedian": med(market["margin"], 1)}
    return out


def compute_valuation(s, today_ref):
    """P/E وP/B يومياً بالسعر الحي على آخر أساسيات أسبوعية + العائد (§3.5 مدموجاً)"""
    vi = s.get("valuationInputs") or {}
    price = s.get("currentPrice")
    v = {}
    rejects = []
    eps = vi.get("eps")
    if price and eps and eps > 0:
        pe = round(price / eps, 2)
        if 0 < pe <= 500:
            v["pe"] = pe
        else:
            rejects.append(("pe", pe, "خارج (0،500]"))
            v["pe"] = None
    else:
        v["pe"] = None    # خاسرة/بلا eps → صفر P/E عمداً (§3.5 — حسم فرضية 2)
    bv = vi.get("bookValue")
    if price and bv and bv > 0:
        pb = round(price / bv, 3)
        if 0.05 <= pb <= 50:
            v["pb"] = pb
        else:
            rejects.append(("pb", pb, "خارج [0.05،50]"))
            v["pb"] = None
    else:
        v["pb"] = None
    dv = vi.get("divTtm12m")
    v["dividendYield"] = round(dv / price, 6) if (price and dv and dv > 0) else (0.0 if dv == 0.0 else None)
    # حارس تقاطع pe المصدر (§3.5): فرق >10% → يعد لإنذار L1
    pe_src = vi.get("peSource")
    if v.get("pe") and pe_src and pe_src > 0:
        diff = abs(v["pe"] - pe_src) / pe_src * 100
        v["peSourceDiffPct"] = round(diff, 1)
    s["valuation"] = v
    for fld, val, why in rejects:
        s.setdefault("guardRejected", []).append({"field": fld, "value": val, "reason": why, "date": today_ref})
    return v


# ═══════════════ التصنيف البنكي ═══════════════

def is_bank(s):
    sec = (s.get("sector") or "").lower()
    ind = (s.get("industry") or "").lower()
    sec_fin = ("financ" in sec) or ("مالية" in sec) or ("مصارف" in sec) or ("بنوك" in sec)
    ind_bank = ("bank" in ind) or ("بنك" in ind) or ("مصرف" in ind)
    return (sec_fin and ind_bank) if sec else ind_bank


# ═══════════════ المحاور (§3) ═══════════════

def axis_quality(s, medians):
    """الجودة 30: عام = نمو6+هامش6(نسبي قطاعياً)+ROE6+D/E6+جودة نقد6
                 بنوك = ROA10+ROE8+هامش6(مطلق)+نمو6"""
    fin = s.get("financials") or {}
    d = []
    sc = 0
    if is_bank(s):
        roa = fin.get("returnOnAssets")
        if roa is not None:
            p = 10 if roa > 2.2 else 7 if roa > 1.8 else 4 if roa > 1.4 else 2 if roa > 0.8 else 0
            sc += p; d.append("ROA %s%% → %d/10" % (roa, p))
        else:
            d.append("ROA غير متوفر → 0/10")
        roe = fin.get("returnOnEquity")
        if roe is not None:
            p = 8 if roe > 18 else 6 if roe > 14 else 4 if roe > 10 else 2 if roe > 5 else 0
            sc += p; d.append("ROE %s%% → %d/8" % (roe, p))
        else:
            d.append("ROE غير متوفر → 0/8")
        pm = fin.get("profitMargins")
        if pm is not None:
            p = 6 if pm > 50 else 5 if pm > 40 else 3 if pm > 30 else 1 if pm > 20 else 0
            sc += p; d.append("هامش %s%% (مطلق بنوك) → %d/6" % (pm, p))
        else:
            d.append("هامش غير متوفر → 0/6")
        rg = fin.get("revenueGrowth")
        if rg is not None:
            p = 6 if rg > 15 else 5 if rg > 8 else 3 if rg > 3 else 1 if rg >= 0 else 0
            sc += p; d.append("نمو %s%% → %d/6" % (rg, p))
        else:
            d.append("نمو غير متوفر/راسب الحارس → 0/6")
        return sc, d
    # المسار العام
    rg = fin.get("revenueGrowth")
    if rg is not None:
        p = 6 if rg > 15 else 5 if rg > 8 else 4 if rg > 3 else 2 if rg >= 0 else 0
        sc += p; d.append("نمو %s%% → %d/6" % (rg, p))
    else:
        d.append("نمو غير متوفر → 0/6")
    pm = fin.get("profitMargins")
    sm = medians.get(s.get("sector")) or {}
    if pm is not None:
        if (sm.get("marginPool") or 0) >= 5 and sm.get("marginMedian") is not None:
            diff = pm - sm["marginMedian"]
            p = 6 if diff > 10 else 5 if diff > 3 else 3 if diff > -3 else 1 if diff > -10 else 0
            sc += p; d.append("هامش %s%% مقابل وسيط قطاعه %s%% (%+.1f ن.م) → %d/6" % (pm, sm["marginMedian"], diff, p))
        else:
            p = 6 if pm > 20 else 5 if pm > 12 else 3 if pm > 5 else 1 if pm >= 0 else 0
            sc += p; d.append("هامش %s%% (سلم مطلق — قطاع <5 مؤهلين) → %d/6" % (pm, p))
    else:
        d.append("هامش غير متوفر → 0/6")
    roe = fin.get("returnOnEquity")
    if roe is not None:
        p = 6 if roe > 18 else 5 if roe > 12 else 3 if roe > 8 else 1 if roe >= 0 else 0
        sc += p; d.append("ROE %s%% → %d/6" % (roe, p))
    else:
        d.append("ROE غير متوفر/راسب → 0/6")
    de = fin.get("debtToEquity")
    if de is not None:
        p = 6 if de < 30 else 5 if de < 80 else 3 if de < 150 else 1 if de < 300 else 0
        sc += p; d.append("D/E %s%% → %d/6" % (de, p))
    else:
        d.append("D/E غير متوفر/راسب → 0/6")
    ocf, ni = fin.get("ocf"), fin.get("netIncome")
    if ocf is not None and ocf > 0:
        p = 6 if (ni is not None and ocf >= ni) or ni is None else 4
        sc += p; d.append("جودة نقد: OCF %s %s → %d/6" % (
            ocf, "≥ صافي الربح" if p == 6 else "> 0", p))
    else:
        d.append("OCF ≤ 0 أو غائب → 0/6")
    return sc, d


def axis_trend(s):
    """الاتجاه 25 — بنية v2.1 بحذافيرها على المشتقة (§3.2)؛ السعر = آخر إغلاق يومي"""
    wt = s.get("weeklyTechnical") or {}
    price = wt.get("priceRef") or (s.get("dailyExtra") or {}).get("lastClose") or s.get("currentPrice")
    d = []
    sc = 0
    sma, slope = wt.get("sma200w"), wt.get("sma200wSlope")
    if sma and price:
        if price > sma:
            p = 8 if (slope or 0) > 1 else 6 if (slope or 0) > -1 else 3
        else:
            p = 2 if (price - sma) / sma * 100 > -3 else 0
        sc += p; d.append("SMA200W %s (ميل %s%%) → %d/8" % (sma, slope, p))
    else:
        d.append("SMA200W غير متوفر → 0/8")
    ema40 = wt.get("ema40w")
    if ema40 and sma and price:
        p = 7 if (price > ema40 and ema40 > sma) else 4 if price > ema40 else 2 if price > sma else 0
        sc += p; d.append("EMA40W %s → %d/7" % (ema40, p))
    else:
        d.append("EMA40W/تسلسل غير متوفر → 0/7")
    rsi = wt.get("rsi14w")
    if rsi is not None:
        p = 5 if 55 <= rsi <= 70 else 4 if 50 <= rsi < 55 else 3 if 70 < rsi <= 80 else 2 if 40 <= rsi < 50 else 1
        sc += p; d.append("RSI-W %s → %d/5" % (rsi, p))
    else:
        d.append("RSI-W غير متوفر → 0/5")
    m, sig = wt.get("macdW"), wt.get("macdSignalW")
    if m is not None and sig is not None:
        p = 5 if (m > sig and m > 0) else 4 if (m > sig) else 2 if m > 0 else 0
        sc += p; d.append("MACD-W %s/%s → %d/5" % (m, sig, p))
    else:
        d.append("MACD-W غير متوفر → 0/5")
    return sc, d


def axis_rs(s, medians):
    """القوة النسبية 15 (§3.3): 12-1(4) + 6م(4) + قطاع 6م(4) + 3م(3)"""
    rs = s.get("relativeStrength") or {}
    d = []
    sc = 0
    LADDER4 = lambda x: 4 if x > 10 else 3 if x > 3 else 2 if x > -3 else 1 if x > -10 else 0
    v = rs.get("rsTasi12_1")
    if v is not None:
        p = LADDER4(v); sc += p; d.append("مقابل تاسي 12-1: %+.1f%% → %d/4" % (v, p))
    else:
        d.append("12-1 غير متوفر → 0/4")
    v = rs.get("rsTasi6m")
    if v is not None:
        p = LADDER4(v); sc += p; d.append("مقابل تاسي 6م: %+.1f%% → %d/4" % (v, p))
    else:
        d.append("6م غير متوفر → 0/4")
    r6 = rs.get("return6m")
    sm = medians.get(s.get("sector")) or {}
    if r6 is not None and sm.get("ret6mMedian") is not None:
        v = r6 - sm["ret6mMedian"]
        p = LADDER4(v); sc += p; d.append("مقابل قطاعه 6م: %+.1f%% → %d/4" % (v, p))
    else:
        d.append("قطاع 6م غير متوفر → 0/4")
    v = rs.get("rsTasi3m")
    if v is not None:
        p = 3 if v > 5 else 2 if v > 1 else 1 if v > -5 else 0
        sc += p; d.append("مقابل تاسي 3م: %+.1f%% → %d/3" % (v, p))
    else:
        d.append("3م غير متوفر → 0/3")
    return sc, d


def axis_risk(s):
    """المخاطر 15 (§3.4): ATR%4 + Z3 + قيمة تداول3 + اتجاه حجم2 + ملاءة3"""
    de = s.get("dailyExtra") or {}
    fin = s.get("financials") or {}
    d = []
    sc = 0
    atr = de.get("atrPct")
    if atr is not None:
        p = 4 if atr < 1.5 else 3 if atr < 2.5 else 1 if atr < 4 else 0
        sc += p; d.append("ATR%% ‏%s → %d/4" % (atr, p))
    else:
        d.append("ATR غير متوفر → 0/4")
    z = (s.get("weeklyTechnical") or {}).get("zExt")
    if z is not None:
        az = abs(z)
        p = 3 if az < 1 else 2 if az < 2 else 1 if az < 3 else 0
        sc += p; d.append("Z-امتداد %+.1f → %d/3" % (z, p))
    else:
        d.append("Z غير متوفر (تاريخ < 240 أسبوعاً) → 0/3")
    tv = de.get("tradingValueMedian20")
    if tv is not None:
        p = 3 if tv > 20e6 else 2 if tv > 5e6 else 1 if tv > 1e6 else 0
        sc += p; d.append("قيمة تداول %s ريال → %d/3" % (f"{tv:,.0f}", p))
    else:
        d.append("قيمة التداول غير متوفرة → 0/3")
    a20, a50 = de.get("avgVol20"), de.get("avgVol50")
    if a20 and a50:
        r = a20 / a50
        p = 2 if r > 1.2 else 1 if r > 0.8 else 0
        sc += p; d.append("حجم 20/50: %.2f → %d/2" % (r, p))
    else:
        d.append("اتجاه الحجم غير متوفر → 0/2")
    if is_bank(s):
        ea = fin.get("equityAssets")
        if ea is not None:
            p = 3 if ea > 13 else 2 if ea > 10 else 1 if ea > 8 else 0
            sc += p; d.append("رفع رأسمالي (ملكية/أصول) %s%% → %d/3" % (ea, p))
        else:
            d.append("رفع رأسمالي غير متوفر → 0/3")
    else:
        ol = fin.get("ocfLiabilities")
        if ol is not None and (fin.get("ocf") or 0) > 0:
            p = 3 if ol > 0.20 else 2 if ol > 0.10 else 1 if ol > 0.05 else 0
            sc += p; d.append("‏Beaver ‏OCF/مطلوبات %.2f → %d/3" % (ol, p))
        else:
            d.append("‏Beaver غير متوفر أو OCF≤0 → 0/3")
    return sc, d


def axis_valuation(s, medians):
    """التقييم 15 (§3.5): P/E قطاعي6 + P/B قطاعي5 + عائد4 — الخاسرة صفر P/E عمداً"""
    v = s.get("valuation") or {}
    sm = medians.get(s.get("sector")) or {}
    mkt = medians.get("_market") or {}
    d = []
    sc = 0
    pe = v.get("pe")
    ref, tag = (sm.get("peMedian"), "قطاعه") if (sm.get("pePool") or 0) >= 5 else (mkt.get("peMedian"), "السوق (غ-2)")
    if pe and ref:
        r = pe / ref
        p = 6 if r < 0.7 else 5 if r < 0.9 else 3 if r < 1.1 else 1 if r < 1.5 else 0
        sc += p; d.append("P/E %.1f مقابل وسيط %s %.1f (%.2fx) → %d/6" % (pe, tag, ref, r, p))
    elif pe is None:
        d.append("P/E غير معرف (خاسرة/بلا eps) → 0/6 — تحفظ مقصود")
    else:
        d.append("لا وسيط مرجعي → 0/6")
    pb = v.get("pb")
    ref, tag = (sm.get("pbMedian"), "قطاعه") if (sm.get("pbPool") or 0) >= 5 else (mkt.get("pbMedian"), "السوق (غ-2)")
    if pb and ref:
        r = pb / ref
        p = 5 if r < 0.6 else 4 if r < 0.8 else 2 if r < 1.1 else 1 if r < 1.4 else 0
        sc += p; d.append("P/B %.2f مقابل وسيط %s %.2f (%.2fx) → %d/5" % (pb, tag, ref, r, p))
    else:
        d.append("P/B غير متوفر → 0/5")
    dy = v.get("dividendYield")
    if dy is not None and dy > 0:
        pct = dy * 100
        p = 4 if pct > 4 else 3 if pct > 2 else 1 if pct > 0.5 else 0
        sc += p; d.append("عائد %.1f%% → %d/4" % (pct, p))
    elif dy == 0.0:
        d.append("لا يوزع → 0/4")
    else:
        d.append("عائد غير متوفر → 0/4")
    return sc, d


# ═══════════════ طبقة الدخول (§4 — لا نقاط) ═══════════════

def entry_layer(s, regime):
    de = s.get("dailyExtra") or {}
    price = de.get("lastClose") or s.get("currentPrice")
    sigs, avail = 0, 0
    det = []
    sig1 = None
    ema50 = de.get("ema50d")
    if ema50 is not None and price:
        avail += 1
        sig1 = price > ema50
        sigs += 1 if sig1 else 0
        det.append(("✅" if sig1 else "⚠️") + " سعر مقابل EMA50")
    rsi = de.get("rsi14d")
    if rsi is not None:
        avail += 1
        ok = 40 <= rsi <= 65
        sigs += 1 if ok else 0
        det.append(("✅" if ok else "⚠️") + " RSI-D %s" % rsi)
    m, sg = de.get("macdD"), de.get("macdSignalD")
    if m is not None and sg is not None:
        avail += 1
        ok = m > sg
        sigs += 1 if ok else 0
        det.append(("✅" if ok else "⚠️") + " MACD-D")
    a20, a50 = de.get("avgVol20"), de.get("avgVol50")
    if a20 and a50:
        avail += 1
        ok = a20 > a50
        sigs += 1 if ok else 0
        det.append(("✅" if ok else "⚠️") + " حجم 20>50")
    # المستوى المرجعي (§4.2): الأعلى من EMA50 وأدنى إغلاق 20 جلسة — «تقريبي» ملزم
    lvl = None
    cand = [x for x in (ema50, de.get("low20Close")) if x is not None]
    if cand:
        lvl = round(max(cand), 2)
    lvl_type = None
    if lvl is not None and price:
        lvl_type = "entry" if lvl <= price else "reclaim"   # دلالة الموقع (§4.2)
    atr = de.get("atr14")
    ext = round((price - lvl) / atr, 2) if (lvl is not None and price and atr) else None
    hi52 = de.get("high52wClose")
    near_high = bool(hi52 and price and price >= 0.98 * hi52 and rsi is not None and rsi > 65)
    # الحالة الثلاثية (§4.3)
    if avail == 0:
        state, phrase = "neutral", "بيانات التوقيت غير كافية"
    elif sigs >= 3 and sig1 and ext is not None and ext <= 2 and not near_high:
        state = "green"
        phrase = "السعر مناسب والتوقيت مناسب — الدخول قرب %s تقريباً" % lvl
    elif sigs >= 3 and not sig1:
        # غ-1 المحسومة: قوي الإشارات لكنه ليس فوق متوسطه الخمسيني — لا «دخول الآن».
        # (تحسين الناقد أ) توحيد الدلالة عند التعادل سعر==EMA50: sig1 يتطلب > حرفياً
        # فيسقط، لكن المستوى ≤ السعر = منطقة دخول (§4.2) — فالصياغة تتبع نوع المستوى
        # لا تفترض الاستعادة: تعادل → «على دفعات قرب»، وتحت فعلاً → «استعادة».
        state = "yellow"
        phrase = ("سهم جيد لكنه تحت متوسطه — راقب استعادة السعر فوق %s تقريباً" % lvl
                  if lvl_type == "reclaim"
                  else "سهم جيد — الأفضل الدخول على دفعات قرب %s تقريباً" % lvl)
    elif sigs == 2 or (sigs >= 3 and (ext is None or ext > 2 or near_high)):
        state = "yellow"
        if ext is None and sigs >= 3:
            phrase = "سهم جيد لكن بيانات التذبذب ناقصة — الأفضل الدخول على دفعات قرب %s تقريباً" % lvl
        elif near_high and sigs >= 3:
            phrase = "قرب القمة — لا تطارد؛ الأفضل الدخول على دفعات أو انتظار تراجع نحو %s تقريباً" % lvl
        else:
            phrase = "سهم جيد لكن السعر متقدم — الأفضل الدخول على دفعات أو انتظار تراجع نحو %s تقريباً" % lvl
    else:
        state = "red"
        phrase = ("سهم جيد لكن التوقيت غير مناسب الآن — راقبه فوق %s تقريباً" % lvl) if lvl else \
                 "التوقيت غير مناسب الآن"
    # تكييف النظام (§4.3): 🔴 هابط → 🟢 تهبط صياغة إلى 🟡 دون مساس بالتصنيف
    display = state
    if regime == "هابط" and state == "green":
        display = "yellow"
        phrase = "البيئة العامة ضاغطة — تدرّج: %s" % phrase
    timing = {"green": "ممتاز", "yellow": "مقبول", "red": "انتظر", "neutral": "محايد"}[state]
    return {"state": state, "displayState": display, "phrase": phrase,
            "signals": sigs, "signalsAvailable": avail, "signalDetails": det,
            "referenceLevel": lvl, "referenceLevelType": lvl_type,
            "extensionAtr": ext, "nearHighWarning": near_high,
            "timing": timing}


# ═══════════════ الفلاتر والتصنيف ═══════════════

REVERSAL = "تحت SMA200W لكن إشارات انعكاس"

def investment_filter(s):
    fin = s.get("financials") or {}
    if not fin:
        return False, "لا توجد بيانات مالية"
    wt = s.get("weeklyTechnical") or {}
    price = wt.get("priceRef") or (s.get("dailyExtra") or {}).get("lastClose") or s.get("currentPrice")
    sma = wt.get("sma200w")
    if sma and price and price < sma:
        ema40, rsi = wt.get("ema40w"), wt.get("rsi14w")
        m, sg = wt.get("macdW"), wt.get("macdSignalW")
        if (ema40 and price > ema40 and rsi and rsi > 50
                and m is not None and sg is not None and m > sg):
            return True, REVERSAL
        return False, "تحت SMA200W بدون إشارات انعكاس"
    return True, "عدّى الفلتر"


def classify(total, timing):
    if total >= 80:
        return ("شراء قوي", "strong_buy") if timing == "ممتاز" else \
               ("شراء", "buy") if timing == "مقبول" else ("شراء — انتظر توقيت", "buy_wait")
    if total >= 65:
        return ("شراء", "buy") if timing == "ممتاز" else \
               ("شراء مشروط", "conditional_buy") if timing == "مقبول" else ("انتظار", "hold")
    if total >= 50:
        return "انتظار", "hold"
    if total >= 35:
        return "بيع", "sell"
    return "بيع قوي", "strong_sell"


def build_top_drivers(s, medians):
    pos, neg = [], []
    fin = s.get("financials") or {}
    wt = s.get("weeklyTechnical") or {}
    price = (s.get("dailyExtra") or {}).get("lastClose") or s.get("currentPrice")
    roe = fin.get("returnOnEquity")
    if roe is not None and roe >= 18:
        pos.append("ROE قوي %s%%" % roe)
    rg = fin.get("revenueGrowth")
    if rg is not None and rg >= 15:
        pos.append("نمو إيرادات %s%%" % rg)
    ocf = fin.get("ocf")
    ni = fin.get("netIncome")
    if ocf is not None and ni is not None and ocf > 0 and ocf >= ni:
        pos.append("نقد تشغيلي يغطي الأرباح")
    sma = wt.get("sma200w")
    if price and sma:
        (pos if price > sma else neg).append("فوق SMA200W" if price > sma else "تحت SMA200W")
    rs6 = (s.get("relativeStrength") or {}).get("rsTasi6m")
    if rs6 is not None:
        if rs6 > 10:
            pos.append("يتفوق على تاسي %+.0f%% (6م)" % rs6)
        elif rs6 < -10:
            neg.append("أضعف من تاسي %+.0f%% (6م)" % rs6)
    v = s.get("valuation") or {}
    sm = medians.get(s.get("sector")) or {}
    if v.get("pe") and sm.get("peMedian"):
        r = v["pe"] / sm["peMedian"]
        if r < 0.7:
            pos.append("أرخص من قطاعه (P/E)")
        elif r > 1.3:
            neg.append("أغلى من قطاعه (P/E)")
    z = wt.get("zExt")
    if z is not None and abs(z) >= 2:
        neg.append("ممتد عن متوسطه (Z %+.1f)" % z)
    atr = (s.get("dailyExtra") or {}).get("atrPct")
    if atr is not None and atr > 4:
        neg.append("تذبذب مرتفع ATR %s%%" % atr)
    out = [{"text": t, "type": "positive"} for t in pos[:2]]
    if neg:
        out.append({"text": neg[0], "type": "negative"})
    elif len(pos) > 2:
        out.append({"text": pos[2], "type": "positive"})
    return out


# ═══════════════ التشغيل ═══════════════

def run(data_path, activation=False):
    with open(data_path) as f:
        data = json.load(f)
    today = str(data.get("lastUpdated", ""))[:10]
    # ش-1 (قفل التفعيل): --activation لمرة واحدة بقرار مالك — يتخطى بوابتي المعقولية
    # (التصنيفات >25% ووسيط P/B ×5) لأن أول تشغيلة v3 على بيانات v2.1 تفجرهما حتماً
    # (أثبته الناقد: 222/248 تغير تصنيف). الحدث يُسجل activationEvent، وإعادة التفعيل
    # على نسخة مفعلة أصلاً تُرفض.
    if activation:
        ev = data.get("activationEvent") or {}
        if ev.get("version") == "criteria-v3":
            print("⛔ --activation مرفوض: criteria v3 مفعلة أصلاً (activationEvent بتاريخ %s) —"
                  " البوابات تعمل عادية بدونه" % ev.get("date"))
            sys.exit(1)
        print("█" * 60)
        print("█ تشغيلة تفعيل criteria v3 — قطع عينة متعمد موسوم بقرار المالك █")
        print("█ بوابتا التصنيفات (>25%) وعناقيد P/B (×5) متخطاتان لهذه التشغيلة فقط █")
        print("█" * 60)
    stocks = [s for s in data.get("stocks", []) if s.get("symbol") and not s.get("delisted")]
    regime = (data.get("marketRegime") or {}).get("regime", "")

    # 1) التقييم اليومي المحلي ثم الوسطاء (§3.5 + §6-7)
    for s in stocks:
        compute_valuation(s, today)
    medians = compute_medians(stocks)
    # بوابة عناقيد مقياس P/B (§8): قفزة وسيط قطاع ×5 عن المخزون
    old_med = data.get("sectorMedians") or {}
    pb_alerts = []
    for sec, m in medians.items():
        if sec == "_market":
            continue
        old_pb = (old_med.get(sec) or {}).get("pbMedian")
        new_pb = m.get("pbMedian")
        if old_pb and new_pb and (new_pb / old_pb >= 5 or old_pb / new_pb >= 5):
            pb_alerts.append("%s: ‏%s→%s" % (sec, old_pb, new_pb))
    if pb_alerts:
        if activation:
            print("⚠️ حارس عناقيد P/B متخطى بالتفعيل (موسوم): %s" % pb_alerts)
        else:
            print("⛔ حارس عناقيد مقياس P/B (§8): %s — لا كتابة، تحقيق أولاً" % pb_alerts)
            sys.exit(1)

    prev_class = {s["symbol"]: (s.get("investmentScore") or {}).get("classification") for s in stocks}
    stats = {}
    for s in stocks:
        passed, reason = investment_filter(s)
        wt = s.get("weeklyTechnical") or {}
        unrated = passed and not wt.get("sma200w")
        entry = entry_layer(s, regime)
        if not passed:
            s["investmentScore"] = {
                "total": 0, "filtered": True, "unrated": False, "filterReason": reason,
                "classification": "مستبعد", "classCode": "filtered",
                "timing": entry["timing"], "timingSignals": entry["signals"],
                "entry": entry, "riskReasons": [], "topDrivers": [],
                "criteriaVersion": "v3",
            }
            stats["filtered"] = stats.get("filtered", 0) + 1
            continue
        q, qd = axis_quality(s, medians)
        t, td = axis_trend(s)
        r, rd = axis_rs(s, medians)
        k, kd = axis_risk(s)
        v, vd = axis_valuation(s, medians)
        total = q + t + r + k + v          # المقام 100 مباشرة — لا معايرة (§1)
        cls, code = classify(total, entry["timing"])
        if unrated:
            cls, code = "غير مُقيَّم", "unrated"
        s["investmentScore"] = {
            "total": total,
            "quality": q, "trend": t, "relativeStrength": r, "risk": k, "valuation": v,
            "classification": cls, "classCode": code,
            "filtered": False, "unrated": unrated, "filterReason": reason,
            "viaReversal": reason == REVERSAL,
            "timing": entry["timing"], "timingSignals": entry["signals"],
            "entry": entry,
            "liquidityBlocked": not (s.get("liquidityGate") or {}).get("passed", True),
            "details": {"quality": qd, "trend": td, "relativeStrength": rd,
                        "risk": kd, "valuation": vd, "timing": entry["signalDetails"]},
            "topDrivers": build_top_drivers(s, medians),
            "criteriaVersion": "v3",
        }
        stats[code] = stats.get(code, 0) + 1

    # بوابة التصنيفات (§8): تغير >25% من الكون عن المخزون → إيقاف وتحقيق
    changed = sum(1 for s in stocks
                  if prev_class.get(s["symbol"]) and
                  prev_class[s["symbol"]] != s["investmentScore"]["classification"])
    with_prev = sum(1 for s in stocks if prev_class.get(s["symbol"]))
    if with_prev >= 20 and changed > 0.25 * with_prev:
        if activation:
            print("⚠️ بوابة التصنيفات متخطاة بالتفعيل (موسوم): تغير %d/%d" % (changed, with_prev))
        else:
            print("⛔ بوابة التصنيفات (§8): تغير %d/%d (>25%%) — لا كتابة، تحقيق أولاً" % (changed, with_prev))
            sys.exit(1)

    if activation:
        data["activationEvent"] = {"version": "criteria-v3", "date": today or None,
                                   "classChanged": "%d/%d" % (changed, with_prev),
                                   "note": "تشغيلة تفعيل — قطع عينة متعمد موسوم بقرار المالك"}
    data["sectorMedians"] = {k2: v2 for k2, v2 in medians.items() if k2 != "_market"}
    data["marketMedians"] = medians["_market"]
    data["scoringVersion"] = "criteria-v3"
    with open(data_path, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)

    print("=" * 50)
    print("📊 سيف تداول — criteria v3 (مقام 100)")
    for code, label in (("strong_buy", "⭐⭐⭐ شراء قوي"), ("buy", "⭐⭐ شراء"),
                        ("buy_wait", "⭐⭐ شراء-انتظر"), ("conditional_buy", "⭐ مشروط"),
                        ("hold", "⏳ انتظار"), ("sell", "🔻 بيع"), ("strong_sell", "🔻🔻 بيع قوي"),
                        ("unrated", "⏸ غير مُقيَّم"), ("filtered", "⛔ مستبعد")):
        print("%s: %d" % (label, stats.get(code, 0)))
    blocked = sum(1 for s in stocks if (s.get("investmentScore") or {}).get("liquidityBlocked"))
    print("💧 محجوب سيولةً (معروض موسوماً): %d" % blocked)
    rated = [s for s in stocks if s["investmentScore"]["classCode"] not in ("filtered", "unrated")]
    rated.sort(key=lambda x: -x["investmentScore"]["total"])
    print("🏆 أعلى 10:")
    for s in rated[:10]:
        sc = s["investmentScore"]
        print("  %s (%s): %d/100 — %s | دخول: %s" % (
            s.get("name", ""), s["symbol"], sc["total"], sc["classification"],
            sc["entry"]["displayState"]))


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:]]
    activation = "--activation" in argv
    argv = [a for a in argv if a != "--activation"]
    run(argv[0] if argv else "/srv/ideas/stocks-data.json", activation=activation)
