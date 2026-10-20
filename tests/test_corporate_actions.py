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
plan, pend, _sup, _meta = m.ca_resolve("1030", EV["1030"], None, R1030)
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

# ── 3) اليدوي يغلب الكاشف ضمن 3 جلسات، ويُسند إلى تاريخ الفجوة (ختم 20-10، شرط 2) ──
for off in (-1, 1, 3):
    man = [{"date": DATES[BONUS_I + off], "factor": 0.8, "kind": "bonus", "source": "اختبار"}]
    (R5, ap5, sk5, pend5), out5 = quiet(m.ca_plan_apply, "1030", EV["1030"], man, R1030)
    check("بند يدوي مزاح %+d جلسة ⇒ يُسند إلى تاريخ الفجوة ويُطبَّق بمعامله، والتعارض يُطبع" % off,
          [(a["date"], a["factor"], a["origin"]) for a in ap5] == [(BONUS_D, 0.8, "manual")]
          and "أُسند إلى تاريخ الفجوة" in out5 and "يخالف الكاشف" in out5 and not pend5)
man = [{"date": DATES[BONUS_I], "factor": 2.0, "kind": "capital-reduction", "source": "اختبار"}]
(R5, ap5, sk5, pend5), out5 = quiet(m.ca_plan_apply, "1030", EV["1030"], man, R1030)
check("بند يدوي معطوب (اتجاه معاكس) لم يُطبَّق وقد أسقط حدثاً ⇒ الحدث يعود معلّقاً بـ🚨",
      not ap5 and [p_["date"] for p_ in pend5] == [BONUS_D] and "🚨" in out5)
man = [{"date": DATES[BONUS_I + 10], "factor": 0.8, "kind": "bonus", "source": "اختبار"}]
(R5, ap5, sk5, pend5), out5 = quiet(m.ca_plan_apply, "1030", EV["1030"], man, R1030)
check("بند بعيد (10 جلسات) لا يُسقط الحدث: الآلي يُطبَّق والبند يُتخطّى",
      [(a["date"], a["origin"]) for a in ap5] == [(BONUS_D, "auto")] and sk5 and not pend5)
gap_day = DATES[BONUS_I]
Rhol = [r for r in R1030 if r[0] != DATES[BONUS_I - 1]]   # الجلسة السابقة عطلة
man = [{"date": DATES[BONUS_I - 1], "factor": 5 / 6, "kind": "bonus", "source": "اختبار"}]
(R5, ap5, sk5, pend5), out5 = quiet(m.ca_plan_apply, "1030", [], man, Rhol)
check("بند بتاريخ ليس جلسة ⇒ يُسند إلى أول جلسة بعده ويُطبَّق (ع3)",
      [a["date"] for a in ap5] == [gap_day] and "ليس جلسة" in out5)
for f_na in (1, 0.5):
    man_na = [{"date": BONUS_D, "factor": f_na, "kind": "no-adjust", "source": "اختبار"}]
    R6, ap6, sk6, pend6 = m.ca_plan_apply("1030", EV["1030"], man_na, R1030)
    check("no-adjust (معامل %s) يُسكت الكاشف عند تاريخه" % f_na,
          not ap6 and not pend6 and sk6[0]["why"] == "no-adjust" and R6 == R1030)

# ── 3ب) بند يدوي داخل حد التذبذب (4321: منحة 1:12، r ≈ 0.91) — مراجعة المحلل، ع1 ──
R4321 = series("4321", 15.95, [(BONUS_I, 12 / 13)])
EV4 = detect_all(universe(**{"4321": R4321}))
check("منحة 1:12 داخل الحد ⇒ لا يراها الكاشف", not EV4["4321"])
man = [{"date": BONUS_D, "factor": 12 / 13, "kind": "bonus", "source": "اختبار"}]
(R7, ap7, sk7, _), _o = quiet(m.ca_plan_apply, "4321", [], man, R4321)
check("والبند اليدوي يُطبَّق داخل الحد (يقرّب الفجوة من 1 بأكثر من نصف معامله)",
      [a["date"] for a in ap7] == [BONUS_D] and abs(R7[BONUS_I][1] / R7[BONUS_I - 1][1] - 1) < 0.015)
_, ap8, sk8, _ = m.ca_plan_apply("4321", [], man, R7)
check("وتطبيقه الثاني على المعدّل يُتخطّى", not ap8 and sk8)
Rn = series("NZ", 15.95, [(BONUS_I, 0.96)])
_, ap9, sk9, _ = m.ca_plan_apply("NZ", [], man, Rn)
check("وضجيج تداول 0.96 بعد تعديل المزوّد لا يكفي لتطبيق 12/13", not ap9 and sk9)

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
plan_b, pend_b, _sup, _meta = m.ca_resolve("B1", EVb["B1"], None, RB)
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
    check("corporate-actions.json في المستودع سليم (عشرة أسهم) بلا بند معطوب",
          sorted(real) == ["1030", "1080", "1120", "2200", "4004", "4200", "4321", "6040", "7202", "8010"]
          and "معطوب" not in out)
