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
s_mk2 = stock("4030", eps=6.92, ni=2431.3e6, eq=12e9, shares=922.85e6, bank=False)  # E = 2.63 — البحري
check("غير بنك E = 2.63 (البحري: نمو 2026 حقيقي) ⇒ مراقبة لا إبدال (قرار المالك المعدّل)",
      m.eps_guard(s_mk2, TODAY) == "watch" and s_mk2["valuationInputs"]["eps"] == 6.92
      and s_mk2["valuationInputs"]["epsBasis"] == "provider" and not s_mk2["guardRejected"])
s_mk3 = stock("4321", eps=None, ni=100e6, eq=1e9, shares=100e6, bank=False)
check("غير بنك eps فارغ ⇒ لا ملء", m.eps_guard(s_mk3, TODAY) == "skip" and s_mk3["valuationInputs"]["eps"] is None)
s_sh = stock("1213", eps=3.05, ni=1505.5e6, eq=12e9, shares=1281.25e6)
s_sh["valuationInputs"].update(sharesOutstanding=1281.25e6 * 2.52)
check("عدد أسهم مشكوك فيه (sharesHistory يخالف المجمّد بـ> 25%) ⇒ تخطٍّ لا اشتقاق",
      m.eps_guard(s_sh, TODAY) == "skip" and s_sh["valuationInputs"]["eps"] == 3.05)
s_sk = stock("1020", eps=3.05, ni=1505.5e6, eq=12e9, shares=1281.25e6)
s_sk["valuationInputs"].update(sharesOutstanding=1281.25e6 * 0.8, sharesCapFactor=0.8)
check("shares_now: المجمّد ÷ sharesCapFactor يوافق sharesHistory ⇒ يُستعمل", m.shares_now(s_sk) == 1281.25e6)
s_nh = {"valuationInputs": {"sharesOutstanding": 1e9, "sharesCapFactor": 0.5}}
check("shares_now: بلا sharesHistory ⇒ المجمّد ÷ k", m.shares_now(s_nh) == 2e9)
s_neg = stock("1050", eps=1.0, ni=-5e8, eq=40e9, shares=2.5e9)
check("eps موجب وربح السنة سالب ⇒ مراقبة بسبب", m.eps_guard(s_neg, TODAY) == "watch"
      and "سالب" in s_neg["valuationInputs"]["epsCheck"]["why"])
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
s_bvd = stock("1060", bv=30.0, ni=1e9, eq=10e9, shares=500e6)   # بنك B = 1.5 بلا إجراء
r = m.bv_guard(s_bvd, TODAY)
check("بنك بلا إجراء يفسّرها (B = 1.5) ⇒ الملكية ÷ العدد = 20 (fy-derived)",
      r == "replace" and s_bvd["valuationInputs"]["bookValue"] == 20.0 and s_bvd["valuationInputs"]["bookValueBasis"] == "fy-derived")
s_bvn = stock("4020", bv=30.0, ni=1e8, eq=1e9, shares=50e6, bank=False)
check("غير بنك بلا إجراء (B = 1.5) ⇒ مراقبة لا اشتقاق",
      m.bv_guard(s_bvn, TODAY) == "watch" and s_bvn["valuationInputs"]["bookValue"] == 30.0)
s_bvc = stock("8010", bv=30.0, ni=1e8, eq=1e9, shares=50e6, bank=False)
s_bvc["capActions"] = [{"date": "2026-09-03", "factor": 2 / 3, "kind": "bonus/split"}]
check("غير بنك ومنحة تفسّرها (×2/3) ⇒ provider-capadj للسوق كله",
      m.bv_guard(s_bvc, TODAY) == "replace" and s_bvc["valuationInputs"]["bookValueBasis"] == "provider-capadj"
      and s_bvc["guardRejected"][-1].get("guard") == "provider")
