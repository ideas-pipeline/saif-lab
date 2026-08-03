#!/bin/bash
# Update financial ratios from StockAnalysis.com (S&P Global data)
# Run weekly — القوائم المالية تتغير كل ربع فقط
# Usage: bash update-financials.sh

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/stocks-data.json"

python3 << 'PYTHON'
import json, urllib.request, re, time
from datetime import datetime, timezone, timedelta

with open('/srv/ideas/stocks-data.json') as f:
    data = json.load(f)

def fetch_page(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=12)
        return resp.read().decode('utf-8')
    except:
        return None

def extract_val(html, pattern):
    """استخرج أول رقم بعد label معين"""
    match = re.search(pattern, html, re.DOTALL)
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    return None

skip_symbols = {'2315', '4035', '5113', '5114'}

updated = 0
errors = 0
skipped = 0
total = len(data['stocks'])

print(f"📊 تحديث القوائم المالية لـ {total} سهم من StockAnalysis (S&P Global)...")

for i, stock in enumerate(data['stocks']):
    sym = stock.get('symbol', '')
    
    if sym in skip_symbols:
        skipped += 1
        continue
    
    # 1. صفحة Ratios
    ratios_html = fetch_page(f"https://stockanalysis.com/quote/tadawul/{sym}/financials/ratios/")
    if not ratios_html:
        errors += 1
        continue
    
    new_fin = {}
    
    cr = extract_val(ratios_html, r'Current Ratio.*?>([\-\d\.]+)')
    if cr is not None:
        new_fin['currentRatio'] = round(cr, 2)
    
    de = extract_val(ratios_html, r'Debt / Equity Ratio.*?>([\-\d\.]+)')
    if de is not None:
        new_fin['debtToEquity'] = round(de * 100, 2)  # تحويل من ratio لنسبة مئوية
    
    roe = extract_val(ratios_html, r'Return on Equity \(ROE\).*?>([\-\d\.]+)')
    if roe is not None:
        new_fin['returnOnEquity'] = round(roe, 1)
    
    # 2. صفحة Financials (income)
    income_html = fetch_page(f"https://stockanalysis.com/quote/tadawul/{sym}/financials/")
    
    if income_html:
        # Profit Margin (للشركات العادية)
        pm = extract_val(income_html, r'>Profit Margin<.*?>([\-\d\.]+)%')
        if pm is not None:
            new_fin['profitMargins'] = round(pm, 1)
        
        # Revenue Growth
        rg = extract_val(income_html, r'>Revenue Growth<.*?>([\-\d\.]+)%')
        # البنوك عندها Revenue Growth (YoY) بدل Revenue Growth
        if rg is None:
            rg = extract_val(income_html, r'Revenue Growth \(YoY\).*?>([\-\d\.]+)')
        if rg is not None:
            new_fin['revenueGrowth'] = round(rg, 1)
        
        # للبنوك: لو ما فيه Profit Margin → نحسبه من Net Income / Revenue
        if 'profitMargins' not in new_fin:
            ni = extract_val(income_html, r'Net Income\n\n([\-\d\.,]+)')
            rev = extract_val(income_html, r'Revenue\].*?\n\n([\-\d\.,]+)')
            # نجرب بطريقة ثانية: Net Income Growth كبديل
            nig = extract_val(income_html, r'Net Income Growth.*?>([\-\d\.]+)')
            # البنوك: نستخدم EPS Growth كمؤشر بديل للربحية
    
    # تحديث البيانات
    if new_fin:
        if 'financials' not in stock:
            stock['financials'] = {}
        
        stock['financials'].update(new_fin)
        
        # إعادة حساب health
        f = stock['financials']
        score = 0
        count = 0
        
        cr = f.get('currentRatio')
        if cr is not None:
            count += 1
            if cr > 1.5: score += 1
            elif cr >= 1: score += 0.5
        
        dte = f.get('debtToEquity')
        if dte is not None:
            count += 1
            if dte < 50: score += 1
            elif dte <= 150: score += 0.5
        
        pm = f.get('profitMargins')
        if pm is not None:
            count += 1
            if pm > 10: score += 1
            elif pm >= 0: score += 0.5
        
        roe_val = f.get('returnOnEquity')
        if roe_val is not None:
            count += 1
            if roe_val > 10: score += 1
            elif roe_val >= 0: score += 0.5
        
        rg = f.get('revenueGrowth')
        if rg is not None:
            count += 1
            if rg > 5: score += 1
            elif rg >= 0: score += 0.5
        
        if count > 0:
            pct = score / count * 100
            stock['health'] = 'green' if pct > 70 else ('yellow' if pct >= 40 else 'red')
        
        stock['financialsSource'] = 'S&P Global via StockAnalysis'
        stock['financialsUpdated'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        updated += 1
    else:
        errors += 1
    
    if (i+1) % 50 == 0:
        print(f"  ... {i+1}/{total} ({updated} ✅ | {errors} ❌)")
    
    time.sleep(0.5)

# حفظ
with open('/srv/ideas/stocks-data.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n{'='*50}")
print(f"✅ تم تحديث: {updated} سهم")
print(f"❌ أخطاء: {errors}")
print(f"⏭️ تم تخطي: {skipped}")
print(f"📊 المصدر: S&P Global Market Intelligence via StockAnalysis.com")
PYTHON

# Push to GitHub Pages
echo ""
echo "📤 جاري النشر..."
# (إصلاح بند 6) أُزيل النشر الأوسط — النشر الوحيد نهاية run-stocks-daily.sh
