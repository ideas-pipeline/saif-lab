#!/usr/bin/env python3
"""
سيف تداول — نموذج التقييم الاستثماري المتوسط
Scoring Engine v1.1
105 نقطة خام (تُعاير إلى 100) = 5 محاور × أوزان مختلفة

v1.1: قواعد متخصصة للبنوك (ROA + Cost-to-Income من Yahoo Finance)
      التأمين والقطاعات الأخرى = قواعد عامة (بدون تغيير)
"""
import json, sys

def compute_risk_reasons(s):
    # (2026-07-24) بانرات مخاطر حية بدل الحفرية الموروثة — العتبات تطابق محور المخاطر
    reasons = []
    wt = s.get("weeklyTechnical") or {}
    de = s.get("dailyExtra") or {}
    price = s.get("currentPrice")
    sma = wt.get("sma200w")
    if price and sma and price < sma:
        reasons.append(f"تحت SMA200W بـ {round((sma - price) / sma * 100)}%")
    rsi = wt.get("rsi14w")
    if rsi is not None and rsi < 40:
        reasons.append(f"RSI أسبوعي ضعيف ({rsi})")
    atr = de.get("atrPct")
    if atr is not None and atr >= 3.5:
        reasons.append(f"تقلب مرتفع (ATR {atr}%)")
    h52 = de.get("high52w")
    if h52 and price and h52 > 0:
        dist = (h52 - price) / h52 * 100
        if dist >= 25:
            reasons.append(f"بعد {dist:.0f}% عن القمة السنوية")
    avg50 = de.get("avgVol50")
    if avg50 and avg50 < 50000:
        reasons.append("سيولة ضعيفة (متوسط 50ي تحت 50 ألفا)")
    return reasons

def score_financial_health(stock):
    """المحور 1: الصحة المالية (30 نقطة)
    البنوك: قواعد متخصصة (ROA + Cost-to-Income + ROE + نمو + هامش ربح)
    الباقي: قواعد عامة (نمو + هامش + ROE + D/E + CR + OCF)
    """
    fin = stock.get('financials', {})
    sf = stock.get('sectorFinancials', {})
    industry = stock.get('industry') or ''
    
    is_bank = 'Bank' in industry
    has_bank_data = sf.get('type') == 'bank' and 'ROA' in sf and 'costToIncome' in sf
    
    if is_bank and has_bank_data:
        return _score_bank_financial(fin, sf)
    else:
        return _score_generic_financial(fin, stock)


def _score_bank_financial(fin, sf):
    """قواعد البنوك المتخصصة (30 نقطة)
    ROA(7) + Cost-to-Income(7) + ROE(5) + نمو(5) + هامش(6) = 30
    """
    score = 0
    details = []
    
    # 1. ROA (7 pts) — أهم مؤشر ربحية للبنوك
    roa = sf.get('ROA')
    if roa is not None:
        if roa > 2.0: pts = 7
        elif roa > 1.5: pts = 5
        elif roa > 1.0: pts = 3
        elif roa > 0.5: pts = 1
        else: pts = 0
        score += pts
        details.append(f"ROA {roa}% → {pts}/7")
    
    # 2. Cost-to-Income / Efficiency Ratio (7 pts) — كفاءة التشغيل
    cti = sf.get('costToIncome')
    if cti is not None:
        if cti < 30: pts = 7
        elif cti < 35: pts = 5
        elif cti < 45: pts = 3
        elif cti < 55: pts = 1
        else: pts = 0
        score += pts
        details.append(f"Cost/Income {cti}% → {pts}/7")
    
    # 3. ROE (5 pts)
    roe = fin.get('returnOnEquity')
    if roe is not None:
        if roe > 18: pts = 5
        elif roe > 14: pts = 4
        elif roe > 10: pts = 3
        elif roe > 5: pts = 1
        else: pts = 0
        score += pts
        details.append(f"ROE {roe}% → {pts}/5")
    
    # 4. Revenue Growth (5 pts)
    rg = fin.get('revenueGrowth')
    if rg is not None:
        if rg > 15: pts = 5
        elif rg > 8: pts = 4
        elif rg > 3: pts = 3
        elif rg >= 0: pts = 1
        else: pts = 0
        score += pts
        details.append(f"نمو الإيرادات {rg}% → {pts}/5")
    
    # 5. Net Profit Margin (6 pts) — بنوك سعودية عادة 40-70%
    pm = fin.get('profitMargins')
    if pm is not None:
        if pm > 50: pts = 6
        elif pm > 40: pts = 5
        elif pm > 30: pts = 3
        elif pm > 20: pts = 1
        else: pts = 0
        score += pts
        details.append(f"Net Profit Margin {pm}% → {pts}/6")
    
    return score, 30, details