s_bvr = stock("8010", bv=30.0, ni=1e8, eq=1e9, shares=50e6, bank=False)
s_bvr["capActions"] = [{"date": "2026-09-03", "factor": 0.8, "kind": "rights"}]
check("حقوق أولوية لا تُعدّ إجراءً يفسّر القيمة الدفترية ⇒ مراقبة", m.bv_guard(s_bvr, TODAY) == "watch")
s_bvl = stock("1060", bv=30.0, ni=1e9, eq=10e9, shares=500e6)
s_bvl["capActions"] = [{"date": "2026-09-03", "factor": 0.2, "kind": "split"}]   # B×f = 0.3 < 0.70
check("معامل يُنزل B تحت 0.70 لا يُقبل تفسيراً ⇒ يُشتق من الملكية",
      m.bv_guard(s_bvl, TODAY) == "replace" and s_bvl["valuationInputs"]["bookValueBasis"] == "fy-derived")
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

# ── 4ب) حارس الإيراد في المسار الكامل (بـ/financials)، والمسار (ب)، وثبات الوسم مع الفراغ ──
def fin_resp(rev25, ni25, rev24, ni24):
    def el(fy, rev, ni):
        return {"is_full_year": True, "fiscal_year": fy, "report_date": "%d-12-31" % fy,
                "total_revenue": rev, "net_income": ni}
    return {"income_statements": [el(2025, rev25, ni25), el(2024, rev24, ni24)],
            "balance_sheets": [{"is_full_year": True, "report_date": "2025-12-31", "total_assets": 172720e6,
                                "total_liabilities": 150286.5e6, "stockholders_equity": 22433.5e6}],
            "cash_flows": []}


class ApiF(Api):
    def __init__(self, fin, net_margin=25.1, ratios_ok=True, **kw):
        super().__init__(**kw)
        self.fin, self.nm, self.ratios_ok = fin, net_margin, ratios_ok

    def get(self, path, **k):
        if path.startswith("/financials/"):
            return self.fin, None
        if path.startswith("/analytics/ratios/"):
            if not self.ratios_ok:
                return None, "HTTP 500"
            return {"ratios": {"roe": 10.8, "roa": 1.41, "net_margin": self.nm, "debt_to_equity": 0.13}}, None
        return super().get(path, **k)


sR, outR = run(base, ApiF(fin_resp(9692e6, 2431.5e6, 4178e6, 1956.6e6)))
fR = sR["financials"]
check("المسار الكامل: /financials بإيراد 1030 المتبدّل ⇒ الهامش والنمو فارغان موسومان، وسطر 🛡️ يعدّه",
      fR.get("profitMargins") is None and fR.get("revenueGrowth") is None and "revenueBasisSuspect" in fR
      and "إيراد بنك مرفوض 1" in outR)
sR2, _ = run(sR, ApiF(fin_resp(4400e6, 2431.5e6, 4178e6, 1956.6e6), net_margin=25.1))
check("(ب) القوائم صُحّحت و/ratios ما زال 25.1 ⇒ الهامش المستهلك يُرفض (لا يعود 25.1 بلا وسم)",
      sR2["financials"].get("profitMargins") is None
      and sR2["financials"]["ratiosBasis"].get("profitMargins") == "bank-revenue-basis")
sR3, _ = run(sR2, ApiF(fin_resp(4400e6, 2431.5e6, 4178e6, 1956.6e6), ratios_ok=False))
check("أسبوع فشل /ratios بعد التصحيح ⇒ الوسم يبقى ما دام الهامش فارغاً (لا فراغ صامت)",
      sR3["financials"].get("profitMargins") is None and "revenueBasisSuspect" in sR3["financials"]
      and sR3["financials"]["ratiosBasis"].get("profitMargins") == "bank-revenue-basis")
