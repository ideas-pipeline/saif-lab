#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§8-م (قرار المالك 20-10، criteria v3.3): حراس بيانات المزوّد — ربحية السهم والقيمة الدفترية
للسوق كله، وأساس إيراد البنوك. بأرقام حقيقية من جلب 20-10 وقوائم البنك السعودي للاستثمار —
بلا شبكة وبساعة ثابتة. الاستعمال: python3 tests/test_provider_guards.py"""
import collections, contextlib, copy, importlib.util, io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("f", os.path.join(ROOT, "scripts", "fetch-inputs-sahmk.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.time.sleep = lambda s: None
spec2 = importlib.util.spec_from_file_location("se", os.path.join(ROOT, "scripts", "scoring-engine.py"))
se = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(se)


class FixedClock(m.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 22, 12, 0, tzinfo=tz)


m.datetime = FixedClock
TODAY = "2026-10-20"
fails = 0


def check(label, ok):
    global fails
    print(("✅ " if ok else "❌ ") + label)
    fails += 0 if ok else 1


BANK = {"sector": "Financial Services", "industry": "Banks - Regional"}


def stock(sym, eps=None, bv=None, ni=None, eq=None, shares=None, bank=True, **fin):
    st = dict(BANK) if bank else {"sector": "Industrials", "industry": "Building Products"}
    st.update({"symbol": sym, "guardRejected": [],
               "valuationInputs": {"epsProvider": eps, "bookValueProvider": bv},
               "financials": dict({"netIncome": ni, "equity": eq, "reportDate": "2025-12-31", "fiscalYear": 2025}, **fin)})
    if shares:
        st["sharesHistory"] = [{"date": "2026-10-20", "lastSeen": "2026-10-20", "shares": shares}]
    return st


# ── 1) حارس EPS ──
s1020 = stock("1020", eps=3.05, ni=1505.5e6, eq=12e9, shares=1281.25e6)
r = m.eps_guard(s1020, TODAY)
vi = s1020["valuationInputs"]
check("1020: E = 2.60 > 1.15 ⇒ أُبدل بصافي الربح ÷ العدد (1.175)، والخام في epsProvider وguardRejected",
      r == "replace" and abs(vi["eps"] - 1.175) < 1e-3 and vi["epsBasis"] == "fy-derived" and vi["epsProvider"] == 3.05
      and s1020["guardRejected"][0]["field"] == "eps")
s1030 = stock("1030", eps=2.3348, ni=2431.5e6, eq=22433.5e6, shares=1.5e9)
r = m.eps_guard(s1030, TODAY)
check("1030: E = 1.44 (معامل المنحة مضروب) ⇒ أُبدل بـ1.621", r == "replace" and abs(s1030["valuationInputs"]["eps"] - 1.621) < 1e-3)
s1010 = stock("1010", eps=None, ni=10411e6, eq=60e9, shares=4e9)
r = m.eps_guard(s1010, TODAY)
check("1010: eps فارغ وربح موجب ⇒ مُلئ (2.6028، fy-filled) بلا guardRejected",
      r == "fill" and abs(s1010["valuationInputs"]["eps"] - 2.6028) < 1e-4
      and s1010["valuationInputs"]["epsBasis"] == "fy-filled" and not s1010["guardRejected"])
s_ok = stock("1180", eps=3.10, ni=20e9, eq=150e9, shares=6.0e9)   # E = 0.93
r = m.eps_guard(s_ok, TODAY)
check("بنك سليم (E = 0.93) ⇒ يبقى على المزوّد بلا مساس", r == "keep" and s_ok["valuationInputs"]["eps"] == 3.10
      and s_ok["valuationInputs"]["epsBasis"] == "provider" and "epsCheck" not in s_ok["valuationInputs"])
s_lo = stock("1050", eps=1.0, ni=3e9, eq=40e9, shares=2.5e9)     # E = 0.83 < 0.85
check("بنك E = 0.83 ⇒ مراقبة لا إبدال", m.eps_guard(s_lo, TODAY) == "watch" and s_lo["valuationInputs"]["eps"] == 1.0)
s_mk = stock("4030", eps=1.8, ni=100e6, eq=1e9, shares=100e6, bank=False)   # E = 1.8
check("غير بنك E = 1.8 ⇒ مراقبة لا إبدال (العتبة 2.0)",
      m.eps_guard(s_mk, TODAY) == "watch" and s_mk["valuationInputs"]["eps"] == 1.8)
s_mk2 = stock("4030", eps=2.63, ni=100e6, eq=1e9, shares=100e6, bank=False)  # E = 2.63
check("غير بنك E = 2.63 ⇒ أُبدل", m.eps_guard(s_mk2, TODAY) == "replace" and s_mk2["valuationInputs"]["eps"] == 1.0)
for lbl, mut in (("قائمة جزئية (periodSuspect)", lambda s: s["financials"].update(periodSuspect={"grade": "A"})),
                 ("قائمة متقادمة (> 456 يوماً)", lambda s: s["financials"].update(reportDate="2024-12-31")),
                 ("ربح ضئيل (< 1% من الملكية)", lambda s: s["financials"].update(netIncome=1e8, equity=1e11))):
    x = copy.deepcopy(s1020)
    x["guardRejected"] = []
    mut(x)
    check("التخطي: %s ⇒ لا مساس" % lbl, m.eps_guard(x, TODAY) == "skip" and x["valuationInputs"]["eps"] == 3.05
          and not x["guardRejected"])
x = copy.deepcopy(s1020)
m.eps_guard(x, TODAY)
m.eps_guard(x, TODAY)
check("تشغيلتان متتاليتان ⇒ لا اشتقاق فوق اشتقاق (الخام يبقى epsProvider)",
      abs(x["valuationInputs"]["eps"] - 1.175) < 1e-3 and x["valuationInputs"]["epsProvider"] == 3.05)

# ── 2) حارس القيمة الدفترية ──
s1120 = stock("1120", bv=33.48, ni=24.8e9, eq=142.9e9, shares=6e9)
s1120["capActions"] = [{"date": "2023-11-27", "eventDate": "2026-04-21", "factor": 0.666667, "kind": "bonus"}]
r = m.bv_guard(s1120, TODAY)
check("1120: B = 1.41 ويفسّرها منحة بعد reportDate ⇒ ×2/3 = 22.32 (provider-capadj)",
      r == "replace" and abs(s1120["valuationInputs"]["bookValue"] - 22.32) < 1e-2
      and s1120["valuationInputs"]["bookValueBasis"] == "provider-capadj")
s_bvd = stock("4020", bv=30.0, ni=1e8, eq=1e9, shares=50e6, bank=False)   # B = 1.5 بلا إجراء
r = m.bv_guard(s_bvd, TODAY)
check("بلا إجراء يفسّرها (B = 1.5) ⇒ الملكية ÷ العدد = 20 (fy-derived)",
      r == "replace" and s_bvd["valuationInputs"]["bookValue"] == 20.0 and s_bvd["valuationInputs"]["bookValueBasis"] == "fy-derived")
s_bvk = stock("1030", bv=11.78, ni=2431.5e6, eq=22433.5e6, shares=1.5e9)   # B = 0.788 (بلا صكوك)
check("1030: B = 0.788 (book_value بلا صكوك الشريحة الأولى) ⇒ لا مساس",
      m.bv_guard(s_bvk, TODAY) == "keep" and s_bvk["valuationInputs"]["bookValue"] == 11.78)
s_bvw = stock("X", bv=5.0, ni=1e8, eq=1e9, shares=100e6, bank=False)     # B = 0.5
check("B = 0.5 ⇒ مراقبة bookValueCheck بلا مساس",
      m.bv_guard(s_bvw, TODAY) == "watch" and s_bvw["valuationInputs"]["bookValueCheck"]["B"] == 0.5)

# ── 3) أساس إيراد البنوك ──
s_rev = stock("1030", ni=2431.5e6, eq=22433.5e6, revenue=9692e6, revenuePrev=4178e6, netIncomePrev=1956.6e6,
              profitMargins=25.1, revenueGrowth=132.0, ratiosBasis={"returnOnEquity": "statements"})
r = m.bank_revenue_guard(s_rev, TODAY)
f = s_rev["financials"]
check("1030: هامش 25.1% (سابقه 46.8%) وإيراد ×2.32 ⇒ الهامش والنمو فارغان موسومان",
      r == "reject" and f["profitMargins"] is None and f["revenueGrowth"] is None
      and f["ratiosBasis"]["profitMargins"] == "bank-revenue-basis" and f["revenueBasisSuspect"]["R"] == 2.32
      and f["ratiosBasis"]["returnOnEquity"] == "statements"
      and sorted(g["field"] for g in s_rev["guardRejected"]) == ["profitMargins", "revenueGrowth"])
s_prov = stock("1060", ni=1e9, eq=30e9, revenue=4e9, revenuePrev=3.8e9, netIncomePrev=2e9, profitMargins=25.0)
check("بنك بهامش 25% بلا قفزة إيراد (سنة مخصّصات) ⇒ لا مساس",
      m.bank_revenue_guard(s_prov, TODAY) is None and s_prov["financials"]["profitMargins"] == 25.0)
check("غير البنوك ⇒ لا يعمل", m.bank_revenue_guard(stock("2010", bank=False, revenue=1, revenuePrev=3,
                                                          netIncome=0.1, netIncomePrev=1), TODAY) is None)
s_heal = copy.deepcopy(s_rev)
s_heal["financials"].update(revenue=4.9e9, profitMargins=49.6, revenueGrowth=17.3)
r = m.bank_revenue_guard(s_heal, TODAY)
check("المزوّد صحّح ⇒ الوسم يُمسح والقيم الطازجة باقية",
      r is None and "revenueBasisSuspect" not in s_heal["financials"]
      and "bank-revenue-basis" not in s_heal["financials"]["ratiosBasis"].values()
      and s_heal["financials"]["profitMargins"] == 49.6)


# ── 4) المسار الكامل: fetch_fundamentals ──
class Api:
    def __init__(self, company_ok=True, eps=2.3348, bv=11.78):
        self.company_ok, self.eps, self.bv = company_ok, eps, bv

    def get(self, path, **k):
        if path.startswith("/analytics/ratios/"):
            return {"ratios": {"roe": 10.8, "roa": 1.41, "net_margin": 25.1, "debt_to_equity": 0.13}}, None
        if path.startswith("/company/"):
            if not self.company_ok:
                return None, "HTTP 500"
            return {"fundamentals": {"eps_ttm": self.eps, "book_value": self.bv, "shares_outstanding": 1.5e9}}, None
        if path.startswith("/dividends/"):
            return {"history": []}, None
        return None, "HTTP 500"


base = dict(BANK, symbol="1030", financials={"netIncome": 2431.5e6, "equity": 22433.5e6, "totalAssets": 172720e6,
                                            "reportDate": "2025-12-31", "fiscalYear": 2025},
            liquidityScore={"sharesOutstanding": 1.25e9}, debtHealth={"type": "bank"})
DATA = {"equitySource": {"choice": "derived"}, "deScaleDecision": {"scale": "ratio×100"}}


def run(st, api):
    st = copy.deepcopy(st)
    st["_prevFinancials"] = dict(st.get("financials") or {})
    st["guardRejected"] = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.fetch_fundamentals(api, DATA, [st], collections.defaultdict(int), TODAY, full_universe=False)
    return st, buf.getvalue()


s1, out1 = run(base, Api())
v1 = s1["valuationInputs"]
check("المسار: /company ⇒ epsProvider = 2.3348، وeps مُبدل 1.621، وسطر 🛡️ يعدّه",
      v1["epsProvider"] == 2.3348 and abs(v1["eps"] - 1.621) < 1e-3 and v1["epsBasis"] == "fy-derived"
      and "eps أُبدل 1" in out1)
check("المسار: liquidityScore وdebtHealth حُذفا (حقلان نائمان)", "liquidityScore" not in s1 and "debtHealth" not in s1)
s2, _ = run(s1, Api(company_ok=False))
check("فشل /company ⇒ الخام المخزَّن epsProvider هو المقياس (لا المشتق) فيبقى الإبدال",
      s2["valuationInputs"]["epsProvider"] == 2.3348 and abs(s2["valuationInputs"]["eps"] - 1.621) < 1e-3)
s3, _ = run(s1, Api(eps=1.62))
check("المزوّد صحّح (1.62) ⇒ يعود على أساس المزوّد", s3["valuationInputs"]["eps"] == 1.62
      and s3["valuationInputs"]["epsBasis"] == "provider")
legacy = copy.deepcopy(base)
legacy["valuationInputs"] = {"eps": 3.05, "bookValue": 11.78}   # سجل ما قبل §8-م بلا epsProvider
legacy["sharesHistory"] = [{"date": "2026-10-20", "lastSeen": "2026-10-20", "shares": 1.5e9}]
s4, _ = run(legacy, Api(company_ok=False))
check("أول تشغيلة بعد §8-م مع فشل /company ⇒ eps المخزَّن يُعدّ خاماً (epsProvider = 3.05)",
      s4["valuationInputs"]["epsProvider"] == 3.05 and s4["valuationInputs"]["epsBasis"] == "fy-derived")

# ── 5) المستهلكون ──
st_v = {"currentPrice": 12.0, "valuationInputs": {"eps": 1.621, "epsBasis": "fy-derived", "peSource": 5.0}}
v = se.compute_valuation(st_v, TODAY)
check("compute_valuation: لا peSourceDiffPct حين eps مشتق (لا «توتّر pe» زائف)", "peSourceDiffPct" not in v)
st_v2 = {"currentPrice": 12.0, "valuationInputs": {"eps": 2.0, "peSource": 5.0}}
check("وعلى أساس المزوّد يُحسب كما كان", "peSourceDiffPct" in se.compute_valuation(st_v2, TODAY))
src_l1 = open(os.path.join(ROOT, "scripts", "self-check-L1.py")).read()
check("self-check [6] و[9] يقرآن epsProvider (لا eps المشتق)",
      src_l1.count('vi.get("epsProvider", vi.get("eps"))') == 2)

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
