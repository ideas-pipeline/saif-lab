#!/bin/bash
# المرحلة الأولى: جلب بيانات تحليل فني + أخبار + توزيعات لكل سهم
# يضيف: technical{}, news[], dividends{}, alerts[] لكل سهم في stocks-data.json
# Usage: bash fetch-stock-analysis.sh [--quick] (quick = أول 10 أسهم فقط للاختبار)

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/stocks-data.json"
QUICK="${1:-}"

echo "🔄 المرحلة الأولى: جلب التحليل الفني + الأخبار..."
echo "$(date '+%Y-%m-%d %H:%M:%S')"

python3 << 'PYTHON'
import json, urllib.request, urllib.parse, time, sys, math
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET

QUICK = "--quick" in sys.argv or "QUICK" in open("/dev/stdin", "r").read() if False else False

with open('/srv/ideas/stocks-data.json') as f:
    data = json.load(f)

stocks = data['stocks']
quick_mode = len(sys.argv) > 1 and sys.argv[1] == '--quick'
if quick_mode:
    stocks = stocks[:10]
    print("⚡ وضع سريع — 10 أسهم فقط")

# === HELPER FUNCTIONS ===

def calc_ema(prices, period):
    """Exponential Moving Average"""
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 2)

def calc_rsi(prices, period=14):
    """Relative Strength Index"""
    if len(prices) < period + 1:
        return None
    gains = []
    losses = []
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

def calc_macd(prices):
    """MACD (12, 26, 9)"""
    if len(prices) < 26:
        return None, None, None
    ema12 = calc_ema(prices, 12)
    ema26 = calc_ema(prices, 26)
    if ema12 is None or ema26 is None:
        return None, None, None
    macd_line = round(ema12 - ema26, 2)
    # Signal line = EMA9 of MACD values (simplified)
    signal = round(macd_line * 0.8, 2)  # approximation
    histogram = round(macd_line - signal, 2)
    return macd_line, signal, histogram

def calc_support_resistance(prices):
    """Simple support/resistance from recent lows/highs"""
    if len(prices) < 20:
        return None, None
    recent = prices[-20:]
    support = round(min(recent), 2)
    resistance = round(max(recent), 2)
    return support, resistance

def get_recommendation(rsi, macd, price, ma20, ma50, health):
    """Generate buy/sell/hold recommendation"""
    score = 0
    reasons = []
    
    # RSI
    if rsi is not None:
        if rsi < 30:
            score += 2
            reasons.append("RSI منخفض (تشبع بيعي)")
        elif rsi < 40:
            score += 1
            reasons.append("RSI قريب من التشبع البيعي")
        elif rsi > 70:
            score -= 2
            reasons.append("RSI مرتفع (تشبع شرائي)")
        elif rsi > 60:
            score -= 1
            reasons.append("RSI قريب من التشبع الشرائي")
    
    # MACD
    if macd is not None:
        if macd > 0:
            score += 1
            reasons.append("MACD إيجابي")
        else:
            score -= 1
            reasons.append("MACD سلبي")
    
    # Price vs MA
    if ma20 is not None and price is not None:
        if price > ma20:
            score += 1
            reasons.append("السعر فوق MA20")
        else:
            score -= 1
            reasons.append("السعر تحت MA20")
    
    # Trend (MA20 vs MA50)
    if ma20 is not None and ma50 is not None:
        if ma20 > ma50:
            score += 1
            reasons.append("اتجاه صاعد (MA20 > MA50)")
        else:
            score -= 1
            reasons.append("اتجاه هابط (MA20 < MA50)")
    
    # Health
    if health == 'green':
        score += 1
        reasons.append("صحة مالية قوية")
    elif health == 'red':
        score -= 1
        reasons.append("صحة مالية ضعيفة")
    
    if score >= 3:
        return "شراء قوي", "strong_buy", reasons
    elif score >= 1:
        return "شراء", "buy", reasons
    elif score <= -3:
        return "بيع قوي", "strong_sell", reasons
    elif score <= -1:
        return "بيع", "sell", reasons
    else:
        return "انتظار", "hold", reasons

def generate_alerts(stock, technical):
    """Generate alert flags for a stock"""
    alerts = []
    
    rsi = technical.get('rsi')
    macd = technical.get('macd')
    daily_change = stock.get('dailyChange', 0)
    
    # RSI alerts
    if rsi is not None:
        if rsi > 70:
            alerts.append({"type": "overbought", "icon": "🔴", "text": f"تشبع شرائي (RSI {rsi})"})
        elif rsi < 30:
            alerts.append({"type": "oversold", "icon": "🟢", "text": f"تشبع بيعي (RSI {rsi})"})
    
    # Big daily move
    if abs(daily_change) > 3:
        icon = "📈" if daily_change > 0 else "📉"
        alerts.append({"type": "big_move", "icon": icon, "text": f"تحرك كبير ({daily_change:+.1f}%)"})
    
    # MACD crossover (simplified)
    if macd is not None and abs(macd) < 0.5:
        alerts.append({"type": "macd_cross", "icon": "⚡", "text": "MACD قرب خط الصفر"})
    
    # Price near support
    support = technical.get('support')
    current = stock.get('currentPrice')
    if support and current and current > 0:
        diff_pct = ((current - support) / current) * 100
        if diff_pct < 3:
            alerts.append({"type": "near_support", "icon": "🛡️", "text": f"قريب من الدعم ({support})"})
    
    # Covid bottom
    covid_low = stock.get('covidLow')
    if covid_low and current and covid_low > 0:
        diff = ((current - covid_low) / covid_low) * 100
        if diff < 0:
            alerts.append({"type": "below_covid", "icon": "💀", "text": f"تحت قاع كوفيد ({diff:.1f}%)"})
    
    return alerts

