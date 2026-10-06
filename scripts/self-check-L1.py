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
# ملحق §3.2 المؤرخ 2026-08-11: نقاط الترند الجزئية (حد EMA40W الأدنى المثبت مع غياب
# SMA200W) مشروعة حصراً لunrated أو filtered — تسربها لمُقيَّم عادي = انكسار عقد
partial_trend_bad = []
for s in S:
    wt_ = s.get("weeklyTechnical") or {}
    inv_ = s.get("investmentScore") or {}
    price_ = wt_.get("priceRef") or (s.get("dailyExtra") or {}).get("lastClose") or s.get("currentPrice")
    ema_ = wt_.get("ema40w")
    if not ema_ or wt_.get("sma200w") or not price_:
        continue
    if price_ > ema_:   # إعادة حساب مستقلة: بند التسلسل الجزئي > 0 (الحد المثبت 4/7)
        if not (inv_.get("unrated") is True or inv_.get("filtered") is True):
            partial_trend_bad.append(s["symbol"])
if partial_trend_bad:
    warn("🚨 ALERT صارخ (ملحق §3.2): نقاط ترند جزئية (EMA40W بلا SMA200W) لدى غير "
         "unrated/مفلتر — انكسار عقد: %s" % partial_trend_bad[:10])
# اجتماع قسم الانعكاس (11-08): اتساق العقد البنيوي viaReversal ⇔ filterReason
# (القالب سيطابق على العلم البنيوي — أي انفكاك بين الاثنين كسر عقد صامت محتمل)
REV_REASON = "تحت SMA200W لكن إشارات انعكاس"
rev_mismatch = [s["symbol"] for s in S
                if bool((s.get("investmentScore") or {}).get("viaReversal"))
                != ((s.get("investmentScore") or {}).get("filterReason") == REV_REASON)]
if rev_mismatch:
    warn("🚨 ALERT صارخ: انفكاك viaReversal عن filterReason==REVERSAL لدى %d: %s — "
         "عقد قسم الانعكاس منكسر" % (len(rev_mismatch), rev_mismatch[:10]))
# عزل قياس مفكرة التوزيعات (عقد المحلل 14-08): سجل مصدر divsSince في كاش سكربت
# الدقة (مفاتيح DL|) — أي تاريخ أحقية محتسب يكون null/فارغاً أو بعد يوم البيانات
# = تلوث قياس بتوزيعة مستقبلية → ALERT صارخ. غياب الكاش (بيئة بلا تشغيلة دقة) = تخطٍ.
_cache_p = os.path.join(os.path.dirname(os.path.abspath(DATA)), ".entry-adjclose-cache.json")
if os.path.exists(_cache_p):
    try:
        _dcache = json.load(open(_cache_p, encoding="utf-8"))
    except Exception:
        _dcache = {}
    _lu_day = str(cur.get("lastUpdated", ""))[:10] or "9999-99-99"
    bad_divs = []
    for _k, _v in _dcache.items():
        if not _k.startswith("DL|") or not isinstance(_v, dict):
            continue
        for _dt in _v.get("dates", []):
            if not _dt or str(_dt)[:10] > _lu_day:
                bad_divs.append("%s (%s)" % (_k, _dt))
                break
    print("    سجلات مصدر divsSince المدققة (DL|): %d" %
          sum(1 for _k in _dcache if _k.startswith("DL|")))
    if bad_divs:
        warn("🚨 ALERT صارخ: divsSince ملوث بأحقية مستقبلية/فارغة (عقد عزل مفكرة "
             "التوزيعات منكسر): %s" % bad_divs[:5])
# §4-ب الحارس ب: مستويات مقيدة التاريخ (كشف إجراء رأسمالي ملتبس) → مراجعة يدوية
lv_restricted = [s["symbol"] for s in S if (s.get("levels") or {}).get("restricted")]
print("    مستويات S/R مقيدة التاريخ (كشف ملتبس §4-ب): %d %s"
      % (len(lv_restricted), lv_restricted[:10]))