def _score_generic_financial(fin, stock):
    """القواعد العامة — لكل القطاعات ما عدا البنوك (30 نقطة)
    نمو(6) + هامش(6) + ROE(6) + D/E(6) + CR(3) + OCF(3) = 30
    """
    cf = stock.get('cashflow', {})
    sector = stock.get('sector', '')
    score = 0
    details = []
    
    # Revenue Growth (6 pts)
    rg = fin.get('revenueGrowth')
    if rg is not None:
        if rg > 15: pts = 6
        elif rg > 8: pts = 5
        elif rg > 3: pts = 4
        elif rg >= 0: pts = 2
        else: pts = 0
        score += pts
        details.append(f"نمو الإيرادات {rg}% → {pts}/6")
    
    # Profit Margin (6 pts)
    pm = fin.get('profitMargins')
    if pm is not None:
        if pm > 20: pts = 6
        elif pm > 12: pts = 5
        elif pm > 5: pts = 3
        elif pm >= 0: pts = 1
        else: pts = 0
        score += pts
        details.append(f"هامش الربح {pm}% → {pts}/6")
    
    # ROE (6 pts)
    roe = fin.get('returnOnEquity')
    if roe is not None:
        if roe > 18: pts = 6
        elif roe > 12: pts = 5
        elif roe > 8: pts = 3
        elif roe >= 0: pts = 1
        else: pts = 0
        score += pts
        details.append(f"ROE {roe}% → {pts}/6")
    
    # D/E (6 pts)
    de = fin.get('debtToEquity')
    if de is not None:
        if de < 30: pts = 6
        elif de < 80: pts = 5
        elif de < 150: pts = 3
        elif de < 300: pts = 1
        else: pts = 0
        score += pts
        details.append(f"D/E {de}% → {pts}/6")
    
    # Current Ratio (3 pts)
    cr = fin.get('currentRatio')
    if cr is not None:
        if cr > 1.5: pts = 3
        elif cr >= 1.0: pts = 2
        elif cr >= 0.7: pts = 1
        else: pts = 0
        score += pts
        details.append(f"CR {cr} → {pts}/3")
    
    # OCF (3 pts)
    ocf = cf.get('ocf')
    ni = cf.get('netIncome')
    if ocf is not None and ocf != 0:
        if ocf > 0 and (ni is None or ni <= 0 or ocf > ni):
            pts = 3
        elif ocf > 0:
            pts = 2
        else:
            pts = 0
        score += pts
        details.append(f"OCF → {pts}/3")
    
    return score, 30, details


def score_weekly_trend(stock):
    """المحور 2: الاتجاه الفني الاستثماري (25 نقطة)"""
    wt = stock.get('weeklyTechnical', {})
    if not wt:
        return 0, 25, ["لا توجد بيانات أسبوعية"]
    
    price = wt.get('currentPrice', stock.get('currentPrice', 0))
    score = 0
    details = []
    
    # SMA 200W (8 pts)
    sma200 = wt.get('sma200w')
    slope = wt.get('sma200wSlope', 0)
    if sma200 and price:
        if price > sma200:
            if slope and slope > 1: pts = 8
            elif slope and slope > -1: pts = 6
            else: pts = 3
        else:
            dist = (price - sma200) / sma200 * 100
            if dist > -3: pts = 2
            else: pts = 0
        score += pts
        details.append(f"SMA200W {sma200} (slope {slope}%) → {pts}/8")
    
    # EMA 40W (7 pts)
    ema40 = wt.get('ema40w')
    if ema40 and sma200 and price:
        if price > ema40 and ema40 > sma200: pts = 7
        elif price > ema40: pts = 4
        elif price > sma200: pts = 2
        else: pts = 0
        score += pts
        details.append(f"EMA40W {ema40} → {pts}/7")
    
    # RSI 14W (5 pts)
    rsi = wt.get('rsi14w')
    if rsi is not None:
        if 55 <= rsi <= 70: pts = 5
        elif 50 <= rsi < 55: pts = 4
        elif 70 < rsi <= 80: pts = 3
        elif 40 <= rsi < 50: pts = 2
        else: pts = 1
        score += pts
        details.append(f"RSI-W {rsi} → {pts}/5")
    
    # MACD Weekly (5 pts)
    macd = wt.get('macdW')
    signal = wt.get('macdSignalW')
    if macd is not None and signal is not None:
        if macd > signal and macd > 0: pts = 5
        elif macd > signal and macd <= 0: pts = 4
        elif macd <= signal and macd > 0: pts = 2
        else: pts = 0
        score += pts
        details.append(f"MACD-W {macd} vs Signal {signal} → {pts}/5")
    
    return score, 25, details


