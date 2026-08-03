#!/bin/bash
# update-watchlist-accuracy.sh — v2 (بند 7: حل التقسيمات، 2026-07-14)
# ---
# المصدر الوحيد للتحكم: /srv/ideas/watchlist-config.json
# الجديد: entryPrice يُشتق ديناميكياً كل تشغيلة من adjclose ليوم الدخول (Yahoo)
#   → ذاتي الشفاء بعد أي تقسيم أسهم. adjclose يعدّل للتوزيعات أيضاً
#   → العائد المعروض شبه كلي (موثق في /srv/ideas/accuracy-criteria.md قسم 4)
# سلسلة التراجع عند فشل الجلب: cache سابق → الرقم اليدوي من config (مع وسم)
# للتراجع الكامل: archive/update-watchlist-accuracy.sh.pre-item7-2026-07-14

CONFIG_JSON="${CONFIG_JSON:-/srv/ideas/watchlist-config.json}"
STOCKS_JSON="${STOCKS_JSON:-/srv/ideas/stocks-data.json}"
HTML_FILE="${HTML_FILE:-/srv/ideas/stocks-site/watchlist-accuracy.html}"
CACHE_FILE="${CACHE_FILE:-/srv/ideas/.entry-adjclose-cache.json}"

export CONFIG_JSON STOCKS_JSON HTML_FILE CACHE_FILE

python3 << 'PYEOF'
import json, re, os, time, urllib.request
from datetime import datetime, timedelta

CONFIG_JSON = os.environ["CONFIG_JSON"]
STOCKS_JSON = os.environ["STOCKS_JSON"]
HTML_FILE   = os.environ["HTML_FILE"]
CACHE_FILE  = os.environ["CACHE_FILE"]

# ── 0) جلب الإغلاق المعدل ليوم الدخول (أول يوم تداول >= التاريخ) ──
def fetch_adjclose(symbol, entry_date):
    ysym = symbol + ".SR" if len(symbol) == 4 and symbol.isdigit() else symbol
    t0 = int(datetime.strptime(entry_date, "%Y-%m-%d").timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}"
           f"?period1={t0 - 86400}&period2={t0 + 86400 * 10}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(2):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=20))
            res = r["chart"]["result"][0]
            ts  = res["timestamp"]
            adj = res["indicators"]["adjclose"][0]["adjclose"]
            for t, a in zip(ts, adj):
                if a is None:
                    continue
                day = datetime.fromtimestamp(t).strftime("%Y-%m-%d")
                if day >= entry_date:
                    return round(a, 2), day
            return None, None
        except Exception:
            if attempt == 0:
                time.sleep(2)
    return None, None

SAHMK_KEY = open("/srv/ideas/.sahmk.key").read().strip()
SAHMK_H = {"X-API-Key": SAHMK_KEY, "User-Agent": "Mozilla/5.0"}

def fetch_sahmk_entry_close(symbol, entry_date):
    # tr-v2: اغلاق يوم الدخول من سهمك (معدل للتقسيمات عند المصدر) - نافذة 12 يوما
    end = (datetime.strptime(entry_date, "%Y-%m-%d") + timedelta(days=12)).strftime("%Y-%m-%d")
    url = f"https://app.sahmk.sa/api/v1/historical/{symbol}/?from={entry_date}&to={end}"
    for attempt in range(2):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=SAHMK_H), timeout=20))
            rows = r if isinstance(r, list) else r.get("data", [])
            for row in sorted(rows, key=lambda x: x.get("date", "")):
                if row.get("date", "") >= entry_date and row.get("close"):
                    return round(row["close"], 2), row["date"]
            return None, None
        except Exception:
            if attempt == 0:
                time.sleep(2)
    return None, None

def fetch_sahmk_divs_since(symbol, entry_date, until):
    # tr-v2: مجموع التوزيعات النقدية التي تاريخ احقيتها بين الدخول واليوم
    url = f"https://app.sahmk.sa/api/v1/dividends/{symbol}/?limit=50"
    for attempt in range(2):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=SAHMK_H), timeout=20))
            tot = 0.0
            for h in r.get("history", []):
                ed = h.get("eligibility_date") or ""
                if ed and entry_date <= ed <= until and h.get("value"):
                    tot += h["value"]
            return round(tot, 3)
        except Exception:
            if attempt == 0:
                time.sleep(2)
    return None

# ── 1) قراءة config + الأسعار + الـ cache ──
with open(CONFIG_JSON) as f:
    config = json.load(f)
stocks_config = config.get("stocks", [])

with open(STOCKS_JSON) as f:
    data = json.load(f)
price_map = {s["symbol"]: s.get("currentPrice") for s in data.get("stocks", [])}

cache = {}
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
    except Exception:
        cache = {}

today   = datetime.now().strftime("%Y-%m-%d")
now_iso = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
now_iso = now_iso[:-2] + ":" + now_iso[-2:]

