#!/usr/bin/env python3
# بند 3 — حلقة الفحص الذاتي L1. تقرير فقط: لا يعدل بيانات ولا يوقف النشر.
# يقارن اليوم بلقطة أمس ويطبع إنذارات. يخرج دائما بـ0.
import json, gzip, glob, os, sys
from datetime import datetime

DATA = "/srv/ideas/stocks-data.json"
SNAPS = "/srv/ideas/snapshots"
W = []          # إنذارات
def warn(m): W.append(m)

def load_prev(today_path):
    try:
        files = sorted(glob.glob(os.path.join(SNAPS, "stocks-data-*.json.gz")))
        if not files:
            return None, None
        p = files[-1]
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f), os.path.basename(p)
    except Exception as e:
        return None, "تعذر: %s" % e

try:
    with open(DATA, encoding="utf-8") as f:
        cur = json.load(f)
except Exception as e:
    print("L1: تعذر قراءة البيانات — %s" % e)
    sys.exit(0)

S = cur.get("stocks", [])
N = len(S)
prev, snapname = load_prev(DATA)
P = {s["symbol"]: s for s in (prev or {}).get("stocks", [])} if prev else {}

print("=" * 58)
print("حلقة الفحص الذاتي L1 — %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
print("=" * 58)
print("الأسهم: %d | المقارنة مع: %s" % (N, snapname or "لا لقطة"))

# ── 1) الجمود: حقول حية لم تتحرك رغم تحرك السعر
if P:
    moved = [s for s in S if s.get("symbol") in P
             and s.get("currentPrice") and P[s["symbol"]].get("currentPrice")
             and s["currentPrice"] != P[s["symbol"]]["currentPrice"]]
    print("\n[1] الجمود — أسهم تحرك سعرها: %d" % len(moved))
    if len(moved) >= 20:
        for fld, path in [("pb", ("valuation", "pb")),
                          ("pe", ("valuation", "pe")),
                          ("dividendYield", ("valuation", "dividendYield"))]:
            ch = 0
            for s in moved:
                a = (s.get(path[0]) or {}).get(path[1])
                b = (P[s["symbol"]].get(path[0]) or {}).get(path[1])
                if a != b:
                    ch += 1
            pct = round(ch / len(moved) * 100)
            flag = ""
            if fld == "pb" and pct < 50:
                flag = "  ⚠️ متوقع أن يتحرك مع السعر"
            print("    %-14s تحرك عند %d من %d (%d%%)%s" % (fld, ch, len(moved), pct, flag))
            if flag:
                warn("حقل %s لم يتحرك إلا عند %d%% من الأسهم المتحركة" % (fld, pct))
    else:
        print("    عينة صغيرة — تخطي")
else:
    print("\n[1] الجمود — لا لقطة سابقة، تخطي")

# ── 2) المدخلات الناقصة
print("\n[2] المدخلات الناقصة (من %d)" % N)
checks = [("ROE", lambda s: (s.get("financials") or {}).get("returnOnEquity")),
          ("OCF", lambda s: (s.get("cashflow") or {}).get("ocf")),
          ("P/E", lambda s: (s.get("valuation") or {}).get("pe")),
          ("P/B", lambda s: (s.get("valuation") or {}).get("pb")),
          ("EV/EBITDA", lambda s: (s.get("valuation") or {}).get("evEbitda")),
          ("SMA200W", lambda s: (s.get("weeklyTechnical") or {}).get("sma200w"))]
for name, fn in checks:
    miss = sum(1 for s in S if fn(s) is None)
    print("    %-12s %d" % (name, miss))
# العائد يفصل: null بلا معطيات ≠ لا يوزع حقا (divBasis=none)
dy_none = dy_miss = 0
for s in S:
    if (s.get("valuation") or {}).get("dividendYield") is None:
        if ((s.get("valuationInputs") or {}).get("divBasis")) == "none":
            dy_none += 1
        else:
            dy_miss += 1
print("    %-12s %d (+%d لا يوزع فعلا — سليم)" % ("العائد", dy_miss, dy_none))

# ── 3) حالة مكونات التقييم
vp = [s.get("valuationParts") for s in S if s.get("valuationParts")]
noin = sum(1 for s in S if not s.get("valuationInputs"))
print("\n[3] مكونات التقييم")
print("    عليها ختم: %d | بلا valuationInputs: %d" % (len(vp), noin))
for k in ("pb", "dividendYield", "pe", "evEbitda"):
    fr = sum(1 for v in vp if v.get(k) == "frozen")
    lv = sum(1 for v in vp if v.get(k) == "live")
    print("    %-14s حي %d | مجمد %d" % (k, lv, fr))
if noin > 40:
    warn("أسهم بلا مدخلات تقييم: %d (فوق المعتاد ~24)" % noin)

# ── 4) حالة unrated (criteria v2.1 — كان: الفلتر الصامت)
# المرجع عند التفعيل: 42±2 (بند 18، ACTION-PLAN:291). خارج النطاق = إنذار.
unrated = [s for s in S
           if (s.get("investmentScore") or {}).get("unrated") is True]
silent = [s for s in S
          if (s.get("investmentScore") or {}).get("filtered") is False
          and (s.get("investmentScore") or {}).get("unrated") is not True
          and not (s.get("weeklyTechnical") or {}).get("sma200w")]
print("\n[4] unrated: %d | عبروا الفلتر بلا SMA200W دون وسم unrated: %d" % (len(unrated), len(silent)))
if not (40 <= len(unrated) <= 44):
    warn("عدد unrated خارج نطاق 42±2: %d" % len(unrated))
if silent:
    warn("أسهم عبرت الفلتر بلا SMA200W ودون وسم unrated: %d — ثغرة بند 18 عادت" % len(silent))

# ── 5) انحراف مرشحي الشراء
buy = [s for s in S if (s.get("investmentScore") or {}).get("filtered") is False
       and "شراء" in ((s.get("investmentScore") or {}).get("classification") or "")]
line = "\n[5] مرشحو الشراء: %d" % len(buy)
if P:
    pb_ = [s for s in P.values() if (s.get("investmentScore") or {}).get("filtered") is False
           and "شراء" in ((s.get("investmentScore") or {}).get("classification") or "")]
    d = len(buy) - len(pb_)
    line += " (أمس %d، الفرق %+d)" % (len(pb_), d)
    if abs(d) > 8:
        warn("مرشحو الشراء تغيروا بمقدار %+d في يوم" % d)
print(line)

# ── 6) اتساق الأختام
print("\n[6] الأختام الزمنية")
pstamps = sorted({s.get("priceUpdatedAt") for s in S if s.get("priceUpdatedAt")})
vstamps = sorted({s.get("valuationUpdatedAt") for s in S if s.get("valuationUpdatedAt")})
print("    lastRunAt: %s" % cur.get("lastRunAt"))
print("    priceUpdatedAt: %s" % (pstamps[-1] if pstamps else "—"))
print("    valuationUpdatedAt: %s" % (vstamps[-1] if vstamps else "—"))
if len(pstamps) > 2:
    warn("أختام أسعار متعددة (%d) — جلب جزئي محتمل" % len(pstamps))
# تباعد lastRunAt عن ختم الأسعار = ختم لا يقيس ما يدعيه (بند 25)
def _mins(ts):
    try:
        d, hm = ts.split()[0], ts.split()[1]
        h, m = hm.split(":")[:2]
        y, mo, dd = d.split("-")
        return ((int(y) * 12 + int(mo)) * 31 + int(dd)) * 1440 + int(h) * 60 + int(m)
    except Exception:
        return None
lr, pu = _mins(str(cur.get("lastRunAt") or "")), _mins(pstamps[-1] if pstamps else "")
if lr is not None and pu is not None and abs(lr - pu) > 60:
    warn("lastRunAt يبعد %d دقيقة عن ختم الأسعار — ختم لا يقيس الجلب (بند 25)" % abs(lr - pu))

# ── 7) معقولية التوزيع — يكشف التلف الذي يحرك القيم لا الذي يجمدها (درس 29-07)
print("\n[7] معقولية التوزيع")
PLAUS = [("revenueGrowth", lambda s: (s.get("financials") or {}).get("revenueGrowth")),
         ("profitMargins", lambda s: (s.get("financials") or {}).get("profitMargins")),
         ("returnOnEquity", lambda s: (s.get("financials") or {}).get("returnOnEquity")),
         ("pb", lambda s: (s.get("valuation") or {}).get("pb")),
         ("dividendYield", lambda s: (s.get("valuation") or {}).get("dividendYield"))]
for _nm, _fn in PLAUS:
    v = [_fn(s) for s in S]
    v = [x for x in v if isinstance(x, (int, float))]
    if len(v) < 30:
        print("    %-15s عينة صغيرة (%d)" % (_nm, len(v)))
        continue
    ints = sum(1 for x in v if float(x) == int(x))
    negs = sum(1 for x in v if x < 0)
    cnt = {}
    for x in v:
        cnt[x] = cnt.get(x, 0) + 1
    top, topn = max(cnt.items(), key=lambda z: z[1])
    ip = round(ints / len(v) * 100)
    flags = []
    if topn > len(v) * 0.10:
        flags.append("القيمة %s تتكرر %d مرة" % (top, topn))
    if ip > 40:
        flags.append("أعداد صحيحة %d%%" % ip)
    if P:
        pv = [_fn(P[k]) for k in P]
        pv = [x for x in pv if isinstance(x, (int, float))]
        pn = sum(1 for x in pv if x < 0)
        if pn >= 20 and negs < 5:
            flags.append("السالبة انهارت من %d إلى %d" % (pn, negs))
    print("    %-15s n=%d | صحيحة %d%% | سالبة %d | أكثرها %s×%d%s" % (
        _nm, len(v), ip, negs, top, topn, "  ⚠️" if flags else ""))
    for _f in flags:
        warn("%s: %s" % (_nm, _f))

# ── الخلاصة
print("\n" + "=" * 58)
if W:
    print("⚠️  إنذارات: %d" % len(W))
    for w in W:
        print("   • %s" % w)
else:
    print("✅ لا إنذارات")
print("=" * 58)
sys.exit(0)