def score_relative_strength(stock, sector_medians):
    """المحور 3: الزخم النسبي (15 نقطة)"""
    rs = stock.get('relativeStrength', {})
    if not rs:
        return 0, 15, ["لا توجد بيانات"]
    
    score = 0
    details = []
    
    # RS vs TASI 6M (4 pts)
    rs6m = rs.get('rsTasi6m', rs.get('rs6m'))
    if rs6m is not None:
        if rs6m > 10: pts = 4
        elif rs6m > 3: pts = 3
        elif rs6m > -3: pts = 2
        elif rs6m > -10: pts = 1
        else: pts = 0
        score += pts
        details.append(f"RS-TASI 6M: {rs6m:+.1f}% → {pts}/4")
    
    # RS vs TASI 12M (4 pts) — not available in current data, use return12m as proxy
    rs12m = rs.get('rsTasi12m', rs.get('rs12m'))
    if rs12m is not None:
        if rs12m > 10: pts = 4
        elif rs12m > 3: pts = 3
        elif rs12m > -3: pts = 2
        elif rs12m > -10: pts = 1
        else: pts = 0
        score += pts
        details.append(f"RS-TASI 12M: {rs12m:+.1f}% → {pts}/4")
    
    # RS vs Sector 6M (4 pts)
    sec = stock.get('sector')
    ret6m = rs.get('return6m', rs.get('ret6m'))
    if sec and ret6m is not None and sec in sector_medians:
        sec_ret = sector_medians[sec].get('ret6mMedian', 0)
        if sec_ret is not None:
            rs_sec = ret6m - sec_ret
            if rs_sec > 10: pts = 4
            elif rs_sec > 3: pts = 3
            elif rs_sec > -3: pts = 2
            elif rs_sec > -10: pts = 1
            else: pts = 0
            score += pts
            details.append(f"RS-Sector 6M: {rs_sec:+.1f}% → {pts}/4")
    
    # RS vs TASI 3M (3 pts)
    rs3m = rs.get('rsTasi3m', rs.get('rs3m'))
    if rs3m is not None:
        if rs3m > 5: pts = 3
        elif rs3m > 1: pts = 2
        elif rs3m > -5: pts = 1
        else: pts = 0
        score += pts
        details.append(f"RS-TASI 3M: {rs3m:+.1f}% → {pts}/3")
    
    return score, 15, details