finally:
    shutil.rmtree(tmpd)

check("ca_factor_after_event: ما بعد d0 وحتى d1",
      m.ca_factor_after_event([{"date": "2026-09-01", "factor": 0.5}, {"date": "2026-10-01", "factor": 0.8}], "2026-08-31",
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
          'dataFault:     {"kind": "capaction-unadjusted", "date": "2026-08-24", "label": "أُغلق بعطب بيانات"},' in blocks[2]
          and "entryPriceAdj" not in blocks[2])
finally:
    shutil.rmtree(d)

# ══ 19) حالات ختم 20-10 ومراجعة المحلل ══
# q من المجمّد ضمن سماحية اتساقه (10%) لا يناقض A (شرط 3)
st_q = {"sharesHistory": [{"date": DATES[255], "lastSeen": DATES[255], "shares": 1.25e9 / 0.7848}],
        "valuationInputs": {"sharesOutstanding": 1.25e9, "marketCap": 1.25e9 * 14.5 * 1.06, "theirPrice": 14.5}}
EVq = detect_all(universe(**{"1030": R1030}), {"1030": st_q})
check("q=0.7848 من مجمّدٍ منحرف 6% ⇒ بلا معلومة، A يبقى آلياً (شرط 3)", EVq["1030"][0]["decision"] == "auto")
st_q2 = copy.deepcopy(st_q)
st_q2["sharesHistory"][0]["shares"] = 1.25e9 / 0.70
EVq2 = detect_all(universe(**{"1030": R1030}), {"1030": st_q2})
check("وq=0.70 (خارج 10%) ⇒ يناقض فيدوي", EVq2["1030"][0]["decision"] == "manual")
# ع2: حدث بعد أول تسجيل لعدد الأسهم ⇒ لا مجمّد
st_e2 = {"sharesHistory": [{"date": DATES[240], "lastSeen": DATES[260], "shares": 1.5e9}],
         "valuationInputs": {"sharesOutstanding": 1.25e9, "marketCap": 1.25e9 * 14.5, "theirPrice": 14.5}}
q, src = m.ca_q_for(st_e2, BONUS_D, [])
check("حدث بعد أول تسجيل في sharesHistory ⇒ المجمّد لا يُستعمل (ع2)", q is None and "أول تسجيل" in src)
st_e3 = copy.deepcopy(st_fz)
st_e3["valuationInputs"]["sharesAsOf"] = "2026-10-05"
check("sharesAsOf يحلّ محل ثابت اللقطة (حدث قبله ⇒ لا q)", m.ca_q_for(st_e3, "2026-10-01", [])[0] is None)
check("وتواريخ البنود اليدوية من «حدث آخر بين اللقطة والحدث»",
      m.ca_q_for(st_fz, "2026-10-01", ["2026-09-15"])[0] is None)
# الجماعية لا تكتب فوق الارتداد (بند 4)
mass_rev = {"R%d" % k: series("R%d" % k, 30 + k, [(200, 0.8), (201, 1.25)]) for k in range(6)}
EVmr = detect_all(universe(**mass_rev))
check("ارتداد جماعي ليوم واحد ⇒ يبقى N لا S (لا تعليق دائم)",
      all(x["grade"] == "N" for k in mass_rev for x in EVmr[k]))
# الملف اليدوي: مصفوفة في الأعلى، وقيمة ليست قائمة (شرط 8)
tmpd = tempfile.mkdtemp()
try:
    p8 = os.path.join(tmpd, "ca.json")
    json.dump([{"date": "2026-10-01"}], open(p8, "w"))
    r8, out8 = quiet(m.load_manual_actions, p8)
    check("مصفوفة في المستوى الأعلى ⇒ {} بإنذار لا انهيار", r8 == {} and "🚨" in out8)
    json.dump({"1": {"date": "2026-10-01", "factor": 0.5, "kind": "bonus", "source": "s"}}, open(p8, "w"))
    r8, out8 = quiet(m.load_manual_actions, p8)
    check("قيمة سهم كائنٌ لا قائمة ⇒ تُسقَط بطباعة", r8 == {} and "ليست قائمة" in out8)
finally:
    shutil.rmtree(tmpd)
check("ca_factor_after_event: الحدث في d0 لا يُحتسب، وفي d1 يُحتسب",
      m.ca_factor_after_event([{"date": "2026-09-01", "factor": 0.5}], "2026-09-01") == 1.0
      and m.ca_factor_after_event([{"date": "2026-09-01", "factor": 0.5}], "2026-08-01", "2026-09-01") == 0.5)

# المسار الكامل: الجزئي يقرأ المخزن من القرص، والجماعية، و«اختفى»، وsharesCapFactor القديم، والتوزيع اليومي
tmpd = tempfile.mkdtemp()
try:
    cdir = os.path.join(tmpd, "candles")
    os.makedirs(cdir)
    u = universe(**{"1030": R1030}, **mass)
    for s_, R in u.items():
        m.save_candles(cdir, s_, R)
    st_m0 = {"symbol": "M0"}
    _, outp = quiet(m.fetch_daily_and_derive, Api(), [st_m0], collections.defaultdict(int), cdir, tasi, "stamp", DATES[-1])
    check("تشغيل جزئي (--symbols) لسهم واحد من الوصلة ⇒ يرى البقية من القرص: S معلّق لا تطبيق",
          "capActions" not in st_m0 and st_m0.get("capActionsPending", [{}])[0].get("grade") == "S")
    st_old = {"symbol": "N00", "capActions": [{"date": "2026-01-01", "factor": 0.5}],
              "valuationInputs": {"sharesOutstanding": 1e6, "sharesCapFactor": 0.5}}
    st_div = {"symbol": "1030", "dividendEvents": [{"date": "2026-06-30", "amount": 0.6}],
              "valuationInputs": {"sharesOutstanding": 1.25e9, "divTtm12m": 0.6, "divBasis": "ttm12m"}}
    st_asof = {"symbol": "1030", "valuationInputs": {"sharesOutstanding": 1.25e9, "sharesAsOf": "2026-09-01"}}
    _, outg = quiet(m.fetch_daily_and_derive, Api(), [st_old, st_div], collections.defaultdict(int), cdir, tasi,
                    "stamp", DATES[-1])
    check("حدث كان مطبَّقاً واختفى ⇒ 🚨 ويُعدّ في «اختفت»",
          "كان مطبَّقاً واختفى" in outg and "اختفت 1" in outg and "capActions" not in st_old)
    check("sharesCapFactor قديم بلا حدث ⇒ يُحذف", "sharesCapFactor" not in st_old["valuationInputs"])
    check("التوزيع يُحمل على الأساس الحالي يومياً من الأحقيات المخزّنة (0.6 → 0.5) — بند 9",
          abs(st_div["valuationInputs"]["divTtm12m"] - 0.5) < 1e-6 and st_div["valuationInputs"]["divBasis"] == "ttm12m")
    quiet(m.fetch_daily_and_derive, Api(), [st_asof], collections.defaultdict(int), cdir, tasi, "stamp", DATES[-1])
    check("sharesAsOf بعد الحدث ⇒ لا sharesCapFactor (العدد على الأساس الجديد أصلاً)",
          "sharesCapFactor" not in st_asof["valuationInputs"] and st_asof.get("capActions"))
finally:
    shutil.rmtree(tmpd)

# سطر 🔎 لتغيّر الأسهم الذي لا يفسّره المطبَّق (مراجعة المحلل، بند 3)
st_w = {"symbol": "1820", "sharesHistory": [{"date": "2026-10-20", "lastSeen": "2026-10-20", "shares": 619.67e6}],
        "valuationInputs": {"sharesOutstanding": 315e6, "marketCap": 625.96e6 * 10, "theirPrice": 10}}
dev, outw = quiet(m.ca_shares_watch, st_w, R1030, [])
check("1820: تغيّر بلا فجوة ⇒ سطر 🔎 بوسم «المجمّد بائت»", dev is not None and "المجمّد بائت" in outw)
st_w2 = {"symbol": "1030", "sharesHistory": [{"date": "2026-10-20", "lastSeen": "2026-10-20", "shares": 1.5e9}],
         "valuationInputs": {"sharesOutstanding": 1.25e9}}
dev2, outw2 = quiet(m.ca_shares_watch, st_w2, R1030, [{"date": BONUS_D, "factor": 5 / 6}])
check("1030 بعد تطبيق 5/6 ⇒ لا سطر (المطبَّق يفسّره)", dev2 is None and not outw2)

# حارس الفترة الجزئية يأخذ العدد على الأساس الحالي (المجمّد ÷ sharesCapFactor)
seen = {}
orig_ppg = m.partial_period_guard
m.partial_period_guard = lambda st, prev, eps, shares, pm, today: seen.setdefault("shares", shares)
try:
    st_g = {"symbol": "1030", "sector": "Industrials", "industry": "x", "financials": {}, "guardRejected": [],
            "_prevFinancials": {}, "valuationInputs": {"sharesOutstanding": 1.25e9, "sharesCapFactor": 0.833333}}
    quiet(m.fetch_fundamentals, DivApi(), data, [st_g], collections.defaultdict(int), "2026-10-22", full_universe=False)
finally:
    m.partial_period_guard = orig_ppg
check("partial_period_guard يتلقى 1.25 مليار ÷ 0.833333 = 1.5 مليار", abs(seen.get("shares", 0) - 1.5e9) < 1e4)

# عدّاد تغيّر عدد الأسهم يقارن بآخر قيمة لا بطول السجل (ملاحظة ختم المرحلة 1)
hist12 = [{"date": "2026-01-%02d" % (i + 1), "lastSeen": "2026-01-%02d" % (i + 1), "shares": 1000 + i}
          for i in range(m.SHARES_HIST_MAX)]
st_c = {"symbol": "1030", "sector": "Industrials", "industry": "x", "financials": {}, "guardRejected": [],
        "_prevFinancials": {}, "sharesHistory": hist12}
_, outc = quiet(m.fetch_fundamentals, DivApi(), data, [st_c], collections.defaultdict(int), "2026-10-22",
                full_universe=False)
check("سجل عند سقفه (12) وقيمة جديدة ⇒ يُعدّ تغيّراً واحداً", "1 تغيّراً في عدد الأسهم" in outc)

# صفحة الدقة: حدث بعد الإغلاق، وحدث في يوم الدخول، وجلسة الدخول الفعلية (شرط 5)
d = tempfile.mkdtemp()
try:
    P = {k: os.path.join(d, k) for k in ("s.json", "c.json", "p.html", "cache.json", "t.json")}
    json.dump({"runType": "close", "lastUpdated": "2026-10-20 16:00", "stocks": [
        {"symbol": "1030", "currentPrice": 12.0, "capActions": [{"date": "2026-10-01", "factor": 0.833333}]}]},
        open(P["s.json"], "w"))
    json.dump({"stocks": [
        {"symbol": "1030", "name": "س", "entryPrice": 14.4, "entryDate": "2026-09-01", "track": "auto",
         "status": "closed", "closeDate": "2026-09-20", "closePrice": 14.0, "closeReason": "score_below_50"},
        {"symbol": "1030", "name": "س", "entryPrice": 12.1, "entryDate": "2026-10-01", "track": "auto"},
        {"symbol": "1030", "name": "س", "entryPrice": 14.5, "entryDate": "2026-09-26", "track": "auto"}]},
        open(P["c.json"], "w"))
    json.dump({"S|1030|2026-09-26": {"close": 12.11, "tradingDay": "2026-10-01", "fetchedAt": "x"},
               "D|1030|2026-09-26|" + __import__("datetime").datetime.now().strftime("%Y-%m-%d"): 0},
              open(P["cache.json"], "w"))
    open(P["p.html"], "w").write('<script>\nconst WATCHLIST = [\n];\nconst META = {updatedAt: "x"};\n</script>\n')
    json.dump({"data": []}, open(P["t.json"], "w"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("SAHMK")}
    env.update(STOCKS_JSON=P["s.json"], CONFIG_JSON=P["c.json"], HTML_FILE=P["p.html"],
               CACHE_FILE=P["cache.json"], TASI_HISTORY=P["t.json"])
    subprocess.run(["bash", os.path.join(ROOT, "scripts", "update-watchlist-accuracy.sh")], env=env,
                   capture_output=True, text=True)
    blocks = open(P["p.html"]).read().split("\n  {\n")[1:]
    check("مدخل أُغلق قبل الحدث ⇒ بلا entryPriceAdj", "entryPriceAdj" not in blocks[0])
    check("حدث في يوم الدخول نفسه ⇒ بلا entryPriceAdj (إغلاق ذلك اليوم بعد الحدث)", "entryPriceAdj" not in blocks[1])
    check("مدخل يوم غير تداولي وسعره من جلسة الحدث (tradingDay) ⇒ لا تعديل مزدوج",
          "entryPriceAdj" not in blocks[2] and "entryPrice:    12.11" in blocks[2])
finally:
    shutil.rmtree(d)

# feed-watchlist: MAE لا يُحدَّث على فجوة معلّقة ثم يُقاس على المعدّل (شرط 1)، ولا دخول جديد (بند 6)
e200 = {"symbol": "7202", "track": "auto", "status": "open", "category": "buy", "type": "buy",
        "entryPrice": 200.0, "entryDate": "2026-10-01", "maePct": 0.0}
w_day = {"symbol": "7202", "currentPrice": 101.0, "investmentScore": {"total": 70, "classCode": "hold"},
         "capActionsPending": [{"date": "2026-10-06", "r": 0.5, "grade": "W", "why": "x"}]}
cfg, out = run_feed({"runType": "close", "stocks": [w_day]}, {"stocks": [dict(e200)]})
check("يوم W (فجوة معلّقة): MAE لا يسجّل −49.5 الوهمي", cfg["stocks"][0]["maePct"] == 0.0)
ap_day = {"symbol": "7202", "currentPrice": 101.0, "investmentScore": {"total": 70, "classCode": "hold"},
          "capActions": [{"date": "2026-10-06", "factor": 0.5}]}
cfg2, _ = run_feed({"runType": "close", "stocks": [ap_day]}, cfg)
check("ثم بعد التطبيق: MAE على الدخول المعدّل (100) ⇒ يبقى 0.0", cfg2["stocks"][0]["maePct"] == 0.0)
vs = dict(e200, sampleType="value-shadow", category="value-shadow")
cfg3, _ = run_feed({"runType": "close", "stocks": [dict(ap_day, investmentScore={"filtered": True})]},
                   {"stocks": [vs]})
check("ظل القيمة: MAE على الدخول المعدّل كذلك", cfg3["stocks"][0]["maePct"] == 0.0)
newc = {"symbol": "1213", "currentPrice": 16.0, "investmentScore": {"total": 80, "classCode": "strong_buy"},
        "capActionsPending": [{"date": "2026-08-26", "r": 0.65, "grade": "C", "why": "x"}]}
cfg4, out4 = run_feed({"runType": "close", "stocks": [newc]}, {"stocks": []})
check("لا دخول جديد على سهم بفجوة معلّقة داخل نافذة المؤشرات", cfg4["stocks"] == [] and "لا دخول" in out4)
newc2 = dict(newc)
newc2.pop("capActionsPending")
cfg5, _ = run_feed({"runType": "close", "stocks": [newc2]}, {"stocks": []})
check("والسهم نفسه بلا فجوة معلّقة ⇒ يدخل (فالمنع من الفجوة وحدها) ويحمل priceBasisAtEntry",
      len(cfg5["stocks"]) == 1 and cfg5["stocks"][0].get("priceBasisAtEntry") == "capadj-v1")

# close_sma200w: تقريب «دخل فوق المتوسط» بسعر الدخول المعدّل
d = tempfile.mkdtemp()
try:
    sp, cp = os.path.join(d, "s.json"), os.path.join(d, "c.json")
    e3 = {"symbol": "7202", "track": "auto", "status": "open", "entryPrice": 200.0, "entryDate": "2026-10-01"}
    for caps, want in (([{"date": "2026-10-06", "factor": 0.5}], "كان سيُغلق 0"), ([], "كان سيُغلق 1")):
        json.dump({"runType": "close", "lastUpdated": "x", "stocks": [
            {"symbol": "7202", "currentPrice": 105.0, "weeklyTechnical": {"sma200w": 110.0}, "capActions": caps}]},
            open(sp, "w"))
        json.dump({"stocks": [dict(e3)]}, open(cp, "w"))
        env = dict(os.environ, STOCKS_JSON=sp, CONFIG_JSON=cp, ARCHIVE_DIR=d, DRY_RUN="1")
        out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "close_sma200w.py")], env=env,
                             capture_output=True, text=True).stdout
        check("close_sma200w: دخول 200 بعده منحة 1:1 والمتوسط 110 ⇒ %s" % want, want in out)