if lv_restricted:
    warn("مستويات %d سهماً مقيدة التاريخ (إجراء رأسمالي ملتبس) — مراجعة يدوية §4-ب: %s"
         % (len(lv_restricted), lv_restricted[:10]))

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
# حدّ هذا الحارس بدقة (مرصود 03-10، ومُقيَّد بعد ختم الناقد): pe المحسوب = السعر
# الحيّ ÷ vi.eps، وpeSource = pe_ratio من المصدر على سعره وقت companyAsOf
# ‏(الجالب 1032-1033: كلاهما من كتلة fundamentals نفسها). المرصود: وسيط
# ‏(theirPrice ÷ peSource) ÷ eps = 1.006 على 159 سهماً، ووسيط انزياح السعر 8.6%.
# أي أن الحقلين مشتقان اليوم من eps_ttm نفسه، فما يرصده الحارس عملياً هو انزياح
# السعر عن ختم المصدر. ما *لا* يكشفه: أن يكون المُدخل المشترك الواحد موسوماً
# خطأً. وما *يكشفه* فعلاً: أن يتباعد الحقلان — فلو تحوّل eps إلى أساس سنوي وبقي
# pe_ratio على أساسه لانطلق على ~98 سهماً بوسيط فرق 16.3% (مقاس بالمحاكاة).
# فالبوابة 4 في mapping-v3.md قائمة لا مُلغاة؛ و[9] يسدّ ما لا تبلغه بمرجع مستقل.
pe_div = [(s["symbol"], (s.get("valuation") or {}).get("peSourceDiffPct"))
          for s in S if ((s.get("valuation") or {}).get("peSourceDiffPct") or 0) > 10]
# تفكيك الموسومين (تقييد ختم 03-10/ج): «الغالب انزياح السعر» كان أضعف من الدليل.
# العزل: نسبة eps الذي يضمره المصدر (theirPrice ÷ peSource) إلى eps المخزَّن —
# وهي خالية من السعر الحيّ تماماً. قريبة من 1 ⇒ الحقلان متسقان والفرق انزياح سعر؛
# بعيدة ⇒ توتّر حقيقي بين حقلي المصدر لا يفسّره السعر. (خطأ تقريب peSource لمنزلتين
# مقيس: أقصاه 0.17% عند 2140، فلا يبلغ عتبة 2%.)
pe_tense = []
for sym, dpct in pe_div:
    st = next((x for x in S if x["symbol"] == sym), None)
    vi = (st or {}).get("valuationInputs") or {}
    tp, ps, ep = vi.get("theirPrice"), vi.get("peSource"), vi.get("eps")
    if all(isinstance(v, (int, float)) for v in (tp, ps, ep)) and ps > 0 and ep > 0 \
       and abs((tp / ps) / ep - 1) > 0.02:
        pe_tense.append((sym, dpct, round((tp / ps) / ep, 3)))
print("\n[6] تقاطع P/E (محسوب مقابل مصدر، فرق >10%%): %d %s" % (len(pe_div), pe_div[:6]))
print("    منها توتّر بين حقلي المصدر لا يفسّره انزياح السعر: %d %s" % (len(pe_tense), pe_tense[:6]))
if len(pe_div) > 25:
    warn("تباعد P/E واسع (%d سهماً)، منها %d لا يفسّرها انزياح السعر بل توتّر بين "
         "حقلي المصدر؛ ووسم eps الخاطئ على مُدخل مشترك لا يبلغه هذا الحارس أصلاً "
         "(انظر [9])" % (len(pe_div), len(pe_tense)))

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

# ── [9] اصطلاح eps بمرجع مستقل (نقطة عمى [6]) ──
# المرجع: financials.netIncome ÷ valuationInputs.sharesOutstanding (آخر سنة مالية
# كاملة). الأساسان مختلفان بالتصميم فالتباعد يُعدّ ولا يُنذر (نمو سنوي حقيقي
# يضاعفه مشروعاً، 20 من 117 موزِّعاً عند ≥2× في لقطة 10-01). الإنذار محصور في
# قلب حكم تغطية التوزيع: دخل الربح الاثني‑عشري فصمت العرض، وتجاوز الربح السنوي.
EPS_DIV_THR = 2.0          # للعدّ فقط — لا إنذار
EPS_FLIP_MARGIN = 1.05     # هامش ميت: انحراف sharesOutstanding بلغ 3.45% بين الموسومين
EPS_FLIP_WARN_AT = 10      # عتبة انحدار لا عتبة إبلاغ؛ العدّ الحيّ يُطبع دائماً
SH_SANITY_TOL = 0.25       # انحراف عدد الأسهم عن marketCap÷theirPrice
# سدّ ثغرة الصمت الجزئي (رُصدت بالحقن 03-10): حارس التغطية أدناه يقيس الكون
# ‏(80% من N) فلا يرى سقوط المرجع عن حصة صغيرة. ولو سقط sharesOutstanding عن
# الستة الموسومة وحدها لهبط عدّ القلب 6 → 0 بلا إنذار — فيصمت الوسم عن الأسهم
# التي تحتاجه بالضبط وL1 يطبع «0 قلب» كأن البيانات نظيفة. العلاج عدّ المرشَّحين
# الذين يتعذّر فحصهم: dv موجب داخل eps (أي العرض صامت) وبلا مرجع مستقل.
# ‏(‏6016 شاورمر هو الحالة الوحيدة في لقطة 10-01، يستثنيه حارس الأسهم بانحراف
# ‏57.5% — ولا يقلب حكمه أيٌّ من أساسي العدد، فالاستثناء بلا تكلفة.)
# العتبة 2 لا 3: سقوط المرجع عن سهمين من الموسومين يرفع العدّ إلى 3 فينطلق.
EPS_BLIND_WARN_AT = 2