def score_risk(stock, sma200w_zscores=None):
    """المحور 4: المخاطر (20 نقطة)
    ATR% (4) + 52W Distance (4) + Volume (4) + SMA200W Z-Score (3) + Net Debt/EBITDA (5)
    """
    de = stock.get('dailyExtra', {})
    if not de:
        return 0, 20, ["لا توجد بيانات"]
    
    price = stock.get('currentPrice', 0)
    score = 0
    details = []
    
    # ATR% (4 pts) — تقلب يومي
    atr_pct = de.get('atrPct')
    if atr_pct is not None:
        if atr_pct < 1.5: pts = 4
        elif atr_pct < 2.5: pts = 3
        elif atr_pct < 4: pts = 1
        else: pts = 0
        score += pts
        details.append(f"ATR% {atr_pct}% → {pts}/4")
    
    # Distance from 52W High (4 pts)
    h52 = de.get('high52w')
    if h52 and price and h52 > 0:
        dist = (h52 - price) / h52 * 100
        if dist < 5: pts = 4
        elif dist < 15: pts = 3
        elif dist < 25: pts = 1
        else: pts = 0
        score += pts
        details.append(f"البعد عن قمة 52أ {dist:.1f}% → {pts}/4")
    
    # Volume trend (4 pts)
    avg20 = de.get('avgVol20')
    avg50 = de.get('avgVol50')
    if avg20 and avg50 and avg50 > 0:
        ratio = avg20 / avg50
        if avg50 < 50000:
            pts = 1  # Low liquidity warning
        elif ratio > 1.2: pts = 4
        elif ratio > 0.8: pts = 3
        else: pts = 1
        score += pts
        details.append(f"Vol20/50: {ratio:.2f} → {pts}/4")
    
    # SMA200W Extension Z-Score (3 pts) — بُعد السعر عن المتوسط (علمي)
    sym = stock.get('symbol', '')
    if sma200w_zscores and sym in sma200w_zscores:
        zdata = sma200w_zscores[sym]
        z = zdata['z']
        dev = zdata['dev']
        # Z-Score: how many SDs from the stock's own historical mean deviation
        # |Z| < 1: normal range → 3 pts
        # |Z| 1-2: moderately extended → 2 pts  
        # |Z| 2-3: significantly extended → 1 pt
        # |Z| > 3: extremely extended → 0 pts
        abs_z = abs(z)
        if abs_z < 1: pts = 3
        elif abs_z < 2: pts = 2
        elif abs_z < 3: pts = 1
        else: pts = 0
        score += pts
        direction = "فوق" if dev > 0 else "تحت"
        details.append(f"SMA200W Z={z:+.1f} ({direction} بـ{abs(dev):.0f}%) → {pts}/3")
    
    # Net Debt/EBITDA (5 pts) — ملاءة مالية
    dh = stock.get('debtHealth', {})
    dh_type = dh.get('type', '')
    if dh_type == 'bank':
        # Banks: Cost-to-Income
        cti = dh.get('costToIncome')
        if cti is not None:
            if cti < 35: pts = 5
            elif cti < 40: pts = 4
            elif cti < 45: pts = 3
            elif cti < 55: pts = 1
            else: pts = 0
            score += pts
            details.append(f"C/I {cti}% (بنك) → {pts}/5")
    elif dh_type == 'company':
        nde = dh.get('netDebtToEbitda')
        net_debt = dh.get('netDebt')
        if nde is not None:
            if nde < 0:  # فوائض نقدية
                pts = 5
                details.append(f"فوائض نقدية (ND/EBITDA {nde}x) → {pts}/5")
            elif nde <= 1:
                pts = 4
                details.append(f"ND/EBITDA {nde}x (مريح) → {pts}/5")
            elif nde <= 2:
                pts = 3
                details.append(f"ND/EBITDA {nde}x (معقول) → {pts}/5")
            elif nde <= 3:
                pts = 1
                details.append(f"ND/EBITDA {nde}x (مرتفع) → {pts}/5")
            else:
                pts = 0
                details.append(f"ND/EBITDA {nde}x (خطر) → {pts}/5")
            score += pts
        elif net_debt is not None and net_debt < 0:
            pts = 5
            score += pts
            details.append(f"فوائض نقدية → {pts}/5")
    
    return score, 20, details


def score_valuation(stock, sector_medians):
    """المحور 5: التقييم / القيمة الحقيقية (15 نقطة)"""
    val = stock.get('valuation', {})
    sec = stock.get('sector')
    if not val:
        return 0, 15, ["لا توجد بيانات تقييم"]
    
    sm = sector_medians.get(sec, {}) if sec else {}
    score = 0
    details = []
    
    # P/E vs Sector (5 pts)
    pe = val.get('pe')
    pe_med = sm.get('peMedian')
    if pe and pe > 0 and pe_med and pe_med > 0:
        ratio = pe / pe_med
        if ratio < 0.7: pts = 5
        elif ratio < 0.9: pts = 4
        elif ratio < 1.1: pts = 3
        elif ratio < 1.5: pts = 1
        else: pts = 0
        score += pts
        details.append(f"P/E {pe:.1f} vs قطاع {pe_med:.1f} ({ratio:.2f}x) → {pts}/5")
    
    # P/B vs Sector (4 pts)
    pb = val.get('pb')
    pb_med = sm.get('pbMedian')
    if pb and pb > 0 and pb_med and pb_med > 0:
        ratio = pb / pb_med
        if ratio < 0.6: pts = 4
        elif ratio < 0.8: pts = 3
        elif ratio < 1.1: pts = 2
        elif ratio < 1.4: pts = 1
        else: pts = 0
        score += pts
        details.append(f"P/B {pb:.2f} vs قطاع {pb_med:.2f} ({ratio:.2f}x) → {pts}/4")
    
    # Dividend Yield (3 pts)
    dy = val.get('dividendYield')
    if dy and dy > 0:
        dy_pct = dy * 100
        if dy_pct > 4: pts = 3
        elif dy_pct > 2: pts = 2
        elif dy_pct > 0.5: pts = 1
        else: pts = 0
        score += pts
        details.append(f"Yield {dy_pct:.1f}% → {pts}/3")
    
    # EV/EBITDA (3 pts)
    ev = val.get('evEbitda')
    if ev and ev > 0:
        if ev < 8: pts = 3
        elif ev < 12: pts = 2
        elif ev < 18: pts = 1
        else: pts = 0
        score += pts
        details.append(f"EV/EBITDA {ev:.1f} → {pts}/3")
    else:
        # No EV/EBITDA → neutral
        score += 1
        details.append(f"EV/EBITDA غير متوفر → 1/3")
    
    return score, 15, details



