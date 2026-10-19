#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار حارس «الفترة الجزئية» بصيغته البسيطة (partial_period_guard في
scripts/fetch-inputs-sahmk.py) على أرقام حقيقية من جلب 19-10 — بلا شبكة.
يحمل حالات رفض الناقد 19-10: السابق الملوَّث، وB لا يُبقي، والوسم القديم، وM بالإشارة،
وS ليس مؤكِّداً. الاستعمال: python3 tests/test_partial_period.py"""
import copy, importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("f", os.path.join(HERE, "..", "scripts", "fetch-inputs-sahmk.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

fails = 0


def check(label, ok):
    global fails
    print(("✅ " if ok else "❌ ") + label)
    fails += 0 if ok else 1


def run(industry, new, prev, eps, shares, pm_fresh, today="2026-10-19"):
    st = {"industry": industry, "financials": copy.deepcopy(new), "guardRejected": []}
    g = m.partial_period_guard(st, copy.deepcopy(prev), eps, shares, pm_fresh, today)
    return g, st


def F(**kw):
    d = {"ratiosBasis": {"returnOnEquity": "statements", "returnOnAssets": "statements"}}
    d.update(kw)
    return d


# 1321 الشرقية للأنابيب: إيراد 364م «سنة كاملة» مقابل 722م (R=0.505)، E=0.149
P1321 = F(revenue=364418913.0, revenuePrev=721752576.0, netIncome=71244701.0, netIncomePrev=179556936.0,
          equity=1134446848.0, profitMargins=19.6, reportDate="2025-03-31", fiscalYear=2025,
          returnOnEquity=6.3, returnOnAssets=4.35, ocfLiabilities=0.5831, revenueGrowth=-49.5)
OLD_HEALTHY = F(netIncome=382123608.0, reportDate="2025-12-31", fiscalYear=2025, returnOnEquity=33.7,
                returnOnAssets=23.41, ocfLiabilities=0.4774, revenueGrowth=18.8)
g, st = run("Steel", P1321, OLD_HEALTHY, 15.22, 31500000, True)
f = st["financials"]
check("1321 ⇒ A بمؤكِّد E (مستقل عن قائمة الدخل)", g == "A" and f["periodSuspect"]["confirmers"] == ["E"])
check("1321 ⇒ الحقول الأربعة None موسومة — بلا إبقاء حتى مع سابق سليم",
      all(f[k] is None and f["ratiosBasis"][k] == m.PP_TAG for k in m.PP_FIELDS))
check("1321 ⇒ القيم المرفوضة في guardRejected بسببها",
      sorted(r["field"] for r in st["guardRejected"]) == sorted(m.PP_FIELDS)
      and all("فترة جزئية" in r["reason"] for r in st["guardRejected"]))
check("1321 ⇒ الهامش لا يُمسّ", f["profitMargins"] == 19.6)
# سيناريو الإنتاج (ختم 19-10، بند 1): السابق ملوَّث بالأرقام الجزئية نفسها ⇒ النتيجة نفسها
g2, st2 = run("Steel", P1321, P1321, 15.22, 31500000, True)
check("1321 بسابقٍ ملوَّث (ما على الخادم) ⇒ النتيجة نفسها، فلا اعتماد على الذاكرة",
      g2 == "A" and st2["financials"] == f)

# B لا يُبقي شيئاً (ختم 19-10، بند 2): 6050 انهيار حقيقي، وسابقه سليم نموه +22%
P6050 = F(revenue=4077794.0, revenuePrev=19042570.0, netIncome=-25352027.0, netIncomePrev=-40995299.0,
          equity=50287273.0, profitMargins=-836.9, reportDate="2025-12-31", fiscalYear=2025,
          returnOnEquity=-50.4, returnOnAssets=-17.63, ocfLiabilities=0.1364, revenueGrowth=-78.6)
g, st = run(None, P6050, F(revenueGrowth=22.0, netIncome=1.0), -7.02, 6700000, False)
check("6050 ⇒ B: النمو None (لا +22% من السابق) وROE كما هو",
      g == "B" and st["financials"]["revenueGrowth"] is None and st["financials"]["returnOnEquity"] == -50.4
      and st["financials"]["ratiosBasis"]["revenueGrowth"] == m.PP_TAG)

# الوسم القديم لا يبقى (ختم 19-10، بند 3): A ثم سليم ⇒ تُمسح وسوم suspect-period والأوسام المؤقتة
P_OK = F(revenue=500.0e6, revenuePrev=450.0e6, netIncome=60.0e6, netIncomePrev=50.0e6, equity=600.0e6,
         reportDate="2025-12-31", fiscalYear=2025, returnOnEquity=10.0, returnOnAssets=5.0,
         ocfLiabilities=0.3, revenueGrowth=11.1)
dirty = copy.deepcopy(P_OK)
dirty["ratiosBasis"].update({"ocfLiabilities": m.PP_TAG, "revenueGrowth": m.PP_TAG})
dirty["periodSuspect"] = {"grade": "A"}
g, st = run("Steel", dirty, {}, 0.12, 500e6, False)
fb = st["financials"]["ratiosBasis"]
check("سهم عاد سليماً ⇒ لا حكم، وتُمسح وسوم suspect-period وperiodSuspect، والقيم الطازجة باقية",
      g is None and "periodSuspect" not in st["financials"] and m.PP_TAG not in fb.values()
      and st["financials"]["revenueGrowth"] == 11.1 and fb["returnOnEquity"] == "statements")

# فشل /financials (ختم 19-10، بند 5): الحارس يعمل على السجل المخزَّن — ROE أعاد حسابه
# apply_computed_ratios من صافي الربح الجزئي المخزَّن (6.3) فيُفرَّغ من جديد
stored = copy.deepcopy(f)
stored["returnOnEquity"], stored["ratiosBasis"]["returnOnEquity"] = 6.3, "statements"
g, st = run("Steel", stored, stored, 15.22, 31500000, False)
check("فشل /financials ⇒ الحارس على المخزَّن يُفرغ ROE المعاد حسابه",
      g == "A" and st["financials"]["returnOnEquity"] is None)

# M يشترط اتفاق الإشارة (ختم 19-10، بند 6): 2030 — هامش موروث +49.4% مع خسارة
P2030 = F(revenue=600000.0, revenuePrev=1372000.0, netIncome=-60.0e6, netIncomePrev=-40.0e6,
          equity=280.0e6, profitMargins=49.4, reportDate="2025-12-31", fiscalYear=2025,
          returnOnEquity=-21.2, returnOnAssets=-19.73, revenueGrowth=-56.3)
g, st = run(None, P2030, {}, None, None, True)
check("2030 هامش معاكس للإشارة ⇒ M لا يُحسب، فـB لا A", g == "B" and "M" not in st["financials"]["periodSuspect"]["signals"])
g, st = run(None, dict(P2030, profitMargins=-2.0), {}, None, None, True)
check("الأرقام نفسها بهامش متسق الإشارة ⇒ M يؤكد (A)", g == "A" and "M" in st["financials"]["periodSuspect"]["confirmers"])

# S ليس مؤكِّداً (ختم 19-10، بند 7): انهيار بهامش ثابت (S = 1.0) بلا E ولا M ⇒ B
P_HALF = F(revenue=250.0e6, revenuePrev=1000.0e6, netIncome=25.0e6, netIncomePrev=100.0e6, equity=900.0e6,
           reportDate="2025-12-31", fiscalYear=2025, returnOnEquity=2.8, returnOnAssets=1.2,
           ocfLiabilities=0.2, revenueGrowth=-75.0)
g, st = run(None, P_HALF, {}, None, None, False)
check("تقلّص بهامش ثابت (S=1.0) وحده ⇒ B: ROE كما هو، والنمو وحده None",
      g == "B" and st["financials"]["returnOnEquity"] == 2.8 and st["financials"]["revenueGrowth"] is None)

# 1304 اليمامة: سلسلة متسقة (477 ← 426) ⇒ مراقبة بلا مساس
P1304 = F(revenue=477453297.0, revenuePrev=425680503.0, netIncome=15372709.0, netIncomePrev=6446940.0,
          equity=621824559.0, profitMargins=3.2, reportDate="2025-09-30", fiscalYear=2025,
          returnOnEquity=2.5, returnOnAssets=0.87, ocfLiabilities=-0.0017, revenueGrowth=12.2)
g, st = run("Steel", P1304, {"netIncome": 59687481.0, "reportDate": "2025-12-31", "fiscalYear": 2025},
            2.56, 50800000, True)
w = st["financials"].get("periodWatch") or {}
check("1304 ⇒ مراقبة W بسببين (E وتغيّر reportDate)، والأرقام كما هي",
      g is None and len(w.get("reasons", [])) == 2 and st["financials"]["returnOnEquity"] == 2.5
      and not st["guardRejected"])
# مراقبة «أقدم من 15 شهراً» وحدها
g, st = run("Steel", dict(P_OK, reportDate="2025-03-31"), {}, None, None, False)
check("reportDate أقدم من 15 شهراً ⇒ مراقبة بلا مساس",
      g is None and "أقدم من 15 شهراً" in " ".join(st["financials"]["periodWatch"]["reasons"]))

# 8311 تأمين: E وحده ⇒ التأمين يشترط مؤكِّدَين فيبقى B
P8311 = F(revenue=32997000.0, revenuePrev=60214000.0, netIncome=-6699000.0, netIncomePrev=-26762000.0,
          equity=156550000.0, profitMargins=-20.3, reportDate="2025-12-31", fiscalYear=2025,
          returnOnEquity=-4.3, returnOnAssets=-2.91, ocfLiabilities=-0.5199, revenueGrowth=-45.2)
g, st = run("Insurance - Reinsurance", P8311, P8311, -1.43, 23000000, False)
check("8311 تأمين بمؤكِّد واحد ⇒ B لا A", g == "B" and st["financials"]["returnOnEquity"] == -4.3)
g, st = run("Steel", P8311, P8311, -1.43, 23000000, False)
check("الأرقام نفسها لغير التأمين ⇒ A (فالفرق من اشتراط المؤكِّدَين وحده)", g == "A")

# E: أرضية المقام واشتراط الإشارة
g, st = run("Steel", P1321, {}, 15.22 * -1, 31500000, False)
check("E بإشارة معاكسة ⇒ لا يُحسب، فـB", g == "B" and "E" not in st["financials"]["periodSuspect"]["signals"])
g, st = run("Steel", dict(P1321, netIncome=1.0e6), {}, 0.01, 31500000, False)
check("E بمقامٍ دون 5م ⇒ لا يُحسب", "E" not in (st["financials"].get("periodSuspect") or {}).get("signals", {}))

# إيراد غائب ⇒ الحارس لا يعمل
g, st = run(None, {"netIncome": 1.0, "returnOnEquity": 5.0}, {}, None, None, False)
check("إيراد غائب ⇒ لا حكم ولا مساس", g is None and st["financials"]["returnOnEquity"] == 5.0)

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