finally:
    shutil.rmtree(d)

# self-check-L1: الدالتان تقسمان على sharesCapFactor (تُستخرج الدوال من المصدر بلا تشغيله)
import ast
src_l1 = open(os.path.join(ROOT, "scripts", "self-check-L1.py")).read()
tree = ast.parse(src_l1)
ns = {}
keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in ("_cap_k", "_implied_eps", "_implied_eps_alt"))
        or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "SH_SANITY_TOL" for t in n.targets))]
exec(compile(ast.Module(body=keep, type_ignores=[]), "l1", "exec"), ns)
s_l1 = {"financials": {"netIncome": 3e9}, "valuationInputs": {"sharesOutstanding": 1.25e9, "marketCap": 1.25e9 * 14.5,
                                                             "theirPrice": 14.5, "sharesCapFactor": 0.833333}}
check("self-check: _implied_eps و_implied_eps_alt على العدد الحالي (3 مليار ÷ 1.5 مليار = 2.0)",
      abs(ns["_implied_eps"](s_l1) - 2.0) < 1e-4 and abs(ns["_implied_eps_alt"](s_l1) - 2.0) < 1e-4)

# إعادة ختم 20-10 (A): البند يرتبط بحدث جلسته أو بأقرب فجوة — لا بآخر حدث قريب
NB = N - 6
Rsn = series("SN", 14.5, [(NB, 5 / 6), (N - 2, 0.85)])
EVsn = detect_all(universe(SN=Rsn))
check("سيناريو الإسناد: منحة A ثم عطب W بعد 4 جلسات",
      [x["grade"] for x in EVsn["SN"]] == ["A", "W"])