def build_top_drivers(s, sector_medians):
    """البند 5: أبرز المحركات من البيانات الحية — بدل النسخ البائد"""
    pos, neg = [], []
    fin = s.get('financials', {}) or {}
    price = s.get('currentPrice')
    # مالية
    roe = fin.get('returnOnEquity')
    if roe is not None and roe >= 18: pos.append(f"ROE قوي {roe}%")
    roa = fin.get('returnOnAssets')
    if roa is not None and roa >= 1.5: pos.append(f"ROA {roa}%")
    pm = fin.get('profitMargins')
    if pm is not None and pm >= 20: pos.append(f"هامش ربح {pm}%")
    rg = fin.get('revenueGrowth')
    if rg is not None and rg >= 15: pos.append(f"نمو إيرادات {rg}%")
    # اتجاه
    wt = s.get('weeklyTechnical', {}) or {}
    sma = wt.get('sma200w')
    if price and sma:
        (pos if price > sma else neg).append("فوق SMA200W" if price > sma else "تحت SMA200W")
    # زخم نسبي
    rs6 = (s.get('relativeStrength', {}) or {}).get('rsTasi6m')
    if rs6 is not None:
        if rs6 > 10: pos.append(f"يتفوق على TASI {rs6:+.0f}% (6م)")
        elif rs6 < -10: neg.append(f"أضعف من TASI {rs6:+.0f}% (6م)")
    # تقييم نسبي
    v = s.get('valuation', {}) or {}
    sm = sector_medians.get(s.get('sector', ''), {}) or {}
    pe, pem = v.get('pe'), sm.get('peMedian')
    if pe and pem and pe > 0:
        r = pe / pem
        if r < 0.7: pos.append("أرخص من قطاعه (P/E)")
        elif r > 1.3: neg.append("أغلى من قطاعه (P/E)")
    # مخاطر
    nde = (s.get('debtHealth', {}) or {}).get('netDebtToEbitda')
    if nde is not None and nde > 3: neg.append(f"دين مرتفع ND/EBITDA {nde}")
    atr = (s.get('dailyExtra', {}) or {}).get('atrPct')
    if atr is not None and atr > 4: neg.append(f"تذبذب مرتفع ATR {atr}%")
    # تركيب: حتى محرّكين إيجابيين + سلبي واحد إن وجد (سقف 3)
    out = [{'text': t, 'type': 'positive'} for t in pos[:2]]
    if neg: out.append({'text': neg[0], 'type': 'negative'})
    elif len(pos) > 2: out.append({'text': pos[2], 'type': 'positive'})
    return out

def timing_signal(stock):
    """الطبقة 3: توقيت الدخول"""
    de = stock.get('dailyExtra', {})
    tech = stock.get('technical', {})
    price = stock.get('currentPrice', 0)
    
    positives = 0
    total = 0
    details = []
    
    # EMA 50D
    ema50 = de.get('ema50d')
    if ema50 and price:
        total += 1
        if price > ema50:
            positives += 1
            details.append("✅ فوق EMA50D")
        else:
            details.append("⚠️ تحت EMA50D")
    
    # RSI 14D
    rsi = de.get('rsi14d')
    if rsi is not None:
        total += 1
        if 40 <= rsi <= 65:
            positives += 1
            details.append(f"✅ RSI-D {rsi}")
        else:
            details.append(f"⚠️ RSI-D {rsi}")
    
    # MACD Daily
    macd = tech.get('macd')
    signal = tech.get('macdSignal')
    if macd is not None and signal is not None:
        total += 1
        if macd > signal:
            positives += 1
            details.append("✅ MACD-D إيجابي")
        else:
            details.append("⚠️ MACD-D سلبي")
    
    # Volume
    avg20 = de.get('avgVol20')
    avg50 = de.get('avgVol50')
    if avg20 and avg50 and avg50 > 0:
        total += 1
        if avg20 > avg50:
            positives += 1
            details.append("✅ حجم متزايد")
        else:
            details.append("⚠️ حجم متراجع")
    
    if total == 0:
        return "محايد", "🟡", details
    
    if positives >= 3:
        return "ممتاز", "🟢", details
    elif positives >= 2:
        return "مقبول", "🟡", details
    else:
        return "انتظر", "🔴", details