def _implied_eps_alt(s):
    """العدد المضمَّن من القيمة السوقية — الأساس الثاني في اختبار الصلابة (uat.html)"""
    fin, vi = s.get("financials") or {}, s.get("valuationInputs") or {}
    ni, mc, tp = fin.get("netIncome"), vi.get("marketCap"), vi.get("theirPrice")
    if not all(isinstance(x, (int, float)) for x in (ni, mc, tp)) or tp <= 0:
        return None
    sh = mc / tp
    return ni / sh if sh > 0 else None


def _implied_eps(s):
    fin, vi = s.get("financials") or {}, s.get("valuationInputs") or {}
    ni, sh = fin.get("netIncome"), vi.get("sharesOutstanding")
    if not isinstance(ni, (int, float)) or not isinstance(sh, (int, float)) or sh <= 0:
        return None
    mc, tp = vi.get("marketCap"), vi.get("theirPrice")
    if isinstance(mc, (int, float)) and isinstance(tp, (int, float)) and tp > 0 \
       and abs(mc / (sh * tp) - 1) > SH_SANITY_TOL:
        return None
    return ni / sh


# عقد المطابقة مع الواجهة: شرط القلب هنا هو شرط dyFlags حرفياً — هامش ميت 1.05
# *و* صمود الحكم على أساسَي عدد الأسهم. فلو افترق العدّان لصار الرقم المراقَب
# يقيس جمهوراً غير الذي يراه المالك. والهامشيون (يصمدون على المصرَّح ويسقطون على
# المضمَّن) يُطبعون وحدهم: فئة مرشَّحة للتأرجح تستحق المتابعة لا الإنذار.
eps_pairs, eps_div, eps_flip, eps_loss, eps_marginal = 0, [], [], [], []
# حارس حياة فرع الخسارة (ختم 03-10/ب): عدّاد «يتعذّر فحصهم» أدناه يَحصر نفسه في
# مرشَّحي القلب (eps>0 و dv داخل eps)، ولا يجتازه أيٌّ من الخاسرين الثمانية —
# خمسة بلا eps أو بسالب، وثلاثة بـdv>eps. فإسقاط مرجعهم كان يُخفي ثمانية تحذيرات
# يراها المستخدم (منها سابك) وL1 يطبع 0 بخروج 0. وبعد تعليق الحقيقة على netIncome
# وحده، الطريق الوحيد لإخفائها هو سقوط netIncome نفسه — وهذا ما يرصده هذا العدّاد.
# الأساس 2026-10-01 = 0 (netIncome حاضر لدى 135 موزِّعاً كلهم).
loss_blind = []
loss_contested = []        # netIncome سالب وحقول الكتلة نفسها تقول ربحاً — لا قطع
LOSS_BLIND_WARN_AT = 0     # أساسه 0 (netIncome حاضر لدى الموزِّعين كلهم) فلا ضجيج يُحتمى منه
sh_odd = 0
eps_cand, eps_blind = 0, []
for s in S:
    vi = s.get("valuationInputs") or {}
    mc, tp, sh0 = vi.get("marketCap"), vi.get("theirPrice"), vi.get("sharesOutstanding")
    if all(isinstance(x, (int, float)) for x in (mc, tp, sh0)) and sh0 > 0 and tp > 0 \
       and abs(mc / (sh0 * tp) - 1) > 0.05:
        sh_odd += 1
    eps, dv, imp = vi.get("eps"), vi.get("divTtm12m"), _implied_eps(s)
    # خسارة السنة الكاملة لدى موزِّع — تعريف الواجهة حرفياً: الحقيقة من إشارة
    # netIncome وحدها (لا من imp)، فسابك واللجين بلا eps ويُعرض لهما الوسم،
    # ولا يُسكتهما غياب عدد الأسهم. ومن لا يوزّع لا يُعدّ هنا.
    ni_a = (s.get("financials") or {}).get("netIncome")
    if isinstance(dv, (int, float)) and dv > 0:
        if not isinstance(ni_a, (int, float)):
            loss_blind.append(s["symbol"])      # يتعذّر الحكم أصلاً — الخبر يصمت
        elif ni_a <= 0:
            # تفريق الواجهة نفسه: القطع حيث يوافق السجل، والنسب حيث يعارض
            fin_a = s.get("financials") or {}
            opp = [n for n, v in (("هامش", fin_a.get("profitMargins")),
                                  ("ROE", fin_a.get("returnOnEquity")),
                                  ("ROA", fin_a.get("returnOnAssets")))
                   if isinstance(v, (int, float)) and v > 0]
            if opp:
                loss_contested.append((s["symbol"], "+".join(opp)))
            else:
                eps_loss.append(s["symbol"])
    # المرشَّح للفحص: العرض صامت عليه (dv موجب داخل eps) فحكمه يتوقف على المرجع
    if isinstance(eps, (int, float)) and eps > 0 and isinstance(dv, (int, float)) and 0 < dv <= eps:
        eps_cand += 1
        if imp is None:
            ni2 = (s.get("financials") or {}).get("netIncome")
            why = ("بلا netIncome" if not isinstance(ni2, (int, float))
                   else "بلا عدد أسهم" if not isinstance(sh0, (int, float)) or (sh0 or 0) <= 0
                   else "عدد أسهم مرفوض")
            eps_blind.append((s["symbol"], why))
    if imp is None or not isinstance(eps, (int, float)) or eps <= 0:
        continue
    eps_pairs += 1
    if imp <= 0:
        pass                                   # عُدّ أعلاه بتعريف الواجهة
    elif max(eps / imp, imp / eps) >= EPS_DIV_THR:
        # النسبة تُطبع باتجاه موحد (الأكبر ÷ الأصغر) كي لا تظهر 0.49 تحت ترويسة ≥2×
        eps_div.append((s["symbol"], round(max(eps / imp, imp / eps), 2)))
    if isinstance(dv, (int, float)) and 0 < dv <= eps and imp > 0 and dv > imp * EPS_FLIP_MARGIN:
        alt = _implied_eps_alt(s)
        if alt is None or (alt > 0 and dv > alt * EPS_FLIP_MARGIN):
            eps_flip.append((s["symbol"], "%.3f→%.3f" % (dv / eps, dv / imp)))
        else:
            eps_marginal.append((s["symbol"], "%.3f على المصرَّح، %.3f على المضمَّن"
                                 % (dv / imp, (dv / alt) if alt and alt > 0 else float("nan"))))
