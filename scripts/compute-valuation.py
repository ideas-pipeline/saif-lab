#!/usr/bin/env python3
# بند 24 (dev v2) — حساب نسب التقييم من السعر الحي. صفر طلبات شبكة.
# P/B محروس بفحص الاتساق لكل سهم + العائد. P/E و EV/EBITDA يبقيان مجمدين.
import json, sys
from datetime import datetime, timezone, timedelta

DATA = sys.argv[1] if len(sys.argv) > 1 else "/srv/ideas/stocks-data.json"
now = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M")

with open(DATA) as f:
    data = json.load(f)

pb_live = pb_frozen = dy_live = dy_none = skipped = 0
for s in data["stocks"]:
    vi = s.get("valuationInputs") or {}
    p = s.get("currentPrice")
    if not vi or not p or p <= 0:
        skipped += 1
        continue
    v = dict(s.get("valuation") or {})
    parts = {"pe": "frozen", "evEbitda": "frozen"}

    # P/B — لا يكتب إلا إذا اجتاز السهم فحص الاتساق في مصدره
    ptb, tp = vi.get("priceToBook"), vi.get("theirPrice")
    if vi.get("pbConsistent") and ptb and ptb > 0 and tp and tp > 0:
        v["pb"] = round(ptb * p / tp, 4)
        parts["pb"] = "live"
        pb_live += 1
    else:
        parts["pb"] = "frozen"
        pb_frozen += 1

    # العائد — مصدر مستقل عن fundamentals المعطوب
    dv = vi.get("divTtm12m")
    if dv is None:
        parts["dividendYield"] = "frozen"
    elif dv > 0:
        v["dividendYield"] = round(dv / p, 6)
        parts["dividendYield"] = "live"
        dy_live += 1
    else:
        v["dividendYield"] = None
        parts["dividendYield"] = "live"
        dy_none += 1

    s["valuation"] = v
    s["valuationParts"] = parts
    s["valuationUpdatedAt"] = now

with open(DATA, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("P/B: حي %d | مجمد %d" % (pb_live, pb_frozen))
print("العائد: حي %d | لا يوزع %d" % (dy_live, dy_none))
print("متخطى (بلا مدخلات): %d" % skipped)
