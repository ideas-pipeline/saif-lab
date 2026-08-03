import json, os, shutil
from datetime import datetime
CONFIG = "/srv/ideas/watchlist-config.json"
DATA = "/srv/ideas/stocks-data.json"
ARCHIVE = "/srv/ideas/archive"
DRY = os.environ.get("DRY_RUN") == "1"
today = datetime.now().strftime("%Y-%m-%d")
data = json.load(open(DATA))
lu = str(data.get("lastUpdated", ""))
if today not in lu and not DRY:
    print(f"⛔ بيانات غير محدثة اليوم ({lu}) — لا إغلاق")
    raise SystemExit(0)
wt = {}
for s in data.get("stocks", []):
    w = s.get("weeklyTechnical") or {}
    wt[s["symbol"]] = (s.get("currentPrice"), w.get("sma200w"))
cfg = json.load(open(CONFIG))
stocks = cfg.get("stocks", cfg if isinstance(cfg, list) else [])
closed = []
for e in stocks:
    if e.get("track") != "auto" or e.get("status", "open") != "open":
        continue
    cur, sma = wt.get(e["symbol"], (None, None))
    if cur is None or not sma:
        continue
    # تفسير الكسر الامين (قرار سلطان 23-07): يغلق فقط من دخل فوق المتوسط ثم كسره
    # aboveSmaAtEntry من المغذي للجدد، والتقريب entryPrice>=sma للقائمين (المتوسط بطيء)
    entered_above = e.get("aboveSmaAtEntry")
    if entered_above is None:
        entered_above = e.get("entryPrice", 0) >= sma
    if entered_above and cur < sma:
        e["status"] = "closed"
        e["closeDate"] = today
        e["closePrice"] = cur
        e["closeReason"] = "sma200w_weekly_break"
        closed.append((e["symbol"], e.get("category",""), cur, round(sma, 2)))
if DRY:
    print(f"[DRY] كان سيُغلق {len(closed)}:")
    for c in closed:
        print("  ", c)
    raise SystemExit(0)
if closed:
    backup = f"{ARCHIVE}/watchlist-config.json.{today}-sma200w"
    if not os.path.exists(backup):
        shutil.copy2(CONFIG, backup)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CONFIG)
print(f"مرحلة ب: أُغلق {len(closed)}: {[c[0] for c in closed]}")
