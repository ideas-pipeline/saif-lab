#!/bin/bash
# feed-watchlist.sh — المغذي الآلي الموسوم (بند 7 مرحلة أ، 2026-07-14)
# ---
# يحكمه: /srv/ideas/accuracy-criteria.md (المجمدة + ملحق 14-07)
# المطبقة = classCode strong_buy|buy | الظل = نقاط>=65 خارج المطبقة (buy_wait)
# الدخول في كل الأنظمة (خيار أ) موسوماً regimeAtEntry/timingAtEntry/scoreAtEntry
# الإغلاق مرحلة أ: نقاط <50 يومياً — لا حذف أبداً
# فشل المغذي يُنبه ولا يُسقط السلسلة (exit 0 دائماً)
# للتراجع: إزالة سطر الاستدعاء من run-stocks-daily.sh + استعادة config من archive/

CONFIG_JSON="${CONFIG_JSON:-/srv/ideas/watchlist-config.json}"
STOCKS_JSON="${STOCKS_JSON:-/srv/ideas/stocks-data.json}"
ARCHIVE_DIR="${ARCHIVE_DIR:-/srv/ideas/archive}"
export CONFIG_JSON STOCKS_JSON ARCHIVE_DIR

python3 << 'PYEOF'
import json, os, shutil
from datetime import datetime

CONFIG  = os.environ["CONFIG_JSON"]
STOCKS  = os.environ["STOCKS_JSON"]
ARCHIVE = os.environ["ARCHIVE_DIR"]
today = datetime.now().strftime("%Y-%m-%d")

with open(STOCKS) as f:
    data = json.load(f)
with open(CONFIG) as f:
    cfg = json.load(f)
stocks_cfg = cfg.setdefault("stocks", [])

regime = (data.get("marketRegime") or {}).get("regime", "")

# فهرس المدخلات الآلية المفتوحة: (رمز، عينة) -> مدخل
def sample_of(entry):
    return "shadow" if entry.get("category") == "buy_wait" else "applied"

open_auto = {}
for e in stocks_cfg:
    if e.get("track") == "auto" and e.get("status", "open") == "open":
        open_auto[(e["symbol"], sample_of(e))] = e

added, closed, skipped = [], [], 0
snapshot = {}   # رمز -> (سعر، نقاط)

for s in data.get("stocks", []):
    inv = s.get("investmentScore") or {}
    total = inv.get("total")
    code = inv.get("classCode", "")
    cur = s.get("currentPrice")
    sma_w = (s.get("weeklyTechnical") or {}).get("sma200w")
    snapshot[s["symbol"]] = (cur, total)
    if cur is None or total is None:
        continue
    if code in ("strong_buy", "buy"):
        sample, category = "applied", code
    elif total >= 65:
        sample, category = "shadow", "buy_wait"
    else:
        continue
    if (s["symbol"], sample) in open_auto:
        skipped += 1
        continue
    entry = {
        "symbol": s["symbol"],
        "name": s.get("name", ""),
        "sector": s.get("sector", ""),
        "type": "buy",
        "entryPrice": cur,
        "entryDate": today,
        "track": "auto",
        "category": category,
        "engineClass": code,
        "scoreAtEntry": total,
        "timingAtEntry": inv.get("timing", ""),
        "regimeAtEntry": regime,
        "aboveSmaAtEntry": bool(cur >= sma_w) if (cur is not None and sma_w) else None,
        "status": "open",
    }
    stocks_cfg.append(entry)
    open_auto[(s["symbol"], sample)] = entry
    added.append(entry)

# إغلاق مرحلة أ: نقاط < 50 (يشمل الظل لسلامة المقارنة)
for e in stocks_cfg:
    if e.get("track") != "auto" or e.get("status", "open") != "open":
        continue
    cur, total = snapshot.get(e["symbol"], (None, None))
    if total is not None and total < 50:
        e["status"] = "closed"
        e["closeDate"] = today
        e["closePrice"] = cur
        e["closeReason"] = "score_below_50"
        closed.append((e["symbol"], total))

if added or closed:
    backup = f"{ARCHIVE}/watchlist-config.json.{today}"
    if not os.path.exists(backup):
        shutil.copy2(CONFIG, backup)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CONFIG)

n_applied = sum(1 for e in added if e["category"] != "buy_wait")
n_shadow  = len(added) - n_applied
print(f"✅ feed-watchlist: أضيف {n_applied} مطبقة + {n_shadow} ظل | أُغلق {len(closed)} | تخطى مفتوحاً {skipped} | النظام: {regime}")
for e in added:
    print(f"   + [{e['category']}] {e['symbol']} {e['name']} @ {e['entryPrice']} (نقاط {e['scoreAtEntry']}، توقيت {e['timingAtEntry']})")
for sym, sc in closed:
    print(f"   ✖ أُغلق {sym} (نقاط {sc})")
PYEOF

if [ $? -ne 0 ]; then
    echo "⚠️ ALERT: feed-watchlist فشل — السلسلة تكمل على config القائم"
fi
exit 0