sR4, _ = run(sR3, ApiF(fin_resp(4400e6, 2431.5e6, 4178e6, 1956.6e6), net_margin=55.3))
check("والمزوّد صحّح /ratios ⇒ الهامش يعود والوسم يُمسح",
      sR4["financials"].get("profitMargins") == 55.3 and "revenueBasisSuspect" not in sR4["financials"]
      and "bank-revenue-basis" not in (sR4["financials"].get("ratiosBasis") or {}).values())

# ── 4ج) دورة الخام: لا يُستبدل الخام بالمشتق، والمراقبة تُمسح، وحارس الفترة الجزئية يقرأ الخام ──
leg = copy.deepcopy(s1)          # eps مشتق 1.621 والخام 2.3348؛ bookValue كما هو
leg["valuationInputs"]["bookValueProvider"] = 33.48
leg["valuationInputs"]["bookValue"] = 22.32
sL, _ = run(leg, Api(company_ok=False))
check("فشل /company ⇒ bookValueProvider الخام لا يُستبدل بالمشتق (setdefault لا إسناد)",
      sL["valuationInputs"]["bookValueProvider"] == 33.48)
w = stock("1050", eps=1.0, ni=3e9, eq=40e9, shares=2.5e9)
m.eps_guard(w, TODAY)
w["valuationInputs"]["epsProvider"] = 1.2       # صار سليماً (E = 1.0)
m.eps_guard(w, TODAY)
check("epsCheck يُمسح حين تزول المراقبة", "epsCheck" not in w["valuationInputs"])
seen_pp = {}
orig_pp = m.partial_period_guard
m.partial_period_guard = lambda st, prev, eps, shares, pm, today: seen_pp.setdefault("eps", eps)
try:
    nb = copy.deepcopy(base)
    nb.update({"sector": "Industrials", "industry": "Steel"})
    nb["valuationInputs"] = {"eps": 1.0, "epsProvider": 4.4}
    run(nb, Api(company_ok=False))
finally:
    m.partial_period_guard = orig_pp
check("partial_period_guard يتلقى epsProvider الخام (4.4) لا eps المشتق عند فشل /company", seen_pp.get("eps") == 4.4)

# ── 4د) عقد المطابقة واجهة ⟷ L1 على بيانات ما بعد الحراس (ختم §8-م، شرط 2) ──
import json as _json, shutil as _sh, subprocess as _sp, tempfile as _tf
tmp = _tf.mkdtemp()
try:
    os.makedirs(os.path.join(tmp, "scripts"))
    _sh.copy(os.path.join(ROOT, "uat.html"), tmp)
    _sh.copy(os.path.join(ROOT, "scripts", "self-check-L1.py"), os.path.join(tmp, "scripts"))
    D = _json.load(open(os.path.join(ROOT, "stocks-data.json")))
    for st in D["stocks"]:
        vi = st.setdefault("valuationInputs", {})
        vi.setdefault("epsProvider", vi.get("eps"))
        vi.setdefault("bookValueProvider", vi.get("bookValue"))
        st.setdefault("guardRejected", [])
        m.eps_guard(st, TODAY)
        m.bv_guard(st, TODAY)
    _json.dump(D, open(os.path.join(tmp, "stocks-data.json"), "w"), ensure_ascii=False)
    r = _sp.run(["node", os.path.join(HERE, "test_contract.js")], env=dict(os.environ, REPO=tmp),
                capture_output=True, text=True)
    check("test_contract على بيانات ما بعد الحراس ⇒ خروج 0 (جمهور الواجهة = جمهور L1 [9])", r.returncode == 0)
finally:
    _sh.rmtree(tmp)

# ── 4هـ) شروط الختم المتبقية: حالات سلبية للمسارين، ومسح bookValueCheck، والختم، والتجميد، وفصل L1 [3] ──
s_b1 = stock("1080", ni=2e9, eq=30e9, revenue=4e9, revenuePrev=3.8e9, netIncomePrev=1.9e9, profitMargins=65.0)
check("(ب) سلبي: هامش المزوّد 65% داخل النطاق ويخالف القوائم (50%) بـ15 نقطة ⇒ لا رفض (الشرط: خارج النطاق)",
      m.bank_revenue_guard(s_b1, TODAY) is None and s_b1["financials"]["profitMargins"] == 65.0)
