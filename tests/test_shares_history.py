#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""المرحلة 1 من تعديل المنح (قرار المالك 20-10): تخزين عدد الأسهم وأحقيات التوزيعات.
يختبر update_shares_history مباشرة، ومسار fetch_fundamentals كاملاً بمزوّد وهمي
(أرقام 1030: 1.25 مليار سهم ثم 1.5 مليار بعد منحة سهم لكل 5) — بلا شبكة.
الاستعمال: python3 tests/test_shares_history.py"""
import collections, copy, importlib.util, os, sys

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


# ── update_shares_history ──
st = {}
m.update_shares_history(st, 1250000000, "2026-09-10")
m.update_shares_history(st, 1250000000, "2026-09-17")
check("القيمة نفسها ⇒ مُدخَل واحد يتقدّم lastSeen (لا تضخّم أسبوعي)",
      st["sharesHistory"] == [{"date": "2026-09-10", "lastSeen": "2026-09-17", "shares": 1250000000}])
m.update_shares_history(st, 1500000000, "2026-10-22")
h = st["sharesHistory"]
check("قيمة جديدة ⇒ مُدخَل ثانٍ، والتغيّر محصور بين 09-17 و10-22، وq = 5/6",
      len(h) == 2 and h[0]["lastSeen"] == "2026-09-17" and h[1]["date"] == "2026-10-22"
      and abs(h[0]["shares"] / h[1]["shares"] - 5 / 6) < 1e-9)
before = copy.deepcopy(st)
for bad in (None, 0, -5, "1500000000", True):
    m.update_shares_history(st, bad, "2026-10-29")
check("قيمة غائبة أو غير موجبة أو غير رقمية ⇒ لا تُكتب ولا تمسح السجل", st == before)
st2 = {}
for i in range(m.SHARES_HIST_MAX + 5):
    m.update_shares_history(st2, 1000 + i, "2026-01-%02d" % (i + 1))
check("السجل محدود بـ%d تغيّراً (الأحدث)" % m.SHARES_HIST_MAX,
      len(st2["sharesHistory"]) == m.SHARES_HIST_MAX and st2["sharesHistory"][-1]["shares"] == 1000 + m.SHARES_HIST_MAX + 4)


# ── المسار الكامل بمزوّد وهمي ──
class Api:
    def __init__(self, shares, divs, company_ok=True):
        self.shares, self.divs, self.company_ok = shares, divs, company_ok

    def get(self, path, **k):
        if path.startswith("/analytics/ratios/"):
            return {"ratios": {"roe": 10.8, "roa": 1.41, "net_margin": 25.1, "debt_to_equity": 0.13}}, None
        if path.startswith("/financials/"):
            return None, "HTTP 500"
        if path.startswith("/company/"):
            if not self.company_ok:
                return None, "HTTP 500"
            return {"fundamentals": {"eps_ttm": 2.33, "book_value": 11.78, "shares_outstanding": self.shares}}, None
        if path.startswith("/dividends/"):
            return {"history": self.divs}, None
        return None, "x"


def run(st, api, today):
    st = copy.deepcopy(st)
    st["_prevFinancials"] = dict(st.get("financials") or {})
    st["guardRejected"] = []
    data = {"equitySource": {"choice": "derived"}, "deScaleDecision": {"scale": "ratio×100"}}
    m.fetch_fundamentals(api, data, [st], collections.defaultdict(int), today, full_universe=False)
    return st


base = {"symbol": "1030", "name": "البنك السعودي للاستثمار", "sector": "Financials",
        "industry": "Banks - Regional", "financials": {"netIncome": 2431485000.0, "equity": 22433472000.0,
                                                       "totalAssets": 172720276000.0}}
divs = [{"eligibility_date": "2026-06-30", "value": 0.35}, {"eligibility_date": "2025-12-31", "value": 0.35},
        {"eligibility_date": "2022-01-01", "value": 0.2}, {"eligibility_date": "2027-01-01", "value": 0.4},
        {"eligibility_date": "2026-06-30", "value": 0.35}]
s1 = run(base, Api(1250000000, divs), "2026-09-17")
check("الجلب يكتب sharesHistory من /company", s1.get("sharesHistory") == [
    {"date": "2026-09-17", "lastSeen": "2026-09-17", "shares": 1250000000}])
check("الجلب يكتب dividendEvents: آخر 3 سنوات، بلا مستقبل ولا تكرار، مرتّبة",
      s1.get("dividendEvents") == [{"date": "2025-12-31", "amount": 0.35}, {"date": "2026-06-30", "amount": 0.35}])
s2 = run(s1, Api(1500000000, divs), "2026-10-22")
check("جلب بعد المنحة ⇒ مُدخَل ثانٍ بـ1.5 مليار", [h["shares"] for h in s2["sharesHistory"]] == [1250000000, 1500000000])
s3 = run(s2, Api(None, divs, company_ok=False), "2026-10-29")
check("فشل /company ⇒ السجل يبقى كما هو", s3["sharesHistory"] == s2["sharesHistory"])

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
