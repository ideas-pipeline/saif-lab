#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص توافق سهمك — يُشغَّل على جهاز بشبكة مفتوحة (السيرفر)، لا يعمل من بيئة المختبر السحابية.

الاستخدام (المفتاح لا يُكتب في أي ملف داخل المستودع):
    SAHMK_KEY=shmk_live_xxx python3 scripts/sahmk-probe.py
  أو:
    python3 scripts/sahmk-probe.py /root/.sahmk.key

يطبع تقريراً مضغوطاً جاهزاً للصق: حالة المفتاح، حدود الاشتراك،
وإجابة الفجوات الثلاث (تاريخ تاسي، EV/EBITDA، نسب البنوك).
قراءة فقط — لا يكتب أي ملف ولا يعدل شيئاً.
"""
import json, os, sys, urllib.request, urllib.error

BASE = "https://api.sahmk.sa/api/v1"
KEY = os.environ.get("SAHMK_KEY") or (open(sys.argv[1]).read().strip() if len(sys.argv) > 1 else None)
if not KEY:
    sys.exit("❌ لا مفتاح: مرر SAHMK_KEY كمتغير بيئة أو مسار ملف المفتاح كمعامل")

RATE = {}

def call(path, params=""):
    """ترجع (status, json|نص مقتطع). تلتقط ترويسات الحدود من كل رد."""
    url = BASE + path + (("?" + params) if params else "")
    req = urllib.request.Request(url, headers={"X-API-Key": KEY, "User-Agent": "saif-lab-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            for h in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "X-Plan"):
                v = r.headers.get(h)
                if v: RATE[h] = v
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        return e.code, body
    except Exception as e:
        return None, str(e)[:200]

def keytree(obj, depth=0, max_depth=3):
    """شجرة مفاتيح مضغوطة بلا قيم — لمعرفة البنية دون إغراق المخرجات."""
    if depth >= max_depth or not isinstance(obj, dict):
        return "…" if isinstance(obj, (dict, list)) else type(obj).__name__
    out = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            out[k] = keytree(v, depth + 1, max_depth)
        elif isinstance(v, list):
            out[k] = [keytree(v[0], depth + 1, max_depth)] if v else []
        else:
            out[k] = type(v).__name__
    return out

def find_keys(obj, needles, path=""):
    """كل المسارات التي يحوي اسمها إحدى الكلمات المطلوبة، مع قيمتها."""
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if any(n in k.lower() for n in needles) and not isinstance(v, (dict, list)):
                hits.append(f"{p} = {v}")
            hits += find_keys(v, needles, p)
    elif isinstance(obj, list) and obj:
        hits += find_keys(obj[0], needles, path + "[0]")
    return hits

def section(title):
    print(f"\n{'='*8} {title} {'='*8}")

# 1) المفتاح والحدود
section("1) المفتاح + الأسعار الدفعية")
st, d = call("/quotes/", "identifiers=1010,2222,1180")
if st != 200:
    st, d = call("/quotes/", "symbols=1010,2222,1180")  # عقد قديم احتياطي
print("status:", st)
if isinstance(d, dict):
    qs = d.get("quotes", [])
    print("count:", d.get("count"), "| مفاتيح أول سعر:", sorted(qs[0].keys()) if qs else "—")
    if qs: print("عينة 1010:", {k: qs[0].get(k) for k in ("symbol", "price", "previous_close", "volume", "net_liquidity", "is_delayed", "updated_at")})
else:
    print("body:", d)

# 2) التاريخ السعري + adjusted_close
section("2) historical يومي وأسبوعي (2222)")
st, d = call("/historical/2222/", "interval=1d&from=2026-07-01&to=2026-08-04")
print("1d status:", st, end=" | ")
if isinstance(d, dict):
    bars = d.get("data", [])
    print("bars:", len(bars), "| مفاتيح الشمعة:", sorted(bars[0].keys()) if bars else "—")
else:
    print("body:", d)
st, d = call("/historical/2222/", "interval=1w&from=2022-06-01&to=2026-08-04")
print("1w status:", st, end=" | ")
if isinstance(d, dict):
    bars = d.get("data", [])
    print("bars:", len(bars), "(نحتاج ≥200 لـ SMA200W)", "| أول:", bars[0].get("date") if bars else "—", "| آخر:", bars[-1].get("date") if bars else "—")
else:
    print("body:", d)

# 3) الفجوة أ: تاريخ مؤشر تاسي
section("3) فجوة أ — تاريخ تاسي")
for ident in ("TASI", "tasi", "^TASI", "TASI.SR"):
    st, d = call(f"/historical/{ident}/", "interval=1d&from=2026-07-01")
    n = len(d.get("data", [])) if isinstance(d, dict) else 0
    print(f"historical/{ident}: status {st}, bars {n}")
    if st == 200 and n: break

# 4) الفجوة ب+ج: ratios — بنك وعام
section("4) فجوة ب+ج — analytics/ratios")
for sym, label in (("1180", "بنك"), ("2222", "عام")):
    st, d = call(f"/analytics/ratios/{sym}/", "history=latest&period=annual&metrics=all")
    if st != 200:
        st, d = call(f"/analytics/ratios/{sym}/", "history=latest&period=annual&metrics=core")
    print(f"\n--- {sym} ({label}) status:", st)
    if isinstance(d, dict):
        hits = find_keys(d, ["roa", "cost", "income_ratio", "efficiency", "ev", "ebitda", "pe", "pb", "price_to", "roe", "debt", "current_ratio", "margin"])
        print("\n".join(hits[:25]) or "(لا مفاتيح مطابقة — الشجرة أدناه)")
        if not hits: print(json.dumps(keytree(d), ensure_ascii=False)[:800])
    else:
        print("body:", d)

# 5) company — يكشف الخطة (أي الكتل حاضرة)
section("5) company/2222 — كتل حسب الخطة")
st, d = call("/company/2222/")
print("status:", st)
if isinstance(d, dict):
    for blk in ("fundamentals", "technicals", "valuation", "analysts"):
        v = d.get(blk)
        print(f"{blk}: {'✅ ' + str(sorted(v.keys())[:10]) if isinstance(v, dict) else '❌ غائب'}")

# 6) financials — مكونات نسب البنوك
section("6) financials/1180 — هل تكفي لاشتقاق Cost/Income وROA؟")
st, d = call("/financials/1180/", "history=latest")
print("status:", st)
if isinstance(d, dict):
    hits = find_keys(d, ["revenue", "operating", "expense", "net_income", "total_assets", "equity", "cash_flow", "ocf"])
    print("\n".join(hits[:20]) or json.dumps(keytree(d), ensure_ascii=False)[:800])

# 7) dividends + market summary
section("7) dividends/2222 + market/summary")
st, d = call("/dividends/2222/")
print("dividends status:", st, "| yield:", d.get("trailing_12m_yield") if isinstance(d, dict) else d, "| history:", len(d.get("history", [])) if isinstance(d, dict) else "—")
st, d = call("/market/summary/")
print("summary status:", st, "|", {k: d.get(k) for k in ("index_value", "advancing", "declining", "market_mood", "is_delayed")} if isinstance(d, dict) else d)

# الخلاصة
section("الحدود المرصودة (من الترويسات)")
print(RATE or "لم تصل ترويسات X-RateLimit — قد تظهر فقط عند الاقتراب من الحد")
print("\n✅ انتهى الفحص — الصق هذا المخرج كاملاً في المحادثة")