s_b2 = stock("1080", ni=1.28e9, eq=30e9, revenue=4e9, revenuePrev=3.8e9, netIncomePrev=1.2e9, profitMargins=25.0)
check("(ب) سلبي: هامش المزوّد 25% خارج النطاق والقوائم 32% (فجوة 7 نقاط ≤ 10) ⇒ لا رفض",
      m.bank_revenue_guard(s_b2, TODAY) is None and s_b2["financials"]["profitMargins"] == 25.0)
s_a1 = stock("1080", ni=1e9, eq=30e9, revenue=4e9, revenuePrev=1.7e9, netIncomePrev=0.34e9,
             profitMargins=25.0, revenueGrowth=135.0)
check("(أ) سلبي: هامش سابقٍ خارج النطاق أيضاً (20%) مع قفزة إيراد ⇒ لا تبدّل أساس، لا رفض",
      m.bank_revenue_guard(s_a1, TODAY) is None and s_a1["financials"]["revenueGrowth"] == 135.0)
s_bc = stock("X", bv=5.0, ni=1e8, eq=1e9, shares=100e6, bank=False)
m.bv_guard(s_bc, TODAY)
s_bc["valuationInputs"]["bookValueProvider"] = 10.0              # B = 1.0
check("bookValueCheck يُمسح حين تزول المراقبة",
      m.bv_guard(s_bc, TODAY) == "keep" and "bookValueCheck" not in s_bc["valuationInputs"])

D0 = copy.deepcopy(DATA)
DATA.pop("providerGuardsSince", None)
_, _ = run(base, Api())
check("fetch_fundamentals يختم data.providerGuardsSince = اليوم (يوم الانتقال)", DATA.get("providerGuardsSince") == TODAY)
DATA["providerGuardsSince"] = "2026-10-01"
run(base, Api())
check("ولا يُعاد الختم بعد أول تشغيلة (setdefault)", DATA["providerGuardsSince"] == "2026-10-01")
DATA.clear(); DATA.update(D0)
sb = copy.deepcopy(base)
sb["sharesHistory"] = [{"date": "2026-10-20", "lastSeen": "2026-10-20", "shares": 1.5e9}]
sb["valuationInputs"] = {"sharesOutstanding": 4e9}
_, outS = run(sb, Api())
check("عدد مشكوك فيه ⇒ السهم يُطبع في سطر 🛡️ (لا تعطيل صامت)", "عدد أسهم مشكوك فيه" in outS and "1030" in outS)

import datetime as _dt
FEED_TODAY = _dt.datetime.now().strftime("%Y-%m-%d")


def run_feed(stocks_data, cfg):
    d = _tf.mkdtemp()
    try:
        sp, cp = os.path.join(d, "s.json"), os.path.join(d, "c.json")
        _json.dump(stocks_data, open(sp, "w"))
        _json.dump(cfg, open(cp, "w"))
        os.makedirs(os.path.join(d, "arch"))
        env = dict(os.environ, STOCKS_JSON=sp, CONFIG_JSON=cp, ARCHIVE_DIR=os.path.join(d, "arch"))
        out = _sp.run(["bash", os.path.join(ROOT, "scripts", "feed-watchlist.sh")], env=env,
                      capture_output=True, text=True).stdout
        return _json.load(open(cp)), out
    finally:
        _sh.rmtree(d)


vs_old = {"symbol": "2010", "track": "auto", "status": "open", "sampleType": "value-shadow", "category": "value-shadow",
          "type": "buy", "entryPrice": 50.0, "entryDate": "2025-01-01", "maePct": 0.0}