for off, lbl in ((0, "البند على جلسة المنحة"), (1, "البند بعد المنحة بجلسة (العطب أبعد)")):
    man = [{"date": DATES[NB + off], "factor": 5 / 6, "kind": "bonus", "source": "اختبار"}]
    (Rs, aps, sks, pends), outs = quiet(m.ca_plan_apply, "SN", EVsn["SN"], man, Rsn)
    check("%s ⇒ يُطبَّق على المنحة، والعطب W يبقى معلّقاً" % lbl,
          [a["date"] for a in aps] == [DATES[NB]] and [p_["grade"] for p_ in pends] == ["W"])
man = [{"date": DATES[N - 3], "factor": 5 / 6, "kind": "bonus", "source": "اختبار"}]
(Rs, aps, sks, pends), outs = quiet(m.ca_plan_apply, "SN", EVsn["SN"], man, Rsn)
check("البند أقرب إلى العطب (بجلسة) ⇒ يرتبط به وحده، والمنحة A تبقى آلية",
      sorted((a["date"], a["origin"]) for a in aps)[0] == (DATES[NB], "auto"))
# تواريخ البنود اليدوية في «حدث آخر بين اللقطة والحدث» (ع2) — عبر ca_detect
st_x = {"sharesHistory": [{"date": DATES[255], "lastSeen": DATES[255], "shares": 1.5e9}],
        "valuationInputs": {"sharesOutstanding": 1.25e9, "marketCap": 1.25e9 * 14.5, "theirPrice": 14.5}}
