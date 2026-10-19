#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار حارس «الفترة الجزئية» (partial_period_guard في scripts/fetch-inputs-sahmk.py)
على أرقام حقيقية من جلب 19-10 (f7fbc8c) وما قبله (452d3f9) — بلا شبكة.
الاستعمال: python3 tests/test_partial_period.py"""
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


# 1321 الشرقية للأنابيب: إيراد 364م «سنة كاملة» مقابل 722م — المزوّد يسِمه annual و4 أرباع
P1321_NEW = {"revenue": 364418913.0, "revenuePrev": 721752576.0, "netIncome": 71244701.0,
             "netIncomePrev": 179556936.0, "equity": 1134446848.0, "profitMargins": 19.6,
             "reportDate": "2025-03-31", "fiscalYear": 2025, "returnOnEquity": 6.3,
             "returnOnAssets": 4.35, "ocfLiabilities": 0.5831, "revenueGrowth": -49.5,
             "ratiosBasis": {"returnOnEquity": "statements", "returnOnAssets": "statements"}}
P1321_OLD = {"netIncome": 382123608.0, "equity": 1134446848.0, "reportDate": "2025-12-31",
             "fiscalYear": 2025, "returnOnEquity": 33.7, "returnOnAssets": 23.41,
             "ocfLiabilities": 0.4774, "revenueGrowth": 18.8,
             "ratiosBasis": {"returnOnEquity": "statements", "returnOnAssets": "statements"}}
g, st = run("Steel", P1321_NEW, P1321_OLD, 15.22, 31500000, True)
f = st["financials"]
check("1321 ⇒ A بمؤكِّدَي E وS", g == "A" and f["periodSuspect"]["confirmers"] == ["E", "S"])
check("1321 ⇒ آخر قيمة سليمة مُبقاة موسومة (ROE 33.7، النمو 18.8)",
      f["returnOnEquity"] == 33.7 and f["revenueGrowth"] == 18.8
      and f["ratiosBasis"]["returnOnEquity"] == "suspect-period-held")
check("1321 ⇒ القيم المرفوضة في guardRejected بسببها (4 حقول)",
      sorted(r["field"] for r in st["guardRejected"]) == sorted(m.PP_FIELDS)
      and all("فترة جزئية" in r["reason"] for r in st["guardRejected"]))
check("1321 ⇒ الهامش لا يُمسّ", f["profitMargins"] == 19.6)

# الإبقاء يستمر داخل 13 أسبوعاً وينتهي بعدها إلى None
prev2 = copy.deepcopy(f)
g2, st2 = run("Steel", P1321_NEW, prev2, 15.22, 31500000, True, today="2026-11-30")
check("1321 بعد 6 أسابيع ⇒ الإبقاء مستمر من since الأول",
      st2["financials"]["returnOnEquity"] == 33.7 and st2["financials"]["periodSuspect"]["since"] == "2026-10-19")
g3, st3 = run("Steel", P1321_NEW, copy.deepcopy(st2["financials"]), 15.22, 31500000, True, today="2027-01-25")
check("1321 بعد 14 أسبوعاً ⇒ None موسوم (لا إبقاء أبدي)",
      st3["financials"]["returnOnEquity"] is None
      and st3["financials"]["ratiosBasis"]["returnOnEquity"] == "suspect-period")

# 6050 الأسماك: انهيار إيراد حقيقي (R=0.21) — S=2.9 خارج النطاق وE=0.54 ⇒ B: النمو وحده
P6050 = {"revenue": 4077794.0, "revenuePrev": 19042570.0, "netIncome": -25352027.0,
         "netIncomePrev": -40995299.0, "equity": 50287273.0, "profitMargins": -836.9,
         "reportDate": "2025-12-31", "fiscalYear": 2025, "returnOnEquity": -50.4,
         "returnOnAssets": -17.63, "ocfLiabilities": 0.1364, "revenueGrowth": -78.6}
g, st = run(None, P6050, P6050, -7.02, 6700000, False)
check("6050 (انهيار حقيقي) ⇒ B: النمو None وROE كما هو",
      g == "B" and st["financials"]["revenueGrowth"] is None and st["financials"]["returnOnEquity"] == -50.4)

# 1304 اليمامة: سلسلة متسقة (477 ← 426) — تعافٍ لاحق لا فترة جزئية ⇒ مراقبة بلا مساس
P1304_NEW = {"revenue": 477453297.0, "revenuePrev": 425680503.0, "netIncome": 15372709.0,
             "netIncomePrev": 6446940.0, "equity": 621824559.0, "profitMargins": 3.2,
             "reportDate": "2025-09-30", "fiscalYear": 2025, "returnOnEquity": 2.5,
             "returnOnAssets": 0.87, "ocfLiabilities": -0.0017, "revenueGrowth": 12.2}
P1304_OLD = {"netIncome": 59687481.0, "reportDate": "2025-12-31", "fiscalYear": 2025}
g, st = run("Steel", P1304_NEW, P1304_OLD, 2.56, 50800000, True)
check("1304 ⇒ مراقبة W فقط، والأرقام كما هي",
      g is None and "periodWatch" in st["financials"] and st["financials"]["returnOnEquity"] == 2.5
      and not st["guardRejected"])

# 8311 تأمين: R=0.548 وE وحده ⇒ التأمين يشترط مؤكِّدَين فينزل إلى B
P8311 = {"revenue": 32997000.0, "revenuePrev": 60214000.0, "netIncome": -6699000.0,
         "netIncomePrev": -26762000.0, "equity": 156550000.0, "profitMargins": -20.3,
         "reportDate": "2025-12-31", "fiscalYear": 2025, "returnOnEquity": -4.3,
         "returnOnAssets": -2.91, "ocfLiabilities": -0.5199, "revenueGrowth": -45.2}
g, st = run("Insurance - Reinsurance", P8311, P8311, -1.43, 23000000, True)
check("8311 تأمين بمؤكِّد واحد ⇒ B لا A", g == "B" and st["financials"]["returnOnEquity"] == -4.3)
g, st = run("Steel", P8311, P8311, -1.43, 23000000, True)
check("الأرقام نفسها لغير التأمين ⇒ A (فالفرق من اشتراط المؤكِّدَين وحده)", g == "A")

# 2222 أرامكو: سنة سليمة ⇒ لا شيء، والحقول المؤقتة تُمسح
P2222 = {"revenue": 1671204000000.0, "revenuePrev": 1801674000000.0, "netIncome": 348042000000.0,
         "netIncomePrev": 393891000000.0, "equity": 1721744000000.0, "profitMargins": 20.8,
         "reportDate": "2025-12-31", "fiscalYear": 2025, "returnOnEquity": 20.2,
         "returnOnAssets": 13.64, "ocfLiabilities": 0.6153, "revenueGrowth": -7.2,
         "periodSuspect": {"grade": "A"}, "periodWatch": {"reasons": ["قديم"]}}
g, st = run("Oil & Gas Integrated", P2222, P2222, 1.69, 242000000000, True)
check("2222 سليمة ⇒ لا حكم، وأوسام التشغيلة السابقة تُمسح",
      g is None and "periodSuspect" not in st["financials"] and "periodWatch" not in st["financials"]
      and not st["guardRejected"])

# إيراد غائب (البنوك وما شابه) ⇒ الحارس لا يعمل
g, st = run(None, {"netIncome": 1.0, "returnOnEquity": 5.0}, {}, None, None, False)
check("إيراد غائب ⇒ لا حكم ولا مساس", g is None and st["financials"]["returnOnEquity"] == 5.0)

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