sh_n = sum(1 for s in S if isinstance((s.get("valuationInputs") or {}).get("sharesOutstanding"), (int, float)))
ni_n = sum(1 for s in S if isinstance((s.get("financials") or {}).get("netIncome"), (int, float)))
dead_n = sum(1 for s in S if any(k in (s.get("valuationInputs") or {})
                                 for k in ("peRatio", "epsTtm", "forwardPe")))
print("\n[9] اصطلاح eps بمرجع مستقل: أزواج %d | تباعد ≥%.1f× (عدّ لا إنذار): %d %s"
      % (eps_pairs, EPS_DIV_THR, len(eps_div), eps_div[:6]))
print("    موزِّعون أقفلوا سنتهم الكاملة بخسارة — السجل متسق فالقطع جائز: %d %s"
      % (len(eps_loss), eps_loss[:10]))
print("    ومنهم من تعارضه حقول كتلته (لا قطع، نسبة لا حكم): %d %s"
      % (len(loss_contested), loss_contested[:8]))
print("    قلب حكم تغطية التوزيع (صامد على أساسَي عدد الأسهم — مطابق لوسم الواجهة): %d %s"
      % (len(eps_flip), eps_flip[:8]))
print("    هامشيون (يسقطون على العدد المضمَّن — لا وسم لهم ولا إنذار): %d %s"
      % (len(eps_marginal), eps_marginal[:6]))
print("    مرجعه: sharesOutstanding %d | netIncome %d من %d | عدد أسهم غير متسق مع marketCap >5%%: %d"
      "  | حقول نائمة (peRatio/epsTtm/forwardPe): %d" % (sh_n, ni_n, N, sh_odd, dead_n))