mm0 = m.ca_market_median(universe(**{"1030": R1030}))
e_x = m.ca_detect("1030", R1030, mm0, st_x, DATES[0])
e_y = m.ca_detect("1030", R1030, mm0, st_x, DATES[0], [DATES[249]])
check("ca_detect: بند يدوي بين اللقطة والحدث يمنع q المجمّد", e_x[0]["q"] is not None and e_y[0]["q"] is None)
# المسار الكامل يطبع سطر 🔎 لتغيّر الأسهم الذي لا يفسّره المطبَّق
tmpd = tempfile.mkdtemp()
try:
    cdir = os.path.join(tmpd, "candles")
    os.makedirs(cdir)
    for s_, R in universe().items():
        m.save_candles(cdir, s_, R)
    st_sw = {"symbol": "N01", "sharesHistory": [{"date": "2026-10-20", "lastSeen": "2026-10-20", "shares": 2e6}],
             "valuationInputs": {"sharesOutstanding": 1e6}}
    _, outsw = quiet(m.fetch_daily_and_derive, Api(), [st_sw], collections.defaultdict(int), cdir, tasi, "stamp", DATES[-1])
    check("المسار الكامل: تغيّر أسهم بلا فجوة ⇒ سطر 🔎", "🔎 N01: عدد الأسهم" in outsw)