def investment_filter(stock):
    """الطبقة 1: الفلتر الاستثماري"""
    wt = stock.get('weeklyTechnical', {})
    de = stock.get('dailyExtra', {})
    fin = stock.get('financials', {})
    price = wt.get('currentPrice', stock.get('currentPrice', 0))
    
    # Check: has financial data?
    if not fin:
        return False, "لا توجد بيانات مالية"
    
    # Check: SMA 200W filter
    sma200 = wt.get('sma200w')
    if sma200 and price:
        if price < sma200:
            # Check exception: reversal signals
            ema40 = wt.get('ema40w')
            rsi = wt.get('rsi14w')
            macd = wt.get('macdW')
            signal = wt.get('macdSignalW')
            
            if (ema40 and price > ema40 and 
                rsi and rsi > 50 and 
                macd is not None and signal is not None and macd > signal):
                return True, "تحت SMA200W لكن إشارات انعكاس"
            else:
                return False, "تحت SMA200W بدون إشارات انعكاس"
    
    return True, "عدّى الفلتر"


def classify(total_score, timing_label):
    """التصنيف النهائي"""
    if total_score >= 80:
        if timing_label == "ممتاز":
            return "شراء قوي", "⭐⭐⭐", "strong_buy"
        elif timing_label == "مقبول":
            return "شراء", "⭐⭐", "buy"
        else:
            return "شراء — انتظر توقيت", "⭐⭐", "buy_wait"
    elif total_score >= 65:
        if timing_label == "ممتاز":
            return "شراء", "⭐⭐", "buy"
        elif timing_label == "مقبول":
            return "شراء مشروط", "⭐", "conditional_buy"
        else:
            return "انتظار", "⏳", "hold"
    elif total_score >= 50:
        return "انتظار", "⏳", "hold"
    elif total_score >= 35:
        return "بيع", "🔻", "sell"
    else:
        return "بيع قوي", "🔻🔻", "strong_sell"


