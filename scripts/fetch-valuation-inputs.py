#!/usr/bin/env python3
# بند 24 (dev v3) — جلب مدخلات التقييم من سهمك. أسبوعي.
# التوزيعات: مجموع 12 شهرا، فإن كان صفرا فآخر توزيع فعلي خلال 18 شهرا (بلا ازدواج).
import json, time, urllib.request, sys
from datetime import datetime, timezone, timedelta

DATA = sys.argv[1] if len(sys.argv) > 1 else "/srv/ideas/stocks-data.json"
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
BASE = "https://app.sahmk.sa/api/v1"
H = {"X-API-Key": open("/srv/ideas/.sahmk.key").read().strip(),
     "User-Agent": "Mozilla/5.0"}

def get(url, tries=2):
    for a in range(tries):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers=H), timeout=20))
        except Exception:
            if a == 0:
                time.sleep(2)
    return None

now = datetime.now(timezone.utc)
today = now.strftime("%Y-%m-%d")
d365 = (now - timedelta(days=365)).strftime("%Y-%m-%d")
d548 = (now - timedelta(days=548)).strftime("%Y-%m-%d")

with open(DATA) as f:
    data = json.load(f)
stocks = data["stocks"]
if LIMIT:
    stocks = stocks[:LIMIT]

ok = fail = pbgood = 0
b_ttm = b_last = b_none = 0
print("جلب مدخلات التقييم لـ %d سهم" % len(stocks), flush=True)

for i, s in enumerate(stocks):
    sym = s.get("symbol", "")
    if not sym:
        continue
    c = get(BASE + "/company/" + sym + "/")
    fn = ((c or {}).get("fundamentals") or {})
    ptb = fn.get("price_to_book")
    bv = fn.get("book_value")
    tp = (c or {}).get("current_price")
    mc = fn.get("market_cap")
    sh = fn.get("shares_outstanding")

    d = get(BASE + "/dividends/" + sym + "/?limit=50")
    div, basis = None, None
    if d is not None:
        rows = []
        for h in (d.get("history") or []):
            ed = h.get("eligibility_date")
            val = h.get("value")
            if ed and val and val > 0:
                rows.append((ed, val))
        rows.sort(reverse=True)
        tot = sum(v for e, v in rows if d365 <= e <= today)
        if tot > 0:
            div, basis = round(tot, 4), "ttm12m"
            b_ttm += 1
        else:
            recent = [(e, v) for e, v in rows if d548 <= e <= today]
            if recent:
                div, basis = round(recent[0][1], 4), "last18m"
                b_last += 1
            else:
                div, basis = 0.0, "none"
                b_none += 1

    cons = False
    if ptb and bv and tp and tp > 0:
        cons = abs((ptb * bv) / tp - 1) < 0.03
    if cons:
        pbgood += 1

    if c is None and d is None:
        fail += 1
    else:
        ok += 1
        s["valuationInputs"] = {
            "priceToBook": ptb, "bookValue": bv, "theirPrice": tp,
            "marketCap": mc, "sharesOutstanding": sh,
            "divTtm12m": div, "divBasis": basis, "pbConsistent": cons,
            "updatedAt": today, "source": "sahmk"
        }
    time.sleep(0.15)
    if (i + 1) % 50 == 0:
        print("  %d/%d" % (i + 1, len(stocks)), flush=True)

with open(DATA, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("تم — نجح %d | فشل %d | اتساق P/B %d" % (ok, fail, pbgood))
print("أساس التوزيع: مجموع12 %d | آخر18 %d | لا يوزع %d" % (b_ttm, b_last, b_none))