finally:
    shutil.rmtree(tmpd)
# ظل القيمة: لا دخول على فجوة معلّقة، ولا MAE ولا إغلاق ما دامت معلّقة بعد الدخول
vs_stock = {"symbol": "3020", "sector": "Materials", "currentPrice": 10.0,
            "investmentScore": {"filtered": True, "filterReason": "تحت SMA200W بدون إشارات انعكاس",
                                "axes": {"quality": 20}},
            "valuation": {"pe": 8.0}, "financials": {"ocf": 1e6}, "weeklyTechnical": {"sma200w": 12.0}}
base_d = {"runType": "close", "sectorMedians": {"Materials": {"peMedian": 15.0}}}
cfg6, _ = run_feed(dict(base_d, stocks=[vs_stock]), {"stocks": []})
check("ظل القيمة: السهم المؤهَّل يدخل (شاهد)", [e["sampleType"] for e in cfg6["stocks"]] == ["value-shadow"])
vs_p = dict(vs_stock, capActionsPending=[{"date": "2025-10-21", "r": 0.89, "grade": "B", "why": "x"}])
cfg7, _ = run_feed(dict(base_d, stocks=[vs_p]), {"stocks": []})
check("ظل القيمة: وبفجوة معلّقة داخل النافذة ⇒ لا دخول", cfg7["stocks"] == [])
vs_open = {"symbol": "3020", "track": "auto", "status": "open", "sampleType": "value-shadow", "category": "value-shadow",
           "type": "buy", "entryPrice": 20.0, "entryDate": "2025-08-09", "maePct": 0.0}
cfg8, _ = run_feed(dict(base_d, stocks=[dict(vs_p, capActionsPending=[{"date": "2025-10-21", "r": 0.5,
                                                                         "grade": "W", "why": "x"}])]),
                   {"stocks": [vs_open]})
check("ظل القيمة المفتوح بفجوة معلّقة بعد دخوله ⇒ لا MAE (لا −50 وهمي) ولا إغلاق",
      cfg8["stocks"][0]["maePct"] == 0.0 and cfg8["stocks"][0]["status"] == "open")

# وصلة 2023-11-27 (قرار المالك 20-10): بند يدوي على فجوة P قبل 2024-03 يُطبَّق على العمودين ولا يتكرر
Rsp = [["2023-11-%02d" % d, 30.0, 30.0, 30.3, 29.7, 1000] for d in range(1, 27)]
Rsp += [["2023-11-27", 20.0, 20.0, 20.2, 19.8, 1000]] + series("SPX", 20.0)
EVsp = detect_all(universe(SP=Rsp))
check("وصلة 2023-11-27 ⇒ درجة P لا تُطبَّق آلياً", EVsp["SP"][0]["grade"] == "P" and EVsp["SP"][0]["decision"] == "no")
man = [{"date": "2023-11-27", "factor": 2 / 3, "kind": "bonus", "source": "اختبار"}]
(Rsp2, apsp, sksp, pdsp), _ = quiet(m.ca_plan_apply, "SP", EVsp["SP"], man, Rsp)
check("والبند اليدوي عليها يُطبَّق على close وadjusted (30 → 20)",
      apsp and apsp[0]["cols"] == ["close", "adjusted"] and abs(Rsp2[0][1] - 20.0) < 1e-9 and abs(Rsp2[0][2] - 20.0) < 1e-9)