cand = {"symbol": "2020", "sector": "Basic Materials", "currentPrice": 40.0, "valuation": {"pe": 8.0},
        "investmentScore": {"filtered": True, "filterReason": "تحت SMA200W بدون إشارات انعكاس", "axes": {"quality": 20}},
        "financials": {"ocf": 1e9}, "weeklyTechnical": {"sma200w": 45.0}}
held = {"symbol": "2010", "currentPrice": 52.0, "investmentScore": {"filtered": True}}
SD = {"runType": "close", "sectorMedians": {"Basic Materials": {"peMedian": 15.0}}, "stocks": [held, cand]}
cfgN, _ = run_feed(SD, {"stocks": [dict(vs_old)]})
byN = {e["symbol"]: e for e in cfgN["stocks"]}
check("المغذي بلا ختم اليوم: ظل القيمة يُغلق (max_age_12m) ويدخل المرشح (الأساس)",
      byN["2010"]["status"] == "closed" and "2020" in byN)
cfgF, outF = run_feed(dict(SD, providerGuardsSince=FEED_TODAY), {"stocks": [dict(vs_old)]})
byF = {e["symbol"]: e for e in cfgF["stocks"]}
check("يوم الانتقال (providerGuardsSince = اليوم): لا إغلاق ولا دخول في ظل القيمة",
      byF["2010"]["status"] == "open" and "2020" not in byF and "مجمّد اليوم" in outF)
cfgY, _ = run_feed(dict(SD, providerGuardsSince="2026-01-01"), {"stocks": [dict(vs_old)]})
check("وختمٌ قديم لا يجمّد (يوم واحد فقط)", {e["symbol"]: e for e in cfgY["stocks"]}["2010"]["status"] == "closed")

tmp = _tf.mkdtemp()
try:
    def l1_out(guard):
        Dl = _json.load(open(os.path.join(ROOT, "stocks-data.json")))
        for st in Dl["stocks"]:
            st["guardRejected"] = []
        Dl["stocks"][0]["guardRejected"] = [dict({"field": "eps", "value": 1, "reason": "x", "date": TODAY}, **guard)
                                            for _ in range(41)]
        fp = os.path.join(tmp, "d.json")
        _json.dump(Dl, open(fp, "w"), ensure_ascii=False)
        return _sp.run([sys.executable, os.path.join(ROOT, "scripts", "self-check-L1.py"), fp],
                       capture_output=True, text=True).stdout
    oP, oG = l1_out({"guard": "provider"}), l1_out({})
    check("L1 [3]: 41 رفضاً من حراس المزوّد ⇒ تُعدّ منفصلة ولا إنذار «رفض الحراس مرتفع»",
          "رفض الحراس مرتفع" not in oP and "خارج العتبة): {'eps': 41}" in oP)
    check("و41 رفضاً عادياً ⇒ الإنذار (العتبة باقية)", "رفض الحراس مرتفع: 41" in oG)
finally:
    _sh.rmtree(tmp)

# ── 5) المستهلكون ──
st_v = {"currentPrice": 12.0, "valuationInputs": {"eps": 1.621, "epsBasis": "fy-derived", "peSource": 5.0}}
v = se.compute_valuation(st_v, TODAY)
check("compute_valuation: لا peSourceDiffPct حين eps مشتق (لا «توتّر pe» زائف)", "peSourceDiffPct" not in v)
st_v2 = {"currentPrice": 12.0, "valuationInputs": {"eps": 2.0, "peSource": 5.0}}
check("وعلى أساس المزوّد يُحسب كما كان", "peSourceDiffPct" in se.compute_valuation(st_v2, TODAY))
src_l1 = open(os.path.join(ROOT, "scripts", "self-check-L1.py")).read()
check("self-check [6] على epsProvider، و[9] قلبُه على eps (عقد الواجهة) وتباعده على epsProvider",
      src_l1.count('vi.get("epsProvider", vi.get("eps"))') == 1 and 'eps_p = vi.get("epsProvider", eps)' in src_l1)

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
