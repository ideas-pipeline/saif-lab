#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§8-ن: حارس التوزيع الوهمي — أحقية يرفضها فحص السعر (القاعدة الواحدة مع سلسلة العائد الكلي)
تسقط من divTtm12m، فلا يدخل عائدها التقييم ولا وسيط القطاع (3008: 43.44 على سعر 1.06 ⇒ 4098%).
سلاسل اصطناعية تنتهي اليوم — بلا شبكة. الاستعمال: python3 tests/test_div_guard.py"""
import collections, contextlib, importlib.util, io, os, shutil, sys, tempfile
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("f", os.path.join(HERE, "..", "scripts", "fetch-inputs-sahmk.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.time.sleep = lambda s: None
spec2 = importlib.util.spec_from_file_location("se", os.path.join(HERE, "..", "scripts", "scoring-engine.py"))
se = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(se)

fails = 0


def check(label, ok):
    global fails
    print(("✅ " if ok else "❌ ") + label)
    fails += 0 if ok else 1


NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")
D = [(date.fromisoformat(TODAY) - timedelta(days=299 - i)).isoformat() for i in range(300)]
T0 = {"3m": 0, "6m": 0, "12_1": 0}


def series(close=1.06, drop_at=None, after=None):
    rows = [[d, close, close, close * 1.01, close * 0.99, 1000] for d in D]
    if drop_at is not None:
        for r in rows[drop_at + 1:]:
            r[1] = r[2] = after
    return rows


ie = 270
E3008 = {"date": D[ie], "amount": 43.44}
R = series()

# ── 1) الفحص الواحد ──
rej = m.div_rejected(R, [E3008], [])
check("3008: 43.44 على 1.06 (y ≈ 41×) ⇒ مرفوض بسبب العائد",
      len(rej) == 1 and rej[0]["date"] == D[ie] and rej[0]["y"] > 40 and "عائد" in rej[0]["why"])
ok_ev = {"date": D[ie], "amount": 0.05}
R_ok = series(1.06, ie, 1.01)
check("توزيع 4.7% بهبوط مقابل ⇒ مقبول", m.div_rejected(R_ok, [ok_ev], []) == [])
big = {"date": D[ie], "amount": 0.15}                     # y ≈ 14% بلا هبوط
check("عائد 14% بلا هبوط استبعاد ⇒ مرفوض (قاعدة 8% ونصف الهبوط)", len(m.div_rejected(R, [big], [])) == 1)
R_big = series(1.06, ie, 0.92)                           # هبوط ~13%
check("وعائد 14% بهبوط مقابل ⇒ مقبول (توزيع استثنائي حقيقي)", m.div_rejected(R_big, [big], []) == [])
fut = {"date": D[-1], "amount": 43.44}
check("أحقية بلا جلسة استبعاد بعدُ ⇒ عتبة 25% وحدها ترفضها",
      len(m.div_rejected(R, [fut], [])) == 1 and m.div_rejected(R, [{"date": D[-1], "amount": 0.15}], []) == [])
check("أحقية قبل أول شمعة ⇒ لا حكم", m.div_rejected(R, [{"date": "2000-01-01", "amount": 43.44}], []) == [])
check("المنحة تُحسب: 0.30 على 1.06 قبل منحة 1:1 (y = 14% لا 28%) ⇒ قاعدة الهبوط لا عتبة 25%",
      "هبوط" in m.div_rejected(R, [{"date": D[ie], "amount": 0.30}],
                               [{"date": D[ie + 5], "factor": 0.5}])[0]["why"])

# ── 2) سلسلة العائد الكلي لم تتغيّر بإعادة التنظيم ──
_, log = m.tr_local_series(R, [E3008], [], tc="2000-01-01")
check("tr_local_series: الرفض نفسه في سجلها (القاعدة واحدة)", len(log) == 1 and log[0][0] == D[ie])
_, logf = m.tr_local_series(R, [fut], [], tc="2000-01-01")
check("ولا تحكم على أحقية بلا جلسة استبعاد (كما كانت)", logf == [])

# ── 3) divTtm12m ──
rows = [(E3008["date"], E3008["amount"])]
check("بلا رفض ⇒ 43.44 (الخلل القديم)", m.div_ttm_capadj(rows, [], NOW, TODAY) == (43.44, "ttm12m"))
check("بالرفض وحده في النافذة ⇒ غير متوفر (None، rejected) لا «لا يوزع»",
      m.div_ttm_capadj(rows, [], NOW, TODAY, [(D[ie], 43.44)]) == (None, "rejected"))
rows2 = rows + [(D[100], 0.05)]
check("ومعه توزيع سليم في النافذة ⇒ مجموع السليم وحده",
      m.div_ttm_capadj(rows2, [], NOW, TODAY, [(D[ie], 43.44)]) == (0.05, "ttm12m"))
check("الرفض بالتاريخ والمبلغ معاً: صحّح المزوّد المبلغ ⇒ يُحسب",
      m.div_ttm_capadj([(D[ie], 0.04)], [], NOW, TODAY, [(D[ie], 43.44)]) == (0.04, "ttm12m"))
old = (date.fromisoformat(TODAY) - timedelta(days=400)).isoformat()
check("رفضٌ خارج نافذة 12 شهراً وداخل 18 ⇒ يبقى «خارج نافذة 12 شهراً» لا «لا يوزع» (3007، ش3)",
      m.div_ttm_capadj([(old, 43.44)], [], NOW, TODAY, [(old, 43.44)]) == (0.0, "none-recent18m"))
check("المطابقة على 4 منازل: المزوّد 0.333333 والمرفوض المخزَّن 0.3333 ⇒ يبقى مرفوضاً (ش2)",
      m.div_ttm_capadj([(D[ie], 0.333333)], [], NOW, TODAY, [(D[ie], 0.3333)]) == (None, "rejected"))

# ── 4) المحرك: لا عائد ولا دخول في وسيط القطاع ──
v = se.compute_valuation({"currentPrice": 1.06, "valuationInputs": {"divTtm12m": None, "divBasis": "rejected"}}, TODAY)
check("المحرك: divTtm12m = None ⇒ dividendYield = None («عائد غير متوفر»، لا 4098%)", v.get("dividendYield") is None)

# ── 5) المسار اليومي الكامل: fetch_daily_and_derive ──
tmpd = tempfile.mkdtemp()
try:
    cdir = os.path.join(tmpd, "candles")
    os.makedirs(cdir)
    m.save_candles(cdir, "3008", R)

    class Api:
        def get(self, path, **k):
            return {"data": []}, None

    st = {"symbol": "3008", "dividendEvents": [E3008],
          "valuationInputs": {"divTtm12m": 43.44, "divBasis": "ttm12m"}}
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        m.fetch_daily_and_derive(Api(), [st], collections.defaultdict(int), cdir, T0, "s", D[-1])
    vi = st["valuationInputs"]
    check("اليومي: divTtm12m 43.44 ⇒ None (rejected)، ووسم dividendRejected، وسطر 🚫",
          vi["divTtm12m"] is None and vi["divBasis"] == "rejected"
          and st["dividendRejected"][0]["date"] == D[ie] and "🚫 3008" in buf.getvalue())
    st["dividendEvents"] = [{"date": D[ie], "amount": 0.04}]     # المزوّد صحّح
    with contextlib.redirect_stdout(io.StringIO()):
        m.fetch_daily_and_derive(Api(), [st], collections.defaultdict(int), cdir, T0, "s", D[-1])
    check("المزوّد صحّح ⇒ الوسم يُمسح والعائد يعود (يُعاد الحساب لزوال الرفض)",
          "dividendRejected" not in st and st["valuationInputs"]["divTtm12m"] == 0.04)
    st_ok = {"symbol": "3008", "dividendEvents": [{"date": D[ie], "amount": 0.04}],
             "valuationInputs": {"divTtm12m": 0.04, "divBasis": "ttm12m", "divsAsOf": "x"}}
    with contextlib.redirect_stdout(io.StringIO()):
        m.fetch_daily_and_derive(Api(), [st_ok], collections.defaultdict(int), cdir, T0, "s", D[-1])
    check("وسهم سليم بلا رفض ولا إجراء ⇒ لا يُمسّ", st_ok["valuationInputs"] == {"divTtm12m": 0.04,
                                                                              "divBasis": "ttm12m", "divsAsOf": "x"})
finally:
    shutil.rmtree(tmpd)


# ── 6) الأسبوعي: do_dividends يُسقط ما رفضه اليومي ──
class DivApi:
    def get(self, path, **k):
        if path.startswith("/dividends/"):
            return {"history": [{"eligibility_date": D[ie], "value": 43.44}]}, None
        if path.startswith("/company/"):
            return {"fundamentals": {"eps_ttm": -0.13, "shares_outstanding": 226.04e6}}, None
        if path.startswith("/analytics/ratios/"):
            return {"ratios": {"roe": -58.2, "roa": -13.27, "net_margin": -14.9, "debt_to_equity": 199.46}}, None
        return None, "HTTP 500"


m._DIV_ROWS.clear()          # بلا تمريرة يومية في التشغيلة ⇒ المرفوض المخزَّن وحده
stw = {"symbol": "3008", "sector": "Basic Materials", "industry": "Building Materials", "financials": {},
       "guardRejected": [], "_prevFinancials": {},
       "dividendRejected": [{"date": D[ie], "amount": 43.44, "y": 40.98, "why": "x"}]}
data = {"equitySource": {"choice": "derived"}, "deScaleDecision": {"scale": "ratio×100"}}
with contextlib.redirect_stdout(io.StringIO()):
    m.fetch_fundamentals(DivApi(), data, [stw], collections.defaultdict(int), TODAY, full_universe=False)
check("الأسبوعي: /dividends يعيد 43.44 ⇒ divTtm12m None (rejected) بالرفض المخزَّن، وdividendEvents كما هي",
      stw["valuationInputs"]["divTtm12m"] is None and stw["valuationInputs"]["divBasis"] == "rejected"
      and stw["dividendEvents"] == [{"date": D[ie], "amount": 43.44}])

# ش1: توزيع وهمي جديد يصل من /dividends في الأسبوعي ولا رفض مخزَّن له ⇒ يُحكم بأسعار اليومي في التشغيلة نفسها
m._DIV_ROWS.clear()
m._DIV_ROWS["3008"] = (R, [])
stn = {"symbol": "3008", "sector": "Basic Materials", "industry": "Building Materials", "financials": {},
       "guardRejected": [], "_prevFinancials": {}}
with contextlib.redirect_stdout(io.StringIO()) as bw:
    m.fetch_fundamentals(DivApi(), data, [stn], collections.defaultdict(int), TODAY, full_universe=False)
check("الأسبوعي: حدث وهمي جديد بلا رفض مخزَّن ⇒ None (rejected) فوراً، وdividendRejected يُكتب، وسطر 🚫",
      stn["valuationInputs"]["divTtm12m"] is None and stn["valuationInputs"]["divBasis"] == "rejected"
      and stn["dividendRejected"][0]["date"] == D[ie] and "🚫 3008" in bw.getvalue())
stc = dict(stn, dividendRejected=[{"date": D[ie], "amount": 43.44, "y": 40.98, "why": "x"}])


class FixedApi(DivApi):
    def get(self, path, **k):
        if path.startswith("/dividends/"):
            return {"history": [{"eligibility_date": D[ie], "value": 0.04}]}, None
        return super().get(path, **k)


with contextlib.redirect_stdout(io.StringIO()):
    m.fetch_fundamentals(FixedApi(), data, [stc], collections.defaultdict(int), TODAY, full_universe=False)
check("والمزوّد صحّح في الأسبوعي ⇒ الوسم يُمسح والعائد 0.04", "dividendRejected" not in stc
      and stc["valuationInputs"]["divTtm12m"] == 0.04)

# ش-أ (ختم الناقد): التكامل الحقيقي يومي ⇒ أسبوعي في التشغيلة نفسها، بلا تعبئة _DIV_ROWS يدوياً
m._DIV_ROWS.clear()
tmpd = tempfile.mkdtemp()
try:
    cdir = os.path.join(tmpd, "candles")
    os.makedirs(cdir)
    m.save_candles(cdir, "3008", R)
    sti = {"symbol": "3008", "sector": "Basic Materials", "industry": "Building Materials", "financials": {},
           "guardRejected": [], "_prevFinancials": {}, "dividendEvents": [],
           "valuationInputs": {"divTtm12m": 0.0, "divBasis": "none"}}
    with contextlib.redirect_stdout(io.StringIO()):
        m.fetch_daily_and_derive(Api(), [sti], collections.defaultdict(int), cdir, T0, "s", D[-1])
        m.fetch_fundamentals(DivApi(), data, [sti], collections.defaultdict(int), TODAY, full_universe=False)
    check("تكامل: اليومي ثم الأسبوعي — أحقية وهمية جديدة بلا رفض مخزَّن ⇒ None (rejected) في التشغيلة نفسها",
          sti["valuationInputs"]["divTtm12m"] is None and sti["valuationInputs"]["divBasis"] == "rejected"
          and sti["dividendRejected"][0]["date"] == D[ie])
    # م1: صحّح المزوّد في الأسبوعي وفشلت أساسياته ⇒ لا يعلق «غير متوفر» في اليومي التالي
    stk = {"symbol": "3008", "dividendEvents": [{"date": D[ie], "amount": 0.04}],
           "valuationInputs": {"divTtm12m": None, "divBasis": "rejected"}}
    with contextlib.redirect_stdout(io.StringIO()):
        m.fetch_daily_and_derive(Api(), [stk], collections.defaultdict(int), cdir, T0, "s", D[-1])
    check("م1: (None، rejected) بلا رفض قائم ⇒ اليومي يعيد الحساب (0.04)",
          stk["valuationInputs"]["divTtm12m"] == 0.04 and stk["valuationInputs"]["divBasis"] == "ttm12m")
    # N11: الأسبوعي يمرّر الإجراءات المطبَّقة — 0.30 قبل منحة 1:1 (y = 14% لا 28%) يُرفض بقاعدة الهبوط
    stb = {"symbol": "3008", "sector": "Basic Materials", "industry": "Building Materials", "financials": {},
           "guardRejected": [], "_prevFinancials": {}, "dividendEvents": []}

    class BonusDivApi(DivApi):
        def get(self, path, **k):
            if path.startswith("/dividends/"):
                return {"history": [{"eligibility_date": D[ie], "value": 0.30}]}, None
            return super().get(path, **k)
    m._DIV_ROWS["3008"] = (R, [{"date": D[ie + 5], "factor": 0.5}])
    with contextlib.redirect_stdout(io.StringIO()):
        m.fetch_fundamentals(BonusDivApi(), data, [stb], collections.defaultdict(int), TODAY, full_universe=False)
    check("N11: الأسبوعي يحسب العائد بمعامل المنحة (14% ⇒ سبب الهبوط لا عتبة 25%)",
          "هبوط" in stb["dividendRejected"][0]["why"])
finally:
    shutil.rmtree(tmpd)

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