def fetch_news(stock_name, symbol):
    """Fetch latest news from Google News"""
    try:
        query = f"{stock_name} سهم"
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ar&gl=SA&ceid=SA:ar"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=8)
        root = ET.fromstring(resp.read())
        
        items = root.findall('.//item')[:3]
        news = []
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ''
            date = item.find('pubDate').text if item.find('pubDate') is not None else ''
            link = item.find('link').text if item.find('link') is not None else ''
            source = item.find('source').text if item.find('source') is not None else ''
            news.append({
                "title": title[:100],
                "date": date,
                "source": source,
                "url": link
            })
        return news
    except:
        return []

def fetch_dividends(symbol):
    """Fetch dividend info from Yahoo Finance"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.SR?interval=1mo&range=2y&events=div"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = json.load(urllib.request.urlopen(req, timeout=8))
        result = resp['chart']['result'][0]
        
        events = result.get('events', {})
        divs = events.get('dividends', {})
        
        if not divs:
            return {"hasDividends": False, "history": []}
        
        history = []
        for ts, div_data in sorted(divs.items(), key=lambda x: int(x[0]), reverse=True)[:5]:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            history.append({
                "date": dt.strftime('%Y-%m-%d'),
                "amount": round(div_data.get('amount', 0), 2)
            })
        
        return {
            "hasDividends": True,
            "history": history,
            "lastAmount": history[0]["amount"] if history else 0,
            "lastDate": history[0]["date"] if history else ""
        }
    except:
        return {"hasDividends": False, "history": []}

# === MAIN LOOP ===
updated = 0
errors = 0
total = len(stocks)

for i, stock in enumerate(stocks):
    sym = stock.get('symbol')
    if not sym:
        continue
    
    print(f"  [{i+1}/{total}] {stock['name']} ({sym})...", end=" ", flush=True)
    
    try:
        # 1. Fetch 3-month historical data
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.SR?interval=1d&range=3mo"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = json.load(urllib.request.urlopen(req, timeout=8))
        result = resp['chart']['result'][0]
        
        closes = result['indicators']['adjclose'][0]['adjclose']
        timestamps = result['timestamp']
        prices = [round(c, 2) for c in closes if c is not None]
        
        if len(prices) < 14:
            print("⚠️ بيانات قليلة")
            errors += 1
            continue
        
        current = prices[-1]
        
        # 2. Calculate technical indicators
        rsi = calc_rsi(prices)
        ma20 = round(sum(prices[-20:]) / min(20, len(prices)), 2) if len(prices) >= 20 else None
        ma50 = round(sum(prices[-50:]) / min(50, len(prices)), 2) if len(prices) >= 50 else None
        macd_line, macd_signal, macd_hist = calc_macd(prices)
        support, resistance = calc_support_resistance(prices)
        
        # Trend
        if ma20 and ma50:
            trend = "صاعد" if ma20 > ma50 else "هابط"
        elif ma20:
            trend = "صاعد" if current > ma20 else "هابط"
        else:
            trend = "غير محدد"
        
        # Recommendation
        rec_text, rec_code, rec_reasons = get_recommendation(
            rsi, macd_line, current, ma20, ma50, stock.get('health')
        )
        
        # Historical prices for chart (last 30 days)
        chart_prices = prices[-30:]
        
        technical = {
            "rsi": rsi,
            "ma20": ma20,
            "ma50": ma50,
            "macd": macd_line,
            "macdSignal": macd_signal,
            "macdHist": macd_hist,
            "support": support,
            "resistance": resistance,
            "trend": trend,
            "recommendation": rec_code,
            "recommendationText": rec_text,
            "reasons": rec_reasons[:4],
            "chartPrices": chart_prices,
            "updatedAt": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        stock['technical'] = technical
        
        # 3. Generate alerts
        alerts = generate_alerts(stock, technical)
        stock['alerts'] = alerts
        
        # 4. Fetch news (every 5th stock to avoid rate limits, or all in quick mode)
        if i % 5 == 0 or quick_mode or alerts:
            news = fetch_news(stock['name'], sym)
            if news:
                stock['news'] = news
            time.sleep(0.2)
        
        # 5. Fetch dividends (every 10th stock to avoid rate limits)
        if i % 10 == 0 or quick_mode:
            dividends = fetch_dividends(sym)
            if dividends.get('hasDividends'):
                stock['dividends'] = dividends
            time.sleep(0.2)
        
        status = "✅"
        if alerts:
            status += f" ⚠️{len(alerts)}"
        print(status)
        updated += 1
        
    except Exception as e:
        print(f"❌ {str(e)[:40]}")
        errors += 1
    
    time.sleep(0.3)

# Save
data['analysisUpdated'] = datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d %H:%M الرياض')

with open('/srv/ideas/stocks-data.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Summary
alerts_total = sum(len(s.get('alerts', [])) for s in data['stocks'])
news_total = sum(1 for s in data['stocks'] if s.get('news'))
div_total = sum(1 for s in data['stocks'] if s.get('dividends', {}).get('hasDividends'))

print(f"\n{'='*50}")
print(f"✅ تم تحديث {updated}/{total} سهم")
print(f"❌ أخطاء: {errors}")
print(f"⚠️ إجمالي التنبيهات: {alerts_total}")
print(f"📰 أسهم بأخبار: {news_total}")
print(f"💰 أسهم بتوزيعات: {div_total}")
print(f"📅 {data['analysisUpdated']}")
PYTHON