(_, apsp3, sksp3, _), _ = quiet(m.ca_plan_apply, "SP", EVsp["SP"], man, Rsp2)
check("ولا يتكرر إن وُجد المخزن معدّلاً (صحّح المزوّد لاحقاً)", not apsp3 and sksp3)

# ══ §8-ك: eventDate (وصلة المزوّد) — شروط ختم الدفعة الأولى ══
tmpd = tempfile.mkdtemp()
try:
    pe = os.path.join(tmpd, "ca.json")
    json.dump({"1": [{"date": "2023-11-27", "eventDate": "2026-04-21", "factor": 0.5, "kind": "bonus", "source": "s"},
                     {"date": "2023-11-27", "eventDate": "2023-11-26", "factor": 0.5, "kind": "bonus", "source": "s"},
                     {"date": "2023-11-27", "eventDate": "21-04-2026", "factor": 0.5, "kind": "bonus", "source": "s"}]},
              open(pe, "w"))
    re_, oute = quiet(m.load_manual_actions, pe)
    check("eventDate: يُقبل ≥ date، ويُسقط إن سبقه أو كان تالفاً",
          [it.get("eventDate") for it in re_["1"]] == ["2026-04-21"] and oute.count("بند معطوب") == 2)
    real, _ = quiet(m.load_manual_actions, os.path.join(ROOT, "corporate-actions.json"))
    check("الملف الحقيقي: eventDate لـ1080 و1120 و4200 وحدها",
          sorted(k for k, v in real.items() if v[0].get("eventDate")) == ["1080", "1120", "4200"])
finally:
    shutil.rmtree(tmpd)
man_ev = [{"date": "2023-11-27", "eventDate": "2026-04-21", "factor": 2 / 3, "kind": "bonus", "source": "s"}]
Rsp_ = [["2023-11-%02d" % d, 75.0, 75.0, 75.7, 74.3, 1000] for d in range(1, 27)]
Rsp_ += [["2023-11-27", 50.0, 50.0, 50.5, 49.5, 1000]] + series("SPY", 50.0)
(_, ap_ev, _, _), _ = quiet(m.ca_plan_apply, "1120", [], man_ev, Rsp_)
check("eventDate يُنقل إلى capActions المطبَّق", ap_ev and ap_ev[0].get("eventDate") == "2026-04-21"
      and ap_ev[0]["date"] == "2023-11-27")
tot, basis = m.div_ttm_capadj([("2026-04-20", 1.75), ("2026-09-21", 1.26)], ap_ev,
                              m.datetime(2026, 10, 20, tzinfo=m.timezone.utc), "2026-10-20")
check("1120: توزيع 1.75 قبل eventDate يُضرب بـ2/3، و1.26 بعده لا ⇒ 2.4267", abs(tot - 2.4267) < 1e-4)
tot2, _ = m.div_ttm_capadj([("2026-04-21", 1.75)], ap_ev, m.datetime(2026, 10, 20, tzinfo=m.timezone.utc), "2026-10-20")
check("وتوزيع أحقيته يوم eventDate نفسه لا يُضرب", abs(tot2 - 1.75) < 1e-9)
check("ca_factor_after_event على eventDate لا date (وdate وحده إن غاب)",
      abs(m.ca_factor_after_event(ap_ev, "2026-01-01") - 2 / 3) < 1e-6 and m.ca_factor_after_event(ap_ev, "2026-04-21") == 1.0
      and m.ca_factor_after_event([{"date": "2026-09-01", "factor": 0.5}], "2026-08-01") == 0.5)
# وصلة بعمود adjusted مختلف قبلها (1080: 0.973 × close) ⇒ يُطبَّق على العمودين
Radj = [["2023-11-%02d" % d, 23.88, round(23.88 * 0.973, 4), 24.1, 23.6, 1000] for d in range(1, 27)]
Radj += [["2023-11-27", 18.04, 18.04, 18.2, 17.9, 1000]] + series("ADJ", 18.04)
man_a = [{"date": "2023-11-27", "eventDate": "2024-05-21", "factor": 0.75, "kind": "bonus", "source": "s"}]
(Radj2, ap_a, _, _), out_a = quiet(m.ca_plan_apply, "1080", [], man_a, Radj)
check("adjusted قبل الوصلة = 0.973×close ⇒ البند على العمودين، وclose بلا قفزة متبقية",
      ap_a[0]["cols"] == ["close", "adjusted"] and abs(Radj2[25][1] - 23.88 * 0.75) < 1e-6 and "🚨" not in out_a)
