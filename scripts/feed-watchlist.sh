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

# قاعدة الإقفال الحصرية (شرط المحلل 2 — اعتماد 05-08ب): المغذي وقاعدتا الإغلاق
# لا تعمل إلا على تشغيلة إقفال. ختم غائب = ملف جالب أقدم → رفض مسموع لا افتراض.
rt = data.get("runType")
if rt != "close":
    print("⛔ feed-watchlist: تشغيلة سوق مفتوح (runType=%s) — لا مدخلات ولا إغلاقات،"
          " دخول وخروج العينة بأسعار إقفال حصراً (شرط المحلل 2)" % rt)
    raise SystemExit(0)

with open(CONFIG) as f:
    cfg = json.load(f)
stocks_cfg = cfg.setdefault("stocks", [])

regime = (data.get("marketRegime") or {}).get("regime", "")

# فهرس المدخلات الآلية المفتوحة: (رمز، عينة) -> مدخل
def sample_of(entry):
    return "shadow" if entry.get("category") == "buy_wait" else "applied"

open_auto = {}
for e in stocks_cfg:
    if e.get("sampleType") == "value-shadow":
        continue   # عينة الظل الثانية مسار مستقل — لا تحجز مقعد العينة الرسمية
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
    # (criteria v2.1 — حارس بند 18): سهم unrated لا يدخل قائمة المراقبة بأي عينة —
    # لم يختبره الفلتر فليس توصية نظام، ودخوله الظل (نقاط>=65) يلوث تقرير طبقة التوقيت.
    # المفتوحون القائمون لأسهم صارت unrated يبقون ويدارون بقواعد الإغلاق القائمة (لا إغلاق رجعي).
    if inv.get("unrated") is True or code == "unrated":
        continue
    # (criteria v3 §2) بوابة السيولة إقصائية عن التوصيات — لا دخول بأي عينة (يشمل الظل — قرار معلن)
    if not (s.get("liquidityGate") or {}).get("passed", True):
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
        "scoreScaleAtEntry": "criteria-v3",  # مقام 100 مباشرة — لا مقارنة عبر سلالم النسخ الأقدم
        "status": "open",
    }
    stocks_cfg.append(entry)
    open_auto[(s["symbol"], sample)] = entry
    added.append(entry)

# إغلاق مرحلة أ: نقاط < 50 (يشمل الظل لسلامة المقارنة — وليس ظل القيمة: قواعده مستقلة)
for e in stocks_cfg:
    if e.get("track") != "auto" or e.get("status", "open") != "open":
        continue
    if e.get("sampleType") == "value-shadow":
        continue   # مستبعد بالتعريف (total=0) — إغلاقه بقاعدة <50 يقتله فوراً زوراً
    cur, total = snapshot.get(e["symbol"], (None, None))
    if total is not None and total < 50:
        e["status"] = "closed"
        e["closeDate"] = today
        e["closePrice"] = cur
        e["closeReason"] = "score_below_50"
        closed.append((e["symbol"], total))

# ══ عينة الظل الثانية: «قيمة تحت الفلتر» (مواصفة المحلل 07-08 — ظل بحثي، ليست توصيات) ══
# الدخول: مستبعد بفلتر SMA200W تحديداً + عابر السيولة + P/E موجب < 0.8×وسيط قطاعه
# وبسقف مطلق 15 + جودة ≥18/30 (من investmentScore.axes) + OCF موجب. سقف 15 متزامناً.
# القياس: measurement v3 (tasiRet/excessNet بخصم 3.5% تناسبياً) + MAE كل تشغيلة close.
# الإغلاق: 12 شهراً أو خروج صعودي (استعادة الفلتر / تجاوز سقف الرخص).
VS_CAP = 15
SMA_FILTER_REASON = "تحت SMA200W بدون إشارات انعكاس"
tasi_now = (data.get("tasi") or {}).get("current")
sm_map = data.get("sectorMedians") or {}
by_sym = {s["symbol"]: s for s in data.get("stocks", []) if s.get("symbol")}
vs_all = [e for e in stocks_cfg if e.get("sampleType") == "value-shadow"]
vs_closed_now, vs_added = [], []
vs_meas_updated = False   # تحديثات MAE/القياس الجارية تستوجب الكتابة ولو بلا دخول/إغلاق
for e in vs_all:
    if e.get("status", "open") != "open":
        continue
    st = by_sym.get(e["symbol"]) or {}
    inv = st.get("investmentScore") or {}
    cur = st.get("currentPrice")
    if cur is None or not e.get("entryPrice"):
        continue
    days = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(e["entryDate"], "%Y-%m-%d")).days
    ret = (cur / e["entryPrice"] - 1) * 100
    e["maePct"] = round(min(e.get("maePct", 0.0), ret), 2)          # أقصى انزلاق سلبي بالإغلاقات
    vs_meas_updated = True
    if tasi_now and e.get("tasiAtEntry"):
        tret = (tasi_now / e["tasiAtEntry"] - 1) * 100
        e["tasiRet"] = round(tret, 2)
        e["excessNet"] = round(ret - tret - 3.5 * days / 365, 2)    # measurement v3 جارٍ
    # ثمن الانتظار: أول عبور للفلتر (يشمل استثناء الانعكاس) يُسجل تاريخاً وسعراً
    passed_now = inv.get("filtered") is False and inv.get("total") is not None
    if passed_now and not e.get("filterCrossDate"):
        e["filterCrossDate"], e["filterCrossPrice"] = today, cur
    vs_reason = None
    if days >= 365:
        vs_reason = "max_age_12m"
    elif passed_now:
        vs_reason = "filter_recovered"
    else:
        pe_now = (st.get("valuation") or {}).get("pe")
        med_now = (sm_map.get(st.get("sector")) or {}).get("peMedian")
        if pe_now and pe_now > 0 and (pe_now > 15 or (med_now and pe_now >= 0.8 * med_now)):
            vs_reason = "cheapness_exited"
    if vs_reason:
        e["status"], e["closeDate"], e["closePrice"], e["closeReason"] = "closed", today, cur, vs_reason
        vs_closed_now.append((e["symbol"], vs_reason, e.get("excessNet")))