def run_scoring():
    with open('/srv/ideas/stocks-data.json') as f:
        data = json.load(f)
    
    # Load SMA200W Z-scores
    import os
    zscores_path = '/srv/ideas/sma200w-zscores.json'
    sma200w_zscores = {}
    if os.path.exists(zscores_path):
        with open(zscores_path) as f:
            sma200w_zscores = json.load(f)
    
    sector_medians = data.get('sectorMedians', {})
    stats = {'strong_buy': 0, 'buy': 0, 'buy_wait': 0, 'conditional_buy': 0, 'hold': 0, 'sell': 0, 'strong_sell': 0, 'filtered': 0}
    
    for s in data['stocks']:
        # Filter
        passed, filter_reason = investment_filter(s)
        
        if not passed:
            old_sc = s.get('investmentScore', {})
            s['investmentScore'] = {
                'total': 0,
                'filtered': True, 'filterReason': filter_reason,
                'classification': 'انتظار', 'classCode': 'filtered',
                'timing': 'N/A',
                # Preserve old fields
                'confidence': old_sc.get('confidence', ''),
                'confidenceCode': old_sc.get('confidenceCode', ''),
                'confidencePct': old_sc.get('confidencePct', 0),
                'interpretation': old_sc.get('interpretation', ''),
                'execInterpretation': old_sc.get('execInterpretation', ''),
                'topDrivers': build_top_drivers(s, sector_medians),
                'riskScore': old_sc.get('riskScore', 0),
                'riskLevel': old_sc.get('riskLevel', ''),
                'riskLevelCode': old_sc.get('riskLevelCode', ''),
                'riskReasons': compute_risk_reasons(s),
            }
            stats['filtered'] += 1
            continue
        
        # Score all 5 axes
        fin_score, fin_max, fin_detail = score_financial_health(s)
        trend_score, trend_max, trend_detail = score_weekly_trend(s)
        rs_score, rs_max, rs_detail = score_relative_strength(s, sector_medians)
        risk_score, risk_max, risk_detail = score_risk(s, sma200w_zscores)
        val_score, val_max, val_detail = score_valuation(s, sector_medians)
        
        raw_total = fin_score + trend_score + rs_score + risk_score + val_score
        max_total = fin_max + trend_max + rs_max + risk_max + val_max
        # Normalize to 100 scale
        total = round((raw_total / max_total) * 100) if max_total > 0 else 0
        
        # Timing
        timing_label, timing_icon, timing_detail = timing_signal(s)
        
        # Classification
        class_text, class_icon, class_code = classify(total, timing_label)
        
        # Preserve existing fields not computed here (confidence, interpretation, etc.)
        old_sc = s.get('investmentScore', {})
        
        # Count timing signals
        timing_positive = sum(1 for d in timing_detail if d.startswith('✅'))
        timing_total = len(timing_detail)
        
        s['investmentScore'] = {
            'total': total,
            'financial': fin_score,
            'trend': trend_score,
            'relativeStrength': rs_score,
            'risk': risk_score,
            'valuation': val_score,
            'timing': timing_label,
            'timingSignals': timing_positive,
            'classification': class_text,
            'classCode': class_code,
            'sector': s.get('sector', ''),
            'industry': s.get('industry', ''),
            'filtered': False,
            'filterReason': filter_reason,
            # Preserve fields from previous scoring runs
            'confidence': old_sc.get('confidence', ''),
            'confidenceCode': old_sc.get('confidenceCode', ''),
            'confidencePct': old_sc.get('confidencePct', 0),
            'interpretation': old_sc.get('interpretation', ''),
            'execInterpretation': old_sc.get('execInterpretation', ''),
            'topDrivers': build_top_drivers(s, sector_medians),
            'details': {
                'financial': fin_detail,
                'trend': trend_detail,
                'relativeStrength': rs_detail,
                'risk': risk_detail,
                'valuation': val_detail,
                'timing': timing_detail,
            },
            'riskScore': old_sc.get('riskScore', 0),
            'riskLevel': old_sc.get('riskLevel', ''),
            'riskLevelCode': old_sc.get('riskLevelCode', ''),
            'riskReasons': compute_risk_reasons(s),
            'sectorRank': old_sc.get('sectorRank', 0),
            'sectorTotal': old_sc.get('sectorTotal', 0),
            'sectorPercentile': old_sc.get('sectorPercentile', 0),
            'sectorAvgScore': old_sc.get('sectorAvgScore', 0),
            'sectorAvgRisk': old_sc.get('sectorAvgRisk', 0),
        }
        
        stats[class_code] = stats.get(class_code, 0) + 1
    
    with open('/srv/ideas/stocks-data.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("=" * 50)
    print("📊 سيف تداول — نتائج التقييم الاستثماري")
    print("=" * 50)
    print(f"⭐⭐⭐ شراء قوي: {stats.get('strong_buy', 0)}")
    print(f"⭐⭐ شراء: {stats.get('buy', 0)}")
    print(f"⭐⭐ شراء (انتظر توقيت): {stats.get('buy_wait', 0)}")
    print(f"⭐ شراء مشروط: {stats.get('conditional_buy', 0)}")
    print(f"⏳ انتظار: {stats.get('hold', 0)}")
    print(f"🔻 بيع: {stats.get('sell', 0)}")
    print(f"🔻🔻 بيع قوي: {stats.get('strong_sell', 0)}")
    print(f"⛔ لم يعدّ الفلتر: {stats.get('filtered', 0)}")
    print()
    
    # Top 10
    scored = [s for s in data['stocks'] if not s.get('investmentScore', {}).get('filtered')]
    scored.sort(key=lambda x: x['investmentScore']['total'], reverse=True)
    print("🏆 أعلى 10 أسهم:")
    for s in scored[:10]:
        sc = s['investmentScore']
        print(f"  {s['name']} ({s['symbol']}): {sc['total']}/100 — {sc['classification']}")
    
    print(f"\n🔻 أدنى 5:")
    for s in scored[-5:]:
        sc = s['investmentScore']
        print(f"  {s['name']} ({s['symbol']}): {sc['total']}/100 — {sc['classification']}")


if __name__ == '__main__':
    run_scoring()