# ── 2) بناء كتلة WATCHLIST ──
lines = ["const WATCHLIST = ["]
stats = {"sahmk-close": 0, "adjclose": 0, "cache": 0, "manual-fallback": 0, "same-day-close": 0}
for s in stocks_config:
    symbol      = s["symbol"]
    display_sym = symbol + ".SR" if len(symbol) == 4 and symbol.isdigit() else symbol
    name        = s["name"]
    sector      = s.get("sector", "")
    stype       = s.get("type", "buy")
    manual      = s["entryPrice"]
    entry_date  = s.get("entryDate", config.get("entryDate", ""))
    track       = s.get("track", "")
    category    = s.get("category", "")
    current     = price_map.get(symbol)
    status      = s.get("status", "open")
    close_date  = s.get("closeDate", "")
    close_price = s.get("closePrice")
    close_reason = s.get("closeReason", "")
    div_until   = close_date if (status == "closed" and close_date) else today

    entry_price, source, divs = manual, "manual-fallback", 0
    if entry_date == today and current is not None:
        # مدخل اليوم: adjclose اليوم = إغلاق اليوم — لا حاجة لـ Yahoo (توصية الوكيل 3)
        entry_price, source = current, "same-day-close"
    elif entry_date:
        key = f"{symbol}|{entry_date}"
        skey = "S|" + key
        _c = cache.get(skey)
        sc = _c.get("close") if isinstance(_c, dict) else None
        if sc is None:
            sc, sday = fetch_sahmk_entry_close(symbol, entry_date)
            time.sleep(0.4)
            if sc is not None:
                cache[skey] = {"close": sc, "tradingDay": sday, "fetchedAt": today}
        if sc is not None:
            d = fetch_sahmk_divs_since(symbol, entry_date, div_until)
            time.sleep(0.4)
            entry_price, source = sc, "sahmk-close"
            divs = d if d is not None else 0
    if source == "manual-fallback" and entry_date and entry_date != today:
        adj, adj_day = fetch_adjclose(symbol, entry_date)
        time.sleep(0.5)
        if adj is not None:
            entry_price, source = adj, "adjclose"
            cache[key] = {"adj": adj, "tradingDay": adj_day, "fetchedAt": today}
        elif key in cache:
            entry_price, source = cache[key]["adj"], "cache"
    stats[source] += 1

    mark = {"sahmk-close": "🟢", "adjclose": "✅", "cache": "🔁", "manual-fallback": "⚠️", "same-day-close": "🆕"}[source]
    print(f"  {mark} {symbol} entry: {entry_price} ({source}, يدوي: {manual})")

    if current is not None:
        price_str = f"{current},           // ✅ confirmed {today}"
    else:
        price_str = "null,              // ⚠️ not found in stocks-data.json"
        print(f"  ⚠️  {symbol} → currentPrice not found")

    lines.append("  {")
    lines.append(f'    symbol:        "{display_sym}",')
    lines.append(f'    name:          "{name}",')
    lines.append(f'    sector:        "{sector}",')
    lines.append(f'    type:          "{stype}",          // "buy" | "sell"')
    lines.append(f'    entryPrice:    {entry_price},      // {source} | يدوي أصلي: {manual}')
    lines.append(f'    entrySource:   "{source}",')
    lines.append(f"    divsSince:     {divs},")
    if status == "closed":
        lines.append(f"    status:        \"closed\",")
        lines.append(f"    closeDate:     \"{close_date}\",")
        cp2 = close_price if close_price is not None else "null"
        lines.append(f"    closePrice:    {cp2},")
        lines.append(f"    closeReason:   \"{close_reason}\",")
    if entry_date:
        lines.append(f'    entryDate:     "{entry_date}",')
    if track:
        lines.append(f'    track:         "{track}",')
    if category:
        lines.append(f'    category:      "{category}",')
    lines.append(f"    currentPrice:  {price_str}")
    lines.append("  },")
lines.append("];")
new_block = "\n".join(lines)

# ── 3) حفظ الـ cache ──
tmp = CACHE_FILE + ".tmp"
with open(tmp, "w") as f:
    json.dump(cache, f, ensure_ascii=False, indent=1)
os.replace(tmp, CACHE_FILE)

# ── 4) استبدال الكتلة في الـ HTML ──
with open(HTML_FILE) as f:
    html = f.read()
new_html, count = re.subn(r"const WATCHLIST = \[.*?\];", new_block, html, flags=re.DOTALL)
if count != 1:
    print(f"❌ WATCHLIST block not found or multiple matches ({count}) — aborting")
    raise SystemExit(1)
new_html = re.sub(r'(updatedAt:\s*")[^"]+(")', r"\g<1>" + now_iso + r"\2", new_html)

with open(HTML_FILE, "w") as f:
    f.write(new_html)

print(f"\n✅ Done tr-v2 — {len(stocks_config)} stocks | sahmk: {stats['sahmk-close']} | adjclose: {stats['adjclose']} | cache: {stats['cache']} | fallback: {stats['manual-fallback']} | same-day: {stats['same-day-close']}")
PYEOF

echo "✅ Script finished"