vs_open_syms = {e["symbol"] for e in vs_all if e.get("status", "open") == "open"}
if len(vs_open_syms) < VS_CAP:
    cands = []
    for s in data.get("stocks", []):
        inv = s.get("investmentScore") or {}
        if not (inv.get("filtered") is True and inv.get("filterReason") == SMA_FILTER_REASON):
            continue   # فلتر SMA تحديداً — لا unrated ولا فاقد البيانات المالية
        if not (s.get("liquidityGate") or {}).get("passed", True):
            continue
        if s["symbol"] in vs_open_syms:
            continue
        pe = (s.get("valuation") or {}).get("pe")
        med = (sm_map.get(s.get("sector")) or {}).get("peMedian")
        if not (pe and pe > 0 and med and pe < 0.8 * med and pe < 15):
            continue
        q = (inv.get("axes") or {}).get("quality")
        ocf = (s.get("financials") or {}).get("ocf")
        if q is None or q < 18 or not ocf or ocf <= 0:
            continue
        cur = s.get("currentPrice")
        sma_w2 = (s.get("weeklyTechnical") or {}).get("sma200w")
        if cur is None or not sma_w2:
            continue
        cands.append((pe / med, s, pe, med, q, cur, sma_w2, inv))
    cands.sort(key=lambda x: x[0])      # عند تزاحم المقاعد: الأرخص نسبياً أولاً (قاعدة معلنة)
    for _ratio, s, pe, med, q, cur, sma_w2, inv in cands[:VS_CAP - len(vs_open_syms)]:
        e = {
            "symbol": s["symbol"], "name": s.get("name", ""), "sector": s.get("sector", ""),
            "type": "buy", "entryPrice": cur, "entryDate": today, "track": "auto",
            "sampleType": "value-shadow", "category": "value-shadow",
            "engineClass": "filtered", "scoreAtEntry": 0, "qualityAtEntry": q,
            "timingAtEntry": inv.get("timing", ""), "regimeAtEntry": regime,
            "scoreScaleAtEntry": "criteria-v3", "aboveSmaAtEntry": False,
            "priceVsSmaPct": round((cur / sma_w2 - 1) * 100, 2),
            "peAtEntry": pe, "peSectorMedianAtEntry": med,
            "tasiAtEntry": tasi_now, "maePct": 0.0,
            "status": "open",
        }
        stocks_cfg.append(e)
        vs_added.append(e)
if added or closed or vs_added or vs_closed_now or vs_meas_updated:
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
n_vs_open = sum(1 for e in stocks_cfg if e.get("sampleType") == "value-shadow" and e.get("status", "open") == "open")
print(f"🔬 ظل القيمة (بحثي): مفتوحة {n_vs_open}/{VS_CAP} | دخل {len(vs_added)} | أُغلق {len(vs_closed_now)}")
for e in vs_added:
    print(f"   + [value-shadow] {e['symbol']} {e['name']} @ {e['entryPrice']} "
          f"(P/E {e['peAtEntry']} مقابل وسيط {e['peSectorMedianAtEntry']}، جودة {e['qualityAtEntry']}/30، "
          f"تحت SMA200W بـ{abs(e['priceVsSmaPct'])}%)")
for sym, rs, ex in vs_closed_now:
    print(f"   ✖ [value-shadow] أُغلق {sym} ({rs}، زائد صافٍ {ex})")
PYEOF

if [ $? -ne 0 ]; then
    echo "⚠️ ALERT: feed-watchlist فشل — السلسلة تكمل على config القائم"
fi
exit 0
