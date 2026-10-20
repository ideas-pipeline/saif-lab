#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§8-ل (قرار المالك 20-10، criteria v3.2): أساس الاتجاه عائدٌ كلي محلي (tr_local_series) بدل
عمود adjusted المختلط عند المزوّد (معدّل للتوزيعات قبل وصلة 2023-11-27 وسعري بعدها). سلاسل
اصطناعية حتمية — بلا شبكة. الاستعمال: python3 tests/test_adj_basis.py"""
import collections, contextlib, copy, importlib.util, io, os, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("f", os.path.join(HERE, "..", "scripts", "fetch-inputs-sahmk.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.time.sleep = lambda s: None

fails = 0


def check(label, ok):
    global fails
    print(("✅ " if ok else "❌ ") + label)
    fails += 0 if ok else 1


def days(start, n):
    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


TC = m.TR_TC
# سلسلة تعبر الحد: 60 يوماً قبل TC و60 بعده، إغلاق ثابت 10
D = days("2023-08-24", 120)
assert D[60] == TC


def flat(adj_ratio_pre=1.0, seam=None):
    """close = 10 دائماً؛ adjusted = 10 × نسبة المزوّد قبل seam (ثم = close)."""
    rows = []
    for d in D:
        a = 10.0 * (adj_ratio_pre if (seam and d < seam) else 1.0)
        rows.append([d, 10.0, a, 10.1, 9.9, 1000])
    return rows


# 1) خليط المزوّد: معدّل 0.97 حتى الوصلة ثم = close ⇒ السلسلة على أساس واحد (لا قفزة عند الوصلة)
R = flat(0.97, "2023-11-27")
pairs, log = m.tr_local_series(R, [], [])
vals = [v for _, v in pairs]
check("خليط المزوّد (0.97 قبل الوصلة، 1.0 بعدها) ⇒ أساس واحد بلا قفزة: الكل 10",
      all(abs(v - 10.0) < 1e-9 for v in vals) and not log)
rows_adj_col = [r[2] for r in R]
check("وعمود المزوّد نفسه فيه القفزة (الشاهد على المشكلة)",
      abs(rows_adj_col[0] / rows_adj_col[-1] - 0.97) < 1e-9)

# 2) توزيع محلي بعد الحد: D=0.5 بأحقية يوم i، هبوط الإغلاق في الجلسة التالية ⇒ لا هبوط في السلسلة
R2 = flat()
ie = 80
for r in R2[ie + 1:]:
    r[1] = r[2] = 9.5
ev = [{"date": D[ie], "amount": 0.5}]
pairs2, log2 = m.tr_local_series(R2, ev, [])
v2 = [v for _, v in pairs2]
check("توزيع 0.5 على 10 ⇒ ما حتى الأحقية × 0.95، ولا هبوط يوم الاستبعاد",
      abs(v2[ie] - 9.5) < 1e-9 and abs(v2[ie + 1] - 9.5) < 1e-9 and abs(v2[0] - 9.5) < 1e-9 and not log2)
check("tr_local_series نقية: الصفوف كما هي", R2[0][1] == 10.0 and R2[-1][1] == 9.5)
# التوزيع قبل الحد لا يُحسب محلياً (عامل المزوّد يغطيه)
pairs3, _ = m.tr_local_series(flat(), [{"date": D[10], "amount": 0.5}], [])
check("توزيع قبل الحد لا يُحسب محلياً", all(abs(v - 10.0) < 1e-9 for _, v in pairs3))
# لا جلسة بعد الأحقية ⇒ لا عامل
pairs4, _ = m.tr_local_series(flat(), [{"date": D[-1], "amount": 0.5}], [])
check("أحقية في آخر جلسة (لا استبعاد بعد) ⇒ لا عامل", all(abs(v - 10.0) < 1e-9 for _, v in pairs4))

# 3) توزيع قبل منحة مطبَّقة (eventDate بعده) ⇒ على أساس السهم الحالي (×f)
caps = [{"date": "2023-11-27", "eventDate": D[100], "factor": 0.5}]
pairs5, _ = m.tr_local_series(R2, ev, caps)
check("توزيع اسمي 0.5 قبل منحة 1:1 (eventDate بعده) ⇒ y = 0.25/10 = 2.5%",
      abs([v for _, v in pairs5][0] - 10.0 * 0.975) < 1e-9)

# 4) الحراس
R6 = flat()
for r in R6[ie + 1:]:
    r[1] = r[2] = 7.0
_, log6 = m.tr_local_series(R6, [{"date": D[ie], "amount": 3.0}], [])
check("عائد ≥ 25% ⇒ مرفوض بسجل", len(log6) == 1 and "مرفوض" in log6[0][2])
_, log7 = m.tr_local_series(flat(), [{"date": D[ie], "amount": 1.5}], [])
check("عائد 15% بلا هبوط مقابل يوم الاستبعاد ⇒ مرفوض (مبلغ اسمي لا يوافق السعر)",
      len(log7) == 1 and "لا يوافق" in log7[0][2])
R8 = flat()
for r in R8[ie + 1:]:
    r[1] = r[2] = 8.5
p8, log8 = m.tr_local_series(R8, [{"date": D[ie], "amount": 1.5}], [])
check("عائد 15% بهبوط مقابل 15% ⇒ مقبول", not log8 and abs(p8[0][1] - 8.5) < 1e-9)
# خطوة مزوّد قبل الحد: هبوط 26% في adjusted وclose متصل (4322) ⇒ مرفوضة
R9 = flat()
for r in R9[:20]:
    r[2] = 7.4
p9, log9 = m.tr_local_series(R9, [], [])
check("خطوة مزوّد 26% بلا هبوط مقابل في close ⇒ مرفوضة، والسلسلة بلا قفزة",
      any("بلا هبوط مقابل" in x[2] for x in log9) and all(abs(v - 10.0) < 1e-9 for _, v in p9))
R10 = flat()
for r in R10[:20]:
    r[2] = 10.5
_, log10 = m.tr_local_series(R10, [], [])
check("خطوة مزوّد صاعدة > 2% ⇒ مرفوضة", any("صاعدة" in x[2] for x in log10))
# خطوة مزوّد توزيعية حقيقية قبل الحد (هبوط مقابل) ⇒ مقبولة
R11 = flat()
for r in R11[:20]:
    r[2] = 9.7
for r in R11[20:]:
    r[1] = 9.7
for r in R11[20:]:
    r[2] = r[1]
p11, log11 = m.tr_local_series(R11, [], [])
check("خطوة مزوّد 3% بهبوط مقابل في close ⇒ مقبولة: ما قبلها × 0.97",
      not log11 and abs(p11[0][1] - 9.7) < 1e-9 and abs(p11[25][1] - 9.7) < 1e-9)


# 5) المسار الكامل: weeklyTechnical.basis، والاتجاه عائد كلي، وسلاسل الرسم سعرية (ختم §8-ل، شرط 1)
DL = days("2023-08-24", 300)
RL = [[d, 10.0, 10.0, 10.1, 9.9, 1000] for d in DL]
il = 250
for r in RL[il + 1:]:
    r[1] = r[2] = 9.5
evL = [{"date": DL[il], "amount": 0.5}]
T0 = {"3m": 0, "6m": 0, "12_1": 0}
st = {"symbol": "X", "dividendEvents": evL}
m._derive_daily(st, RL, [], T0, "s", collections.defaultdict(int))
st_raw = {"symbol": "X"}
m._derive_daily(st_raw, RL, [], T0, "s", collections.defaultdict(int))
check("weeklyTechnical.basis = tr-local-v1", st["weeklyTechnical"].get("basis") == "tr-local-v1")
check("SMA200D من العائد الكلي: 9.5 بالتوزيع (لا هبوط وهمي) مقابل متوسط أعلى بدونه",
      st["dailyExtra"]["sma200d"] == 9.5 and st_raw["dailyExtra"]["sma200d"] > 9.5)
check("وسلاسل الرسم w52 سعرية في الحالتين (أول أسبوع 10، لا 9.5)",
      st["series"]["w52"]["p"][0] == 10.0 and st_raw["series"]["w52"]["p"][0] == 10.0)
# أحقية حلّت ولم تصل dividendEvents بعد (أسبوعية) ⇒ من المفكرة اليومية (شرط 3)
st_u = {"symbol": "X"}
m._derive_daily(st_u, RL, [], T0, "s", collections.defaultdict(int), [{"date": DL[il], "amount": 0.5}])
check("أحقية من upcomingDividends (≤ اليوم) تدخل الاتجاه قبل الجلب الأسبوعي", st_u["dailyExtra"]["sma200d"] == 9.5)
st_u2 = {"symbol": "X", "dividendEvents": evL}
m._derive_daily(st_u2, RL, [], T0, "s", collections.defaultdict(int), [{"date": DL[il], "amount": 0.9}])
check("والمخزَّن يغلب المفكرة عند تطابق التاريخ (لا ازدواج)", st_u2["dailyExtra"]["sma200d"] == 9.5)
# التوصيل: _derive_daily يمرّر capActions (eventDate) إلى العائد الكلي
st_k = {"symbol": "X", "dividendEvents": evL,
        "capActions": [{"date": "2023-11-27", "eventDate": DL[-5], "factor": 0.5}]}
m._derive_daily(st_k, RL, [], T0, "s", collections.defaultdict(int))
check("_derive_daily يمرّر capActions: توزيع قبل منحة 1:1 ⇒ y = 2.5% لا 5%",
      st_k["dailyExtra"]["sma200d"] > st["dailyExtra"]["sma200d"])
# المسار اليومي الكامل يمرّر المفكرة (fetch_daily_and_derive ← upcoming)
import shutil, tempfile
tmpd = tempfile.mkdtemp()
try:
    cdir = os.path.join(tmpd, "candles")
    os.makedirs(cdir)
    m.save_candles(cdir, "X", RL)
    stF = {"symbol": "X"}

    class Api:
        def get(self, path, **k):
            return {"data": []}, None
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        m.fetch_daily_and_derive(Api(), [stF], collections.defaultdict(int), cdir, T0, "s", DL[-1],
                                 [{"sym": "X", "eligDate": DL[il], "value": 0.5},
                                  {"sym": "X", "eligDate": "2099-01-01", "value": 9.0}])
    check("fetch_daily_and_derive: المفكرة اليومية (≤ اليوم فقط) تصل الاتجاه، وسطر 🧾 يعدّها",
          stF["dailyExtra"]["sma200d"] == 9.5 and "أحقيات من المفكرة اليومية 1" in buf.getvalue())
finally:
    shutil.rmtree(tmpd)

# 5ب) حدود وحراس (طفرات الختم الناجية)
pb, _ = m.tr_local_series(R2, [{"date": TC, "amount": 0.5}], [])
check("أحقية على الحد TC نفسه تُحسب محلياً (e < tc لا e ≤ tc)", abs(pb[0][1] - 10.0 * 0.95) < 1e-9)
Ry = flat()
for r in Ry[ie + 1:]:
    r[1] = r[2] = 7.5
_, logy = m.tr_local_series(Ry, [{"date": D[ie], "amount": 2.5}], [])
check("عائد 25% بالضبط ⇒ مرفوض (≥ لا >)", len(logy) == 1)
Rd = flat()
for r in Rd[ie + 1:]:
    r[1] = r[2] = 9.4   # هبوط 6% مقابل عائد 15%: أقل من نصفه ⇒ مرفوض؛ و0.2y كانت ستقبله
    pass
_, logd = m.tr_local_series(Rd, [{"date": D[ie], "amount": 1.5}], [])
check("عائد 15% بهبوط 6% (< نصفه، > خُمسه) ⇒ مرفوض", len(logd) == 1)
# ic = آخر صف قبل TC: صف TC نفسه لا يدخل التطبيع
Ric = flat()
Ric[60][2] = 9.0   # صف TC: عامل مزوّد شاذ — لا أثر له لأن التطبيع على الصف 59
pic, _ = m.tr_local_series(Ric, [], [])
check("التطبيع على آخر صف قبل TC (صف TC نفسه خارج عامل المزوّد)", all(abs(v - 10.0) < 1e-9 for _, v in pic))
# الجسر فوق adjusted غائب: الخطوة تُقاس بين صفين صالحين متباعدين
Rn = flat()
for r in Rn[:20]:
    r[2] = 9.7
for r in Rn[20:]:
    r[1] = r[2] = 9.7
Rn[25][2] = None
pn, _ = m.tr_local_series(Rn, [], [])
check("adjusted غائب في صف ⇒ يُعبر (nxt يبقى آخر صالح) فتُقاس الخطوة 3% صحيحة",
      abs(pn[0][1] - 9.7) < 1e-9)
# انحراف موثّق عن مرجع المحلل: p(ic) غائب ⇒ التطبيع على أول p صالح تحته (لا إلغاء عامل المزوّد كله)
Rp = flat()
for r in Rp[:20]:
    r[2] = 9.7
for r in Rp[20:]:
    r[1] = r[2] = 9.7
Rp[59][2] = None
pp, _ = m.tr_local_series(Rp, [], [])
check("p(ic) غائب ⇒ عامل المزوّد قبل الحد يبقى (الخطوة 3% تُقاس)", abs(pp[0][1] - 9.7) < 1e-9)


# 6) do_dividends: الحد الأدنى للأحقيات ثابت عند TR_TC (لا قصّ على 1095 يوماً)
class LateClock(m.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2027, 3, 1, 12, 0, tzinfo=tz)


class DivApi:
    def get(self, path, **k):
        if path.startswith("/dividends/"):
            return {"history": [{"eligibility_date": "2023-10-31", "value": 0.4},
                                {"eligibility_date": "2023-10-20", "value": 0.3}]}, None
        if path.startswith("/analytics/ratios/"):
            return {"ratios": {"roe": 10.0, "roa": 1.0, "net_margin": 20.0, "debt_to_equity": 0.1}}, None
        return None, "HTTP 500"


orig = m.datetime
m.datetime = LateClock
try:
    stx = {"symbol": "1830", "sector": "Industrials", "industry": "x", "financials": {}, "guardRejected": [],
           "_prevFinancials": {}}
    with contextlib.redirect_stdout(io.StringIO()):
        m.fetch_fundamentals(DivApi(), {"equitySource": {"choice": "derived"}, "deScaleDecision": {"scale": "ratio×100"}},
                             [stx], collections.defaultdict(int), "2027-03-01", full_universe=False)
finally:
    m.datetime = orig
check("بعد 1095 يوماً من 2023-10-31 يبقى توزيعه (الحد TR_TC)، وما قبل الحد يسقط",
      stx.get("dividendEvents") == [{"date": "2023-10-31", "amount": 0.4}])

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
