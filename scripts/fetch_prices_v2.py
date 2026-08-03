import json, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

TARGET = sys.argv[1] if len(sys.argv) > 1 else "/srv/ideas/stocks-data.json"
key = open("/srv/ideas/.sahmk.key").read().strip()
H = {"X-API-Key": key, "User-Agent": "Mozilla/5.0"}
riyadh = timezone(timedelta(hours=3))
now = datetime.now(riyadh).strftime("%Y-%m-%d %H:%M")

data = json.load(open(TARGET))
stocks = [s for s in data["stocks"] if s.get("symbol")]
syms = [s["symbol"] for s in stocks]
by = {s["symbol"]: s for s in stocks}

# 1) sahmk bulk: 50 per batch, retry+backoff per batch
got = {}
batches_failed = 0
for i in range(0, len(syms), 50):
    batch = syms[i:i+50]
    url = "https://app.sahmk.sa/api/v1/quotes?symbols=" + ",".join(batch)
    r = None
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30))
            break
        except Exception:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    if r is None:
        batches_failed += 1
        continue
    for q in r.get("quotes", []):
        got[q["symbol"]] = q
    time.sleep(1)

# 2) apply sahmk data
updated_sahmk = 0
fallback = []
for sym in syms:
    q = got.get(sym)
    price = q.get("price") if q else None
    if not price or price <= 0:
        fallback.append(sym)
        continue
    st = by[sym]
    st["currentPrice"] = round(price, 2)
    ch = q.get("change")
    if ch is not None:
        prev = round(price - ch, 2)
        st["previousClose"] = prev
        cp = q.get("change_percent")
        if cp is not None:
            st["dailyChange"] = round(cp, 2)
        elif prev > 0:
            st["dailyChange"] = round((round(price,2) - prev) / prev * 100, 2)
    st["priceUpdatedAt"] = now
    st["priceSource"] = "sahmk"
    nl = q.get("net_liquidity")
    if nl is not None:
        st["netLiquidity"] = nl
    updated_sahmk += 1

# 3) yahoo fallback per missing symbol (silent backup)
updated_yahoo = 0
still_failed = []
for sym in fallback:
    resp = None
    for attempt in range(3):
        try:
            u = "https://query1.finance.yahoo.com/v8/finance/chart/" + sym + ".SR?interval=1d&range=5d"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            resp = json.load(urllib.request.urlopen(req, timeout=10))
            break
        except Exception:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    ok = False
    if resp is not None:
        try:
            result = resp["chart"]["result"][0]
            meta = result["meta"]
            st = by[sym]
            current = round(meta["regularMarketPrice"], 2)
            st["currentPrice"] = current
            st["yahooName"] = meta.get("longName", meta.get("shortName", ""))
            closes = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
            valid = [round(c, 2) for c in closes if c is not None]
            if len(valid) >= 2:
                prev = valid[-2]
                st["previousClose"] = prev
                if prev > 0:
                    st["dailyChange"] = round((current - prev) / prev * 100, 2)
            st["priceUpdatedAt"] = now
            st["priceSource"] = "yahoo-fallback"
            updated_yahoo += 1
            ok = True
        except Exception:
            pass
    if not ok:
        still_failed.append(sym)
    time.sleep(0.3)

data["lastUpdated"] = now + " الرياض"
data["priceSource"] = "sahmk-bulk-v1+yahoo-fallback"
data.setdefault("priceSourceSince", "2026-07-20")
# nl-history (2026-07-23): لقطة صافي السيولة اليومية — ذاكرة مؤشر التجميع (بند 13) — بلا طلبات إضافية
try:
    import os
    HIST = "/srv/ideas/net-liquidity-history.json"
    hday = now[:10]
    hist = json.load(open(HIST)) if os.path.exists(HIST) else {}
    hist[hday] = {s2: q2.get("net_liquidity") for s2, q2 in got.items() if q2.get("net_liquidity") is not None}
    htmp = HIST + ".tmp"
    json.dump(hist, open(htmp, "w"), ensure_ascii=False)
    os.replace(htmp, HIST)
except Exception as e2:
    print("nl-history تحذير (لا يوقف الأسعار):", e2)

json.dump(data, open(TARGET, "w"), indent=2, ensure_ascii=False)
print("سهمك:", updated_sahmk, "| احتياطي Yahoo:", updated_yahoo, "| فشل نهائي يحتفظ بالقديم:", len(still_failed), still_failed[:10])
print("دفعات bulk فاشلة:", batches_failed, "| lastUpdated:", data["lastUpdated"])
