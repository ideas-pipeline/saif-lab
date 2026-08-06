#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حلقة الفحص الذاتي L1 — عقد criteria v3 (docs/requirements-v3.md §7-§8).
تقرير فقط: لا يعدل بيانات ولا يوقف النشر. يخرج دائماً بـ0.
الاستخدام: python3 scripts/self-check-L1.py [stocks-data.json]"""
import json, os, sys
from datetime import datetime

DATA = sys.argv[1] if len(sys.argv) > 1 else "/srv/ideas/stocks-data.json"
W = []
def warn(m):
    W.append(m)

try:
    with open(DATA, encoding="utf-8") as f:
        cur = json.load(f)
except Exception as e:
    print("L1: تعذر قراءة البيانات — %s" % e)
    sys.exit(0)

# تعريف S موحد مع كون المحرك حرفياً (symbol + غير مشطوب) — درس عدم التطابق 05-08ب
S = [s for s in cur.get("stocks", []) if s.get("symbol") and not s.get("delisted")]
N = len(S)
print("=" * 58)
print("L1 (criteria v3) — %s | أسهم: %d (+%d delisted)" % (
    datetime.now().strftime("%Y-%m-%d %H:%M"), N,
    sum(1 for s in cur.get("stocks", []) if s.get("delisted"))))
print("الملف: %s" % os.path.abspath(DATA))
print("أختامه: lastUpdated=%s | priceSource=%s | scoringVersion=%s | runType=%s" % (
    cur.get("lastUpdated"), cur.get("priceSource"),
    cur.get("scoringVersion"), cur.get("runType")))
print("=" * 58)

# ── [0] هوية الملف — حارس «الملف الآخر» (جذر إنذارات 05-08ب الكاذبة الثلاثة:
# ‏L1 قرأ ملفاً بائتاً في مساره الافتراضي بينما التشغيلة كتبت ملفاً آخر) ──
has_scores = any(s.get("investmentScore") for s in S)
if has_scores and (not cur.get("coverage") or cur.get("priceSource") != "sahmk-direct-v3"):
    warn("🚨 صارخ: الملف المقروء ليس ناتج تشغيلة جالب v3 (coverage=%s، priceSource=%s) — "
         "شبهة مسار خاطئ/ملف بائت؛ كل ما يلي يصف هذا الملف لا التشغيلة"
         % (bool(cur.get("coverage")), cur.get("priceSource")))
lu_age = None
try:
    lu_age = (datetime.now() - datetime.strptime(str(cur.get("lastUpdated", ""))[:10], "%Y-%m-%d")).days
except (ValueError, TypeError):
    pass
if lu_age is None or lu_age > 3:
    warn("الملف بائت: lastUpdated=%s (عمره %s يوماً) — تحقق من المسار وترتيب الخط"
         % (cur.get("lastUpdated"), lu_age))

# ── [1] تغطية الاشتقاق وبوابة الانهيار (§7) + أرضيات مطلقة ──
cov = cur.get("coverage") or {}
sma_cap = sum(1 for s in S if (s.get("weeklyTechnical") or {}).get("sma200w"))
# قرار المحلل 05-08: ‏Z بالإطار اليومي — يُقرأ من dailyExtra
z_cap = sum(1 for s in S if (s.get("dailyExtra") or {}).get("zExt") is not None)
with_de = sum(1 for s in S if (s.get("dailyExtra") or {}))
isc = lambda s: s.get("investmentScore") or {}
rated_n = sum(1 for s in S if isc(s).get("filtered") is False
              and isc(s).get("classCode") != "unrated")
print("\n[1] التغطية: SMA200W ‏%d | قادرو Z (يومي) ‏%d | ذوو dailyExtra ‏%d | المثبت: %s"
      % (sma_cap, z_cap, with_de, cov))
if cov.get("zCapable") and z_cap < cov["zCapable"] * 0.9:
    warn("قادرو Z انهاروا >10%%: ‏%d → %d" % (cov["zCapable"], z_cap))
# ضبط المحلل: النمو الرتيب متوقع لقادري SMA200W — أي انكماش عن المخزون إنذار
if cov.get("smaCapable") and sma_cap < cov["smaCapable"]:
    warn("قادرو SMA200W انكمشوا (النمو الرتيب هو المتوقع): ‏%d → %d"
         % (cov["smaCapable"], sma_cap))
# أرضيات لا تعتمد أساساً مخزناً (عمى التشغيلة الأولى المرصود 05-08):
if rated_n > 0 and z_cap == 0:
    warn("🚨 صارخ: قادرو Z = 0 مع %d مقيَّماً — محور المخاطر يفقد بنده Z للجميع "
         "(هكذا مرّت تشغيلة التفعيل العمياء)" % rated_n)
# اتساق دقيق (معايرة 05-08ب: العتبة الخام 80% كانت ستنذر كاذباً على التشغيلة السليمة
# ‏198/248=79.8% — الـ50 حديثة التاريخ بلا SMA مشروعة): من عمقه ≥200 أسبوعاً يجب أن يملك SMA
exp_sma = sum(1 for s in S if ((s.get("weeklyTechnical") or {}).get("weeks") or 0) >= 200)
if sma_cap < exp_sma:
    warn("🚨 صارخ: قادرو SMA200W ‏%d < ذوي ≥200 أسبوعاً (%d) — اشتقاق أسبوعي مكسور"
         % (sma_cap, exp_sma))
if with_de > 0 and sma_cap < 0.6 * with_de:
    warn("قادرو SMA200W ‏%d < 60%% ممن لديهم dailyExtra (%d) — عمق أسبوعي منهار"
         % (sma_cap, with_de))
if rated_n > 0 and not (cur.get("deScaleDecision")):
    warn("deScaleDecision غير محسوم مع وجود %d مقيَّماً — مقياس D/E غير موثوق" % rated_n)
if rated_n > 0 and not ((cur.get("equitySource") or {}).get("choice")):
    warn("equitySource غير محسوم مع وجود %d مقيَّماً — مصدر حقوق الملكية غير موثوق" % rated_n)

# ── [2] الشرائح الحدّية: جلسات 200-299 (SMA200D بلا Z) + أسابيع 200-203 (ميل محايد) ──
slice_z = [s["symbol"] for s in S
           if 200 <= ((s.get("dailyExtra") or {}).get("sessions") or 0) < 300]
slice_w = [s["symbol"] for s in S
           if 200 <= ((s.get("weeklyTechnical") or {}).get("weeks") or 0) < 204]
print("\n[2] شريحة 200-299 جلسة (SMA200D حاضر وZ غائب — 0/3 بقرار واعٍ): %d %s"
      % (len(slice_z), slice_z[:10]))
print("    شريحة 200-203 أسبوعاً (SMA200W بلا ميل → معاملة محايدة 6/8): %d %s"
      % (len(slice_w), slice_w[:10]))

# ── [3] الحراس الراسبون (§8) ──
from collections import Counter
rej = Counter()
for s in S:
    for g in (s.get("guardRejected") or []):
        rej[g.get("field")] += 1
print("\n[3] حراس المعقولية — الرفض بالحقل: %s" % (dict(rej) or "لا رفض"))
if sum(rej.values()) > 40:
    warn("رفض الحراس مرتفع: %d قيمة — راجع جودة المصدر" % sum(rej.values()))

# ── [4] unrated وfiltered وبوابة السيولة + مطابقة عدّ المحرك (عقد 05-08ب) ──
unrated = sum(1 for s in S if isc(s).get("classCode") == "unrated")
filtered = sum(1 for s in S if isc(s).get("filtered"))
liq_blocked = sum(1 for s in S if not (s.get("liquidityGate") or {}).get("passed", True))
print("\n[4] unrated: %d | filtered: %d | محجوب سيولة: %d" % (unrated, filtered, liq_blocked))
# عقد الإحصاء الموحد: المحرك خزّن عدّه في scoringStats — إعادة العدّ المستقلة تطابقه
# وإلا فالعقد منكسر (مفتاح تغيّر) أو الملف غير ملف تشغيلة المحرك
eng = (cur.get("scoringStats") or {}).get("counts")
if eng is not None:
    eng_filtered = eng.get("filtered", 0)
    eng_unrated = eng.get("unrated", 0)
    if filtered != eng_filtered or unrated != eng_unrated:
        warn("🚨 صارخ: عدّ L1 ‏(filtered=%d، unrated=%d) ≠ إحصاء المحرك (%d، %d) — "
             "عقد مفاتيح منكسر أو ملف آخر" % (filtered, unrated, eng_filtered, eng_unrated))
elif has_scores:
    warn("scoringStats غائب مع وجود investmentScore — محرك أقدم من عقد 05-08ب أو ملف آخر")

# ── [5] تغير القطاع/النشاط (§7 — إنذار) ──
chg = cur.get("sectorChanges") or []
print("\n[5] تغيرات sector/industry المسجلة: %d" % len(chg))
for c in chg[:5]:
    print("    %s.%s: %s → %s (%s)" % (c.get("symbol"), c.get("field"), c.get("old"), c.get("new"), c.get("date")))
if chg:
    warn("تغير قطاع/نشاط لـ%d سهماً — يقلب المسار والوسطاء، راجع" % len(chg))

# ── [6] حارس تقاطع P/E (§3.5): فرق المحسوب عن المصدر >10% ──
pe_div = [(s["symbol"], (s.get("valuation") or {}).get("peSourceDiffPct"))
          for s in S if ((s.get("valuation") or {}).get("peSourceDiffPct") or 0) > 10]
print("\n[6] تقاطع P/E (محسوب مقابل مصدر، فرق >10%%): %d %s" % (len(pe_div), pe_div[:6]))
if len(pe_div) > 25:
    warn("تباعد P/E واسع (%d سهماً) — شبهة اصطلاح eps" % len(pe_div))

# ── [7] نضارة الكتل بأختامها ──
def age_days(stamp):
    try:
        return (datetime.now() - datetime.strptime(str(stamp)[:10], "%Y-%m-%d")).days
    except (ValueError, TypeError):
        return None
stale_fin = sum(1 for s in S if (age_days(s.get("financialsUpdated")) or 0) > 10)
stale_daily = sum(1 for s in S
                  if (age_days((s.get("dailyExtra") or {}).get("updatedAt")) or 0) > 3)
print("\n[7] النضارة: financials أقدم من 10 أيام: %d | dailyExtra أقدم من 3: %d" % (stale_fin, stale_daily))
if stale_daily > 25:
    warn("كتل يومية بائتة: %d" % stale_daily)

# ── [8] معقولية توزيع النقاط (مقام 100) ──
totals = [isc(s).get("total") for s in S if isc(s).get("filtered") is False
          and isc(s).get("classCode") != "unrated" and isc(s).get("total") is not None]
if totals:
    import statistics
    print("\n[8] النقاط (مقام 100): n=%d | وسيط %.0f | أدنى %d | أعلى %d | ≥80: %d | ≥65: %d"
          % (len(totals), statistics.median(totals), min(totals), max(totals),
             sum(1 for t in totals if t >= 80), sum(1 for t in totals if t >= 65)))
    if eng is not None:
        eng_rated = sum(v for k, v in eng.items() if k not in ("filtered", "unrated"))
        if len(totals) != eng_rated:
            warn("🚨 صارخ: n المصنفين في [8] ‏(%d) ≠ مجموع فئات المحرك (%d) — عقد منكسر أو ملف آخر"
                 % (len(totals), eng_rated))
    bad = [t for t in totals if not (0 <= t <= 100)]
    if bad:
        warn("نقاط خارج [0،100]: %s" % bad[:5])

print("\n" + "=" * 58)
if W:
    print("⚠️ إنذارات: %d" % len(W))
    for w in W:
        print("   • %s" % w)
else:
    print("✅ لا إنذارات")
print("=" * 58)
sys.exit(0)