print("    يتعذّر فحصهم (العرض صامت وبلا مرجع مستقل): %d من %d مرشَّح %s"
      % (len(eps_blind), eps_cand, eps_blind[:8]))
if len(eps_blind) > EPS_BLIND_WARN_AT:
    warn("🚨 صارخ: يتعذّر فحص تغطية %d من %d مرشَّحاً (فوق عتبة %d) — المرجع المستقل "
         "سقط عن حصة من الأسهم فيصمت وسمها بلا ضجيج؛ راجع §8-ش: %s"
         % (len(eps_blind), eps_cand, EPS_BLIND_WARN_AT, eps_blind[:6]))
print("    موزِّعون يتعذّر الحكم على خسارتهم (بلا netIncome): %d %s"
      % (len(loss_blind), loss_blind[:8]))

# ‏أساس النسب + متطابقة البنوك (قرار المالك 06-10 وحكم المحلل): ROE وROA يُحسبان
# عندنا من القوائم، وقيمة المزوّد محفوظة في *Src. وللبنوك تصحّ المتطابقة
# ‏ROE/ROA ≡ أصول/ملكية — فهي حارس **بلا شبكة** على اتساق حقول المزوّد داخلياً:
# اتساقها يعني أن انحرافها عن القوائم «انزياح أساس» لا فساد قيم، وشذوذها يسمّي
# السهم الذي يستحق سؤالاً. (مقيس عند الإدخال: 9 من 10 داخل ±5.5% و1030 شاذ.)
basis_c = {"statements": 0, "provider": 0, "none": 0}
for s_ in S:
    f_ = s_.get("financials") or {}
    b_ = (f_.get("ratiosBasis") or {}).get("returnOnEquity")
    basis_c[b_ if b_ in basis_c else "none"] += 1
print("    أساس ROE: من القوائم %d · من المزوّد %d · بلا أساس %d"
      % (basis_c["statements"], basis_c["provider"], basis_c["none"]))
ident = []
for s_ in S:
    f_ = s_.get("financials") or {}
    if "bank" not in (s_.get("industry") or "").lower():
        continue
    re_, ra_ = f_.get("returnOnEquitySrc"), f_.get("returnOnAssetsSrc")
    eq_, ta_ = f_.get("equity"), f_.get("totalAssets")
    if not (re_ and ra_ and eq_ and ta_ and ra_ != 0 and eq_ != 0):
        continue
    dev = (re_ / ra_) / (ta_ / eq_) - 1
    if abs(dev) > 0.15:
        ident.append((s_["symbol"], round(dev * 100, 1)))
print("    متطابقة البنوك (ROE/ROA ≡ أصول/ملكية) على حقول المزوّد: شاذّ %d %s"
      % (len(ident), ident[:6]))
if ident:
    warn("حقول نسب المزوّد تكسر متطابقتها الحسابية على %d بنكاً (انحراف >15%%) — "
         "اتساقها الداخلي هو ما يرجّح أن فارقها عن القوائم انزياحُ أساس؛ وكسرُها "
         "يسمّي سهماً يستحق سؤال المزوّد: %s" % (len(ident), ident[:6]))
if len(loss_blind) > LOSS_BLIND_WARN_AT:
    warn("🚨 صارخ: %d موزِّعاً بلا netIncome (الأساس 0) — وسم خسارة السنة الكاملة "
         "يصمت عنهم بلا ضجيج؛ راجع §8-ش: %s" % (len(loss_blind), loss_blind[:6]))
if len(eps_flip) > EPS_FLIP_WARN_AT:
    warn("قلب حكم تغطية التوزيع في %d سهماً (فوق عتبة %d) — انحدار جودة مصدر أو "
         "تغيّر اصطلاح eps؛ راجع §8-ش" % (len(eps_flip), EPS_FLIP_WARN_AT))
if has_scores and (sh_n < N * 0.8 or ni_n < N * 0.8):
    warn("🚨 صارخ: مرجع eps المستقل انهار (sharesOutstanding %d، netIncome %d من %d) — "
         "وسم تعارض أساس الربح في الواجهة يصمت بلا ضجيج" % (sh_n, ni_n, N))

print("\n" + "=" * 58)
if W:
    print("⚠️ إنذارات: %d" % len(W))
    for w in W:
        print("   • %s" % w)
else:
    print("✅ لا إنذارات")
print("=" * 58)
sys.exit(0)