# فجوة متبقية بعد البند ⇒ 🚨 (معامل ناقص)، ولا 🚨 لـ6040 الفعلي (−5.4% تداولاً)
Rres = Rsp_[:26] + [["2023-11-27", 37.5, 37.5, 37.9, 37.1, 1000]] + series("RES", 37.5)
_, out_r = quiet(m.ca_plan_apply, "X", [], man_ev, Rres)
check("بند 2/3 وفجوة 0.5 ⇒ 🚨 فجوة متبقية", "فجوة متبقية" in out_r)
R6040 = [["2026-09-%02d" % d, 8.99, 8.99, 9.0, 8.9, 1000] for d in range(1, 27)]
R6040 += [["2026-09-27", 43.52, 43.52, 47.97, 43.32, 1000]] + [["2026-09-28", 43.6, 43.6, 44.0, 43.0, 1000]]
_, out6 = quiet(m.ca_plan_apply, "6040", [], [{"date": "2026-09-27", "factor": 5.119482,
                                                "kind": "capital-reduction", "source": "s"}], R6040)
check("6040 الفعلي (−5.4% بعد البند) ⇒ لا 🚨", "🚨" not in out6)
# سعر الدخول بين date وeventDate يأخذ المعامل (feed وclose_sma200w وصفحة الدقة)
e1120 = {"symbol": "1120", "track": "auto", "status": "open", "category": "buy", "type": "buy",
         "entryPrice": 106.6, "entryDate": "2026-04-02", "maePct": 0.0}
st1120 = {"symbol": "1120", "currentPrice": 70.0, "investmentScore": {"total": 70, "classCode": "hold"},
          "capActions": [{"date": "2023-11-27", "eventDate": "2026-04-21", "factor": 0.666667}]}
cfgE, _ = run_feed({"runType": "close", "stocks": [st1120]}, {"stocks": [dict(e1120)]})
check("feed: دخول 106.6 قبل eventDate ⇒ على 71.07 فـ70 = −1.5% لا −34%", cfgE["stocks"][0]["maePct"] == -1.5)
d = tempfile.mkdtemp()
try:
    sp, cp = os.path.join(d, "s.json"), os.path.join(d, "c.json")
    json.dump({"runType": "close", "lastUpdated": "x", "stocks": [dict(st1120, weeklyTechnical={"sma200w": 80.0})]},
              open(sp, "w"))
    json.dump({"stocks": [{k: v for k, v in e1120.items() if k != "maePct"}]}, open(cp, "w"))
    env = dict(os.environ, STOCKS_JSON=sp, CONFIG_JSON=cp, ARCHIVE_DIR=d, DRY_RUN="1")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "close_sma200w.py")], env=env,
                         capture_output=True, text=True).stdout
    check("close_sma200w: دخول 106.6 × 2/3 = 71.07 تحت متوسط 80 ⇒ لم يدخل فوقه فلا إغلاق", "كان سيُغلق 0" in out)
    P = {k: os.path.join(d, k) for k in ("s2.json", "c2.json", "p.html", "cache.json", "t.json")}
    json.dump({"runType": "close", "lastUpdated": "2026-10-20 16:00", "stocks": [st1120]}, open(P["s2.json"], "w"))
    json.dump({"stocks": [{"symbol": "1120", "name": "ر", "entryPrice": 106.6, "entryDate": "2026-04-02",
                           "track": "legacy"}]}, open(P["c2.json"], "w"))
    open(P["p.html"], "w").write('<script>\nconst WATCHLIST = [\n];\nconst META = {updatedAt: "x"};\n</script>\n')
    json.dump({"data": []}, open(P["t.json"], "w"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("SAHMK")}
    env.update(STOCKS_JSON=P["s2.json"], CONFIG_JSON=P["c2.json"], HTML_FILE=P["p.html"],
               CACHE_FILE=P["cache.json"], TASI_HISTORY=P["t.json"])
    subprocess.run(["bash", os.path.join(ROOT, "scripts", "update-watchlist-accuracy.sh")], env=env,
                   capture_output=True, text=True)
    check("صفحة الدقة: مدخل 1120 القديم قبل eventDate ⇒ entryPriceAdj 71.0667",
          "entryPriceAdj: 71.0667," in open(P["p.html"]).read())
finally:
    shutil.rmtree(d)
cfgw = json.load(open(os.path.join(ROOT, "watchlist-config.json")))
f1080 = [e for e in cfgw["stocks"] if e["symbol"] == "1080" and e.get("track") == "auto"
         and e.get("entryDate") in ("2026-08-19", "2026-08-20")]
check("قرار المالك: مدخلا 1080 (08-19 و08-20) موسومان dataFault بوصلة المزوّد",
      len(f1080) == 2 and all((e.get("dataFault") or {}).get("kind") == "provider-splice" for e in f1080))

# JS: صفحة الدقة (entryPriceAdj وdataFault)، وimpliedEpsAlt، وisV3sc
js = subprocess.run(["node", os.path.join(HERE, "test_capadj_ui.js")], capture_output=True, text=True)
print(js.stdout.rstrip())
check("test_capadj_ui.js ⇒ خروج 0", js.returncode == 0)

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
