#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""المرحلة 2 من تعديل المنح (§8-ق، قرار المالك 20-10): كاشف الإجراءات الرأسمالية بعد
2024-03 وتطبيقها وقت القراءة. سوق اصطناعي حتمي (24 سهماً ضجيجاً + أسهم الحالات) —
بلا شبكة وبساعة ثابتة. ويختبر المسار الكامل fetch_daily_and_derive على مجلد مؤقت
(candles/ يبقى خاماً)، وتوزيعات الأساس الحالي، وتجميد الإغلاق وسعر الدخول المعدّل في
سكربتات العينة. الاستعمال: python3 tests/test_corporate_actions.py"""
import collections, copy, contextlib, importlib.util, io, json, os, random, shutil, subprocess, sys, tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("f", os.path.join(ROOT, "scripts", "fetch-inputs-sahmk.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.time.sleep = lambda s: None


class FixedClock(m.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 22, 12, 0, tzinfo=tz)


m.datetime = FixedClock

fails = 0


def check(label, ok):
    global fails
    print(("✅ " if ok else "❌ ") + label)
    fails += 0 if ok else 1


# ── سوق اصطناعي: 300 جلسة يومية من 2025-12-01 ──
D0 = date(2025, 12, 1)
N = 300
DATES = [(D0 + timedelta(days=i)).isoformat() for i in range(N)]


def series(sym, start=40.0, events=(), first=0, vol=100000):
    """events: [(اليوم i، النسبة)] — قفزة الإغلاق في ذلك اليوم بالنسبة المعطاة."""
    rnd = random.Random(sym)
    ev = dict(events)
    rows, c = [], start
    for i in range(first, N):
        if i > first:
            c = c * ev.get(i, 1 + rnd.uniform(-0.012, 0.012))
        c = round(c, 2)
        rows.append([DATES[i], c, c, round(c * 1.01, 2), round(c * 0.99, 2), vol])
    return rows


NOISE = {"N%02d" % k: series("N%02d" % k, 20 + k) for k in range(24)}
BONUS_I = 250          # 2026-08-08 — بعد اللقطة المجمّدة 08-06
BONUS_D = DATES[BONUS_I]


def universe(**extra):
    u = dict(NOISE)
    u.update(extra)
    return u


def detect_all(u, stocks=None):
    stocks = stocks or {}
    mm = m.ca_market_median(u)
    fud = min(R[0][0] for R in u.values())
    ev = []
    for s, R in u.items():
        ev += m.ca_detect(s, R, mm, stocks.get(s), fud)
    m.ca_mark_systemic(ev)
    return {s: [e for e in ev if e["sym"] == s] for s in u}


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **k)
    return out, buf.getvalue()


# ── 1) منحة 1 لكل 5 (1030): A آلي، والتطبيق يضرب ما قبلها ويقسم الحجم ──
R1030 = series("1030", 14.5, [(BONUS_I, 5 / 6)])
EV = detect_all(universe(**{"1030": R1030}))
e = EV["1030"][0]
check("منحة 1 لكل 5 ⇒ A آلي بمعامل 0.833333", len(EV["1030"]) == 1 and e["grade"] == "A"
      and e["decision"] == "auto" and abs(e["factor"] - 5 / 6) < 1e-6)
check("أسهم الضجيج بلا أي حدث", all(not EV[s] for s in NOISE))
plan, pend = m.ca_resolve("1030", EV["1030"], None, R1030)
orig = copy.deepcopy(R1030)
R2, ap, sk = m.apply_capactions(R1030, plan)
check("apply لا يمسّ الصفوف الأصلية", R1030 == orig)
check("ما قبل الحدث × المعامل (close وadjusted وhigh وlow)، والحجم ÷ المعامل",
      all(abs(R2[j][c] - orig[j][c] * 5 / 6) < 1e-4 for j in range(BONUS_I) for c in (1, 2, 3, 4))
      and abs(R2[0][5] - orig[0][5] * 6 / 5) < 1)
check("ما بعد الحدث بلا تغيير", R2[BONUS_I:] == orig[BONUS_I:])
check("لا فجوة بعد التطبيق", abs(R2[BONUS_I][1] / R2[BONUS_I - 1][1] - 1) < 0.02)
check("القيمة بالريال ثابتة (الحجم × السعر)", abs(R2[10][1] * R2[10][5] - orig[10][1] * orig[10][5]) < 1)
check("applied يحمل التاريخ والمعامل والأصل والعمودين",
      ap == [{"date": BONUS_D, "factor": 0.833333, "kind": "bonus/split", "origin": "auto",
              "grade": "A", "cols": ["close", "adjusted"]}] and not sk and not pend)

# ── 2) لا تكرار: تطبيق ثانٍ على المعدّل يُتخطّى؛ ومخزن معدّل لدى المزوّد (1120) كذلك ──
R3, ap3, sk3 = m.apply_capactions(R2, plan)
check("تطبيق ثانٍ على صفوف معدّلة ⇒ يُتخطّى (لا تعديل مزدوج)",
      R3 == R2 and not ap3 and "مُعدَّل لدى المزوّد" in sk3[0]["why"])
R1120 = series("1120", 71.4)    # المزوّد عدّلها: لا فجوة في المخزن
_, ap4, sk4 = m.apply_capactions(R1120, [(DATES[200], 0.8, "bonus", "manual", "M")])
check("بند يدوي على مخزن بلا فجوة (1120) ⇒ لا تطبيق", not ap4 and len(sk4) == 1)

# ── 3) اليدوي يغلب الكاشف ضمن 3 جلسات، وتعارض المعاملين إنذار ──
man = [{"date": DATES[BONUS_I + 1], "factor": 0.8, "kind": "bonus", "source": "اختبار"}]
(plan5, pend5), out5 = quiet(m.ca_resolve, "1030", EV["1030"], man, R1030)
check("اليدوي ضمن 3 جلسات يحلّ محل الآلي، والتعارض يُطبع",
      plan5 == [(DATES[BONUS_I + 1], 0.8, "bonus", "manual", "M")] and "يخالف الكاشف" in out5)
_, ap5, sk5 = m.apply_capactions(R1030, plan5)
check("يدوي بتاريخ لا فجوة فيه ⇒ متخطّى لا مطبَّق خطأً", not ap5 and sk5)
man_na = [{"date": BONUS_D, "factor": 1, "kind": "no-adjust", "source": "اختبار"}]
plan6, pend6 = m.ca_resolve("1030", EV["1030"], man_na, R1030)
_, ap6, sk6 = m.apply_capactions(R1030, plan6)
check("no-adjust يُسكت الكاشف عند تاريخه", not ap6 and not pend6 and sk6[0]["why"] == "no-adjust")

# ── 4) هبوط جماعي في يوم واحد (وصلة مزوّد) ⇒ S يدوي، لا تطبيق ──
mass = {"M%d" % k: series("M%d" % k, 30 + k, [(200, 5 / 6)]) for k in range(6)}
EVm = detect_all(universe(**mass))
check("6 أسهم بالفجوة نفسها ⇒ S يدوي لكلها",
      all(EVm[s][0]["grade"] == "S" and EVm[s][0]["decision"] == "manual" for s in mass))

# ── 5) ارتداد في الجلسة التالية ⇒ N (عطب بيانات) ──
Rrev = series("REV", 50, [(200, 0.8), (201, 1.25)])
EVr = detect_all(universe(REV=Rrev))
check("قفزة ثم عودة ⇒ N لا منحة", EVr["REV"] and all(x["grade"] == "N" for x in EVr["REV"]))

# ── 6) توزيع استثنائي يفسّر الفجوة ⇒ D ──
Rdiv = series("DIV", 50, [(200, 0.8)])
st_div = {"dividendEvents": [{"date": DATES[200], "amount": round(Rdiv[199][1] * 0.2, 4)}]}
EVd = detect_all(universe(DIV=Rdiv), {"DIV": st_div})
check("توزيع 20% في يوم الفجوة ⇒ D لا منحة 4:5", EVd["DIV"][0]["grade"] == "D")
EVd2 = detect_all(universe(DIV=Rdiv))
check("الفجوة نفسها بلا توزيع ⇒ A (منحة 1 لكل 4)", EVd2["DIV"][0]["grade"] == "A"
      and abs(EVd2["DIV"][0]["factor"] - 0.8) < 1e-6)

# ── 7) إدراج جديد (أول 5 جلسات) ⇒ X؛ وقبل 2024-03 ⇒ P ──
Ripo = series("IPO", 10, [(103, 1.3)], first=100)
EVi = detect_all(universe(IPO=Ripo))
check("قفزة في أول 5 جلسات إدراج ⇒ X", EVi["IPO"][0]["grade"] == "X")
Rold = [["2024-02-%02d" % d, 10.0, 10.0, 10.1, 9.9, 1000] for d in range(1, 20)]
Rold[10:] = [[r[0], 5.0, 5.0, 5.05, 4.95, 1000] for r in Rold[10:]]
EVp = detect_all(universe(OLD=Rold + series("OLDX", 5.0)))
check("فجوة قبل 2024-03 ⇒ P خارج النطاق", EVp["OLD"][0]["grade"] == "P")

# ── 8) B: q من sharesHistory يحسم؛ وبلا q يبقى معلّقاً ──
RB = series("B1", 6.6, [(BONUS_I, 10 / 13)])
EVb = detect_all(universe(B1=RB))
check("منحة 3 لكل 10 ⇒ B معلّق بلا q (منافسة 1 لكل 3)",
      EVb["B1"][0]["grade"] == "B" and EVb["B1"][0]["decision"] == "manual")
stB = {"sharesHistory": [{"date": DATES[240], "lastSeen": DATES[245], "shares": 200e6},
                         {"date": DATES[255], "lastSeen": DATES[255], "shares": 260e6}]}
EVb2 = detect_all(universe(B1=RB), {"B1": stB})
check("q = 200/260 ⇒ B آلي بمعامل 10/13",
      EVb2["B1"][0]["grade"] == "B" and EVb2["B1"][0]["decision"] == "auto"
      and abs(EVb2["B1"][0]["factor"] - 10 / 13) < 1e-6)
plan_b, pend_b = m.ca_resolve("B1", EVb["B1"], None, RB)
check("B المعلّق ⇒ في pending لا في الخطة", not plan_b and pend_b[0]["grade"] == "B")

# ── 9) q يناقض A ⇒ يدوي؛ وq≈1 بلا معلومة ⇒ يبقى آلياً ──
stX = {"sharesHistory": [{"date": DATES[240], "lastSeen": DATES[245], "shares": 100e6},
                         {"date": DATES[255], "lastSeen": DATES[255], "shares": 200e6}]}
EVx = detect_all(universe(**{"1030": R1030}), {"1030": stX})
check("A يناقضها q=0.5 ⇒ يدوي", EVx["1030"][0]["decision"] == "manual")
stN = {"sharesHistory": [{"date": DATES[255], "lastSeen": DATES[255], "shares": 1.25e9}],
       "valuationInputs": {"sharesOutstanding": 1.25e9, "marketCap": 1.25e9 * 14.5, "theirPrice": 14.5}}
EVn = detect_all(universe(**{"1030": R1030}), {"1030": stN})
check("المزوّد لم يحدّث العدد (q≈1) ⇒ بلا معلومة، A آلي", EVn["1030"][0]["decision"] == "auto")

# ── 10) C لا يُطبَّق آلياً أبداً، حتى مع q مطابق ──
RC = series("C1", 9.0, [(BONUS_I, 0.65)])
stC = {"sharesHistory": [{"date": DATES[240], "lastSeen": DATES[245], "shares": 100e6},
                         {"date": DATES[255], "lastSeen": DATES[255], "shares": 153.85e6}]}
EVc = detect_all(universe(C1=RC), {"C1": stC})
check("نسبة غير شائعة (0.65) ⇒ C يدوي حتى مع q=0.65", EVc["C1"][0]["grade"] == "C"
      and EVc["C1"][0]["decision"] == "manual")

# ── 11) W: فجوة في آخر جلستين ⇒ معلّق ──
RW = series("W1", 30, [(N - 2, 0.5)])
EVw = detect_all(universe(W1=RW))
check("فجوة في آخر جلستين ⇒ W معلّق", EVw["W1"][0]["grade"] == "W" and EVw["W1"][0]["decision"] == "pending")

# ── 12) q من المجمّد: الشروط الثلاثة ──
st_fz = {"sharesHistory": [{"date": "2026-10-22", "lastSeen": "2026-10-22", "shares": 1.5e9}],
         "valuationInputs": {"sharesOutstanding": 1.25e9, "marketCap": 1.25e9 * 14.5, "theirPrice": 14.5}}
q, src = m.ca_q_for(st_fz, "2026-10-01", [])
check("المجمّد «قبل» وآخر sharesHistory «بعد» ⇒ q = 5/6", abs(q - 5 / 6) < 1e-9)
check("الحدث قبل اللقطة ⇒ لا q", m.ca_q_for(st_fz, "2026-08-01", [])[0] is None)
check("حدث آخر بين اللقطة والحدث ⇒ لا q", m.ca_q_for(st_fz, "2026-10-01", ["2026-09-01"])[0] is None)
bad = copy.deepcopy(st_fz)
bad["valuationInputs"]["marketCap"] = 1.25e9 * 14.5 * 1.3
check("المجمّد يخالف marketCap/theirPrice ⇒ لا q", m.ca_q_for(bad, "2026-10-01", [])[0] is None)

# ── 13) الملف اليدوي: بند معطوب يسقط وحده، وملف غير مقروء = {} ──
tmpd = tempfile.mkdtemp()
try:
    p = os.path.join(tmpd, "ca.json")
    json.dump({"_doc": "x", "1": [{"date": "2026-10-01", "factor": 0.5, "kind": "bonus", "source": "s"},
                                  {"date": "2026-10-01", "factor": "0.5", "kind": "bonus", "source": "s"},
                                  {"date": "٢٠٢٦-١٠-٠١", "factor": 0.5, "kind": "bonus", "source": "s"},
                                  {"date": "2026-10-01", "factor": 0.5, "kind": "dividend", "source": "s"},
                                  {"date": "2026-10-01", "factor": 0.5, "kind": "bonus"}]}, open(p, "w"))
    man_ok, out = quiet(m.load_manual_actions, p)
    check("بند سليم يُقبل والأربعة المعطوبة تسقط بطباعة",
          len(man_ok["1"]) == 1 and out.count("بند معطوب") == 4)
    open(p, "w").write("{bad")
    man_bad, out = quiet(m.load_manual_actions, p)
    check("ملف غير مقروء ⇒ {} بإنذار", man_bad == {} and "غير مقروء" in out)
    check("ملف غائب ⇒ {}", m.load_manual_actions(os.path.join(tmpd, "none.json")) == {})
    real, out = quiet(m.load_manual_actions, os.path.join(ROOT, "corporate-actions.json"))
    check("corporate-actions.json في المستودع سليم (6040 و1030 و7202) بلا بند معطوب",
          sorted(real) == ["1030", "6040", "7202"] and "معطوب" not in out)
finally:
    shutil.rmtree(tmpd)

check("ca_factor_after: ما بعد d0 وحتى d1",
      m.ca_factor_after([{"date": "2026-09-01", "factor": 0.5}, {"date": "2026-10-01", "factor": 0.8}], "2026-08-31",
                        "2026-09-30") == 0.5)

# ── 14) build_levels: الفجوة المعلّقة تقيّد النافذة بما بعدها ──
lv = m.build_levels(RB, 0.1, None, "s", [DATES[BONUS_I]])
check("فجوة معلّقة ⇒ المستويات مقيّدة من بعدها",
      lv.get("restricted") is True and lv.get("restrictedFrom") == DATES[BONUS_I + 1])
check("بلا معلّق ⇒ لا تقييد", not m.build_levels(RB, 0.1, None, "s").get("restricted"))


# ── 15) المسار الكامل: fetch_daily_and_derive على مجلد مؤقت ──
class Api:
    def get(self, path, **k):
        return {"data": []}, None      # لا جديد: المخزن كما هو


tmpd = tempfile.mkdtemp()
try:
    cdir = os.path.join(tmpd, "candles")
    os.makedirs(cdir)
    u = universe(**{"1030": R1030, "B1": RB})
    for s, R in u.items():
        m.save_candles(cdir, s, R)
    raw_before = {s: open(os.path.join(cdir, s + ".json")).read() for s in u}
    stocks = [{"symbol": s, "valuationInputs": {"sharesOutstanding": 1.25e9, "marketCap": 1.25e9 * 14.5,
                                                 "theirPrice": 14.5}} for s in u]
    counters = collections.defaultdict(int)
    tasi = {"3m": 1.0, "6m": 2.0, "12_1": 3.0}
    _, out = quiet(m.fetch_daily_and_derive, Api(), stocks, counters, cdir, tasi, "stamp", DATES[-1])
    S = {s["symbol"]: s for s in stocks}
    check("candles/ يبقى خاماً بعد التشغيل", all(open(os.path.join(cdir, s + ".json")).read() == raw_before[s] for s in u))
    check("1030: capActions مكتوبة، وsharesCapFactor = 0.833333",
          S["1030"].get("capActions", [{}])[0].get("factor") == 0.833333
          and S["1030"]["valuationInputs"].get("sharesCapFactor") == 0.833333)
    ref, _ = quiet(m.fetch_daily_and_derive, Api(), [{"symbol": "1030"}], collections.defaultdict(int), cdir, tasi,
                   "stamp", DATES[-1])
    adj, _, _ = m.apply_capactions(R1030, [(BONUS_D, 5 / 6, "bonus", "auto", "A")])
    st_ref = {"symbol": "1030"}
    m._derive_daily(st_ref, adj, [], tasi, "stamp", collections.defaultdict(int))
    check("المؤشرات من الصفوف المعدّلة (ema40w وrsi14d وعائد 3 أشهر)",
          S["1030"]["weeklyTechnical"]["ema40w"] == st_ref["weeklyTechnical"]["ema40w"]
          and S["1030"]["dailyExtra"]["rsi14d"] == st_ref["dailyExtra"]["rsi14d"]
          and S["1030"]["relativeStrength"]["return3m"] == st_ref["relativeStrength"]["return3m"])
    st_raw = {"symbol": "1030"}
    m._derive_daily(st_raw, R1030, [], tasi, "stamp", collections.defaultdict(int))
    check("والفرق عن الخام حقيقي (عائد 3 أشهر لا يحمل −17% الوهمية)",
          st_raw["relativeStrength"]["return3m"] < -10 < S["1030"]["relativeStrength"]["return3m"])
    check("بوابة السيولة لا تتغيّر بالتعديل (القيمة بالريال)",
          abs(S["1030"]["dailyExtra"]["tradingValueMedian20"] - st_raw["dailyExtra"]["tradingValueMedian20"]) <= 2)
    check("B1 المعلّق: capActionsPending والمستويات مقيّدة، ولا capActions",
          S["B1"].get("capActionsPending", [{}])[0].get("grade") == "B" and "capActions" not in S["B1"]
          and S["B1"]["levels"].get("restricted") is True and "sharesCapFactor" not in S["B1"]["valuationInputs"])
    check("أسهم الضجيج بلا capActions ولا pending ولا sharesCapFactor",
          all("capActions" not in S[s] and "capActionsPending" not in S[s]
              and "sharesCapFactor" not in S[s]["valuationInputs"] for s in NOISE))
    check("سطر السجل يعدّ المطبَّق والمعلّق", "🧮 إجراءات رأسمالية: مطبَّقة آلياً 1" in out and "معلّقة للمراجعة 1" in out)
    # البند اليدوي بجوار --data يُقرأ ويغلب
    json.dump({"B1": [{"date": BONUS_D, "factor": 0.769231, "kind": "bonus", "source": "اختبار"}]},
              open(os.path.join(tmpd, "corporate-actions.json"), "w"))
    stocks2 = [{"symbol": s} for s in u]
    _, out2 = quiet(m.fetch_daily_and_derive, Api(), stocks2, collections.defaultdict(int), cdir, tasi, "stamp", DATES[-1])
    S2 = {s["symbol"]: s for s in stocks2}
    check("corporate-actions.json بجوار البيانات يُطبَّق ويُسقط المعلّق",
          S2["B1"].get("capActions", [{}])[0].get("origin") == "manual" and "capActionsPending" not in S2["B1"])
finally:
    shutil.rmtree(tmpd)


# ── 16) التوزيع على أساس السهم الحالي (divTtm12m) ──
class DivApi:
    def get(self, path, **k):
        if path.startswith("/dividends/"):
            return {"history": [{"eligibility_date": "2026-06-30", "value": 0.6},
                                {"eligibility_date": "2026-10-10", "value": 0.3}]}, None
        if path.startswith("/company/"):
            return {"fundamentals": {"eps_ttm": 2.0, "shares_outstanding": 1.5e9}}, None
        if path.startswith("/analytics/ratios/"):
            return {"ratios": {"roe": 10.8, "roa": 1.41, "net_margin": 25.1, "debt_to_equity": 0.13}}, None
        return None, "HTTP 500"


st = {"symbol": "1030", "sector": "Industrials", "industry": "x", "financials": {},
      "capActions": [{"date": "2026-10-01", "factor": 0.833333}], "guardRejected": [], "_prevFinancials": {}}
data = {"equitySource": {"choice": "derived"}, "deScaleDecision": {"scale": "ratio×100"}}
quiet(m.fetch_fundamentals, DivApi(), data, [st], collections.defaultdict(int), "2026-10-22", full_universe=False)
check("divTtm12m: ما قبل المنحة × 5/6 (0.6 → 0.5) وما بعدها كما هو ⇒ 0.8",
      abs(st["valuationInputs"]["divTtm12m"] - 0.8) < 1e-3
      and st["dividendEvents"] == [{"date": "2026-06-30", "amount": 0.6}, {"date": "2026-10-10", "amount": 0.3}])


# ── 17) سكربتات العينة: تجميد الإغلاق، وسعر الدخول المعدّل ──
def run_feed(stocks_data, cfg):
    d = tempfile.mkdtemp()
    try:
        sp, cp = os.path.join(d, "s.json"), os.path.join(d, "c.json")
        json.dump(stocks_data, open(sp, "w"))
        json.dump(cfg, open(cp, "w"))
        os.makedirs(os.path.join(d, "arch"))
        env = dict(os.environ, STOCKS_JSON=sp, CONFIG_JSON=cp, ARCHIVE_DIR=os.path.join(d, "arch"))
        out = subprocess.run(["bash", os.path.join(ROOT, "scripts", "feed-watchlist.sh")], env=env,
                             capture_output=True, text=True).stdout
        return json.load(open(cp)), out
    finally:
        shutil.rmtree(d)


entry = {"symbol": "2200", "track": "auto", "status": "open", "category": "buy", "type": "buy",
         "entryPrice": 6.6, "entryDate": "2026-08-23", "maePct": 0.0}
low = {"symbol": "2200", "currentPrice": 5.2, "investmentScore": {"total": 40, "classCode": "filtered"},
       "capActionsPending": [{"date": "2026-08-24", "r": 0.77, "grade": "B", "why": "x"}]}
cfg, out = run_feed({"runType": "close", "stocks": [low]}, {"stocks": [dict(entry)]})
check("feed-watchlist: نقاط دون 50 مع فجوة معلّقة بعد الدخول ⇒ لا إغلاق (مجمّد)",
      cfg["stocks"][0]["status"] == "open" and "مجمّد" in out)
low2 = dict(low)
low2.pop("capActionsPending")
low2["capActions"] = [{"date": "2026-08-24", "factor": 0.769231}]
low2["investmentScore"] = {"total": 70, "classCode": "hold"}
cfg, out = run_feed({"runType": "close", "stocks": [low2]}, {"stocks": [dict(entry)]})
check("feed-watchlist: MAE على سعر الدخول المعدّل (6.6 × 10/13 = 5.077 ⇒ 5.2 فوقه ⇒ 0.0)",
      cfg["stocks"][0]["maePct"] == 0.0)
low3 = dict(low2)
low3.pop("capActions")
cfg, out = run_feed({"runType": "close", "stocks": [low3]}, {"stocks": [dict(entry)]})
check("وبلا الحدث المطبَّق ⇒ MAE على الخام (−21.21)", cfg["stocks"][0]["maePct"] == -21.21)

d = tempfile.mkdtemp()
try:
    sp, cp = os.path.join(d, "s.json"), os.path.join(d, "c.json")
    e2 = dict(entry, aboveSmaAtEntry=True)
    json.dump({"runType": "close", "lastUpdated": "x", "stocks": [dict(low, weeklyTechnical={"sma200w": 6.0})]},
              open(sp, "w"))
    json.dump({"stocks": [e2]}, open(cp, "w"))
    env = dict(os.environ, STOCKS_JSON=sp, CONFIG_JSON=cp, ARCHIVE_DIR=d, DRY_RUN="1")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "close_sma200w.py")], env=env,
                         capture_output=True, text=True).stdout
    check("close_sma200w: كسر مع فجوة معلّقة بعد الدخول ⇒ مجمّد لا إغلاق", "مجمّد" in out and "كان سيُغلق 0" in out)
finally:
    shutil.rmtree(d)

# ── 18) مولّد صفحة الدقة: entryPriceAdj لمدخل يعبر حدثاً مطبَّقاً، وdataFault من الإعداد ──
d = tempfile.mkdtemp()
try:
    P = {k: os.path.join(d, k) for k in ("s.json", "c.json", "p.html", "cache.json", "t.json")}
    json.dump({"runType": "close", "lastUpdated": "2026-10-20 16:00", "stocks": [
        {"symbol": "1030", "currentPrice": 12.0, "capActions": [{"date": "2026-10-01", "factor": 0.833333}]},
        {"symbol": "2200", "currentPrice": 5.0}]}, open(P["s.json"], "w"))
    json.dump({"stocks": [
        {"symbol": "1030", "name": "س", "entryPrice": 14.4, "entryDate": "2026-09-01", "track": "auto"},
        {"symbol": "1030", "name": "س", "entryPrice": 12.0, "entryDate": "2026-10-05", "track": "auto"},
        {"symbol": "2200", "name": "أ", "entryPrice": 6.6, "entryDate": "2026-08-23", "track": "auto",
         "status": "closed", "closeDate": "2026-08-25", "closePrice": 5.32, "closeReason": "score_below_50",
         "dataFault": {"kind": "capaction-unadjusted", "date": "2026-08-24", "label": "أُغلق بعطب بيانات"}}]},
        open(P["c.json"], "w"))
    open(P["p.html"], "w").write('<script>\nconst WATCHLIST = [\n];\nconst META = {updatedAt: "x"};\n</script>\n')
    json.dump({"data": []}, open(P["t.json"], "w"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("SAHMK")}
    env.update(STOCKS_JSON=P["s.json"], CONFIG_JSON=P["c.json"], HTML_FILE=P["p.html"],
               CACHE_FILE=P["cache.json"], TASI_HISTORY=P["t.json"])
    subprocess.run(["bash", os.path.join(ROOT, "scripts", "update-watchlist-accuracy.sh")], env=env,
                   capture_output=True, text=True)
    html = open(P["p.html"]).read()
    blocks = html.split("\n  {\n")[1:]
    check("صفحة الدقة: مدخل قبل المنحة ⇒ entryPriceAdj = 14.4 × 5/6 = 12.0",
          "entryPriceAdj: 12.0," in blocks[0])
    check("ومدخل بعد المنحة ⇒ بلا entryPriceAdj", "entryPriceAdj" not in blocks[1])
    check("و2200 ⇒ dataFault بوسمه، بلا entryPriceAdj (حدثه معلّق لا مطبَّق)",
          'dataFault:     {kind: "capaction-unadjusted", date: "2026-08-24", label: "أُغلق بعطب بيانات"},' in blocks[2]
          and "entryPriceAdj" not in blocks[2])
finally:
    shutil.rmtree(d)

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
