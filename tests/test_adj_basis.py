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


# 5) المسار الكامل: weeklyTechnical.basis ومصدر SMA200W
st = {"symbol": "X", "dividendEvents": ev}
m._derive_daily(st, R2, [], {"3m": 0, "6m": 0, "12_1": 0}, "s", collections.defaultdict(int))
check("weeklyTechnical.basis = tr-local-v1", st["weeklyTechnical"].get("basis") == "tr-local-v1")
st_raw = {"symbol": "X"}
m._derive_daily(st_raw, R2, [], {"3m": 0, "6m": 0, "12_1": 0}, "s", collections.defaultdict(int))
check("الأسبوعي (سلسلة w52) يقرأ العائد الكلي: أول أسبوع 9.5 بالتوزيع و10 بدونه",
      st["series"]["w52"]["p"][0] == 9.5 and st_raw["series"]["w52"]["p"][0] == 10.0)


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
