#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص قدرة «مفكرة التوزيعات» (المرحلة 1) — هل يُدرج سهمك التوزيعات المعلنة المستقبلية؟

يُشغَّل على جهاز بشبكة مفتوحة (السيرفر) — لا يعمل من بيئة المختبر السحابية.
الاستخدام (المفتاح لا يُكتب في أي ملف داخل المستودع):
    SAHMK_KEY=shmk_live_xxx python3 scripts/sahmk-divcal-probe.py
  أو:
    python3 scripts/sahmk-divcal-probe.py /root/.sahmk.key

قراءة صرفة — لا يكتب أي ملف ولا يعدل شيئاً. مخرج مضغوط جاهز للصق.

عينة الاختبار المثالية (جدول المالك — أحقيات الأسبوع 14-20 أغسطس معروفة سلفاً):
  3010 أسمنت العربية: أحقية 2026-08-16 بـ0.50
  4190 جرير:          أحقية 2026-08-17 بـ0.20
  2222 أرامكو:        أحقية 2026-08-19 بـ0.3393
  4007 الحمادي القابضة: أحقية 2026-08-16 بـ0.27   (الرمز محسوم من بياناتنا)
  7203 علم:           «توزيع/إيداع» 2026-08-16 بـ5.00 — يختبر تفريق تاريخي الأحقية والإيداع
  2286 المطاحن الرابعة: أحقية 2026-08-20 بـ0.13   (الرمز محسوم من بياناتنا)

ميزانية الطلبات لو صارت جلبة التوزيعات يومية كاملة (+248 طلباً/يوم):
  الأعداد الفعلية من fetch-inputs-sahmk.py (main):
    يومي:   دفعات quotes ‏5 (248/50) + شموع 248 + تاسي/ملخص 2 ≈ 255 طلباً
    أسبوعي: يضيف الأساسيات 248×4 = 992 (وفيها /dividends/ مرة أسبوعياً أصلاً) ≈ 1247
    شهري:   صيانة الكون ~+3 (ترقيم /companies/)
  بعد الإضافة اليومية المقترحة (+248):
    يوم عادي ≈ 503/5000 (‏10.1%) | يوم أسبوعي ≈ 1495/5000 (‏29.9%) — هامش واسع،
    ومع سويعة 429 المعتادة يبقى السقف بعيداً. القرار النهائي بعد نتيجة هذا الفحص
    (إن كانت المستقبلية تظهر في الرد الأسبوعي القائم فلا حاجة لأي طلب إضافي أصلاً).
"""
import json, os, sys, urllib.request, urllib.error

BASE = "https://api.sahmk.sa/api/v1"
KEY = os.environ.get("SAHMK_KEY") or (open(sys.argv[1]).read().strip() if len(sys.argv) > 1 else None)
if not KEY:
    sys.exit("❌ لا مفتاح: مرر SAHMK_KEY كمتغير بيئة أو مسار ملف المفتاح كمعامل")

TODAY = "2026-08-14"
# (رمز، اسم، تاريخ الحدث المعروف، القيمة، نوع التاريخ المتوقع)
SAMPLE = [
    ("3010", "أسمنت العربية",    "2026-08-16", 0.50,   "أحقية"),
    ("4190", "جرير",             "2026-08-17", 0.20,   "أحقية"),
    ("2222", "أرامكو",           "2026-08-19", 0.3393, "أحقية"),
    ("4007", "الحمادي القابضة",  "2026-08-16", 0.27,   "أحقية"),
    ("7203", "علم",              "2026-08-16", 5.00,   "توزيع/إيداع"),
    ("2286", "المطاحن الرابعة",  "2026-08-20", 0.13,   "أحقية"),
]
DATEISH = ("date", "eligibility", "distribution", "announcement", "due", "ex_", "payment", "record")

RATE = {}

def call(path, params=""):
    """ترجع (status, json|نص مقتطع). تلتقط ترويسات الحدود من كل رد."""
    url = BASE + path + (("?" + params) if params else "")
    req = urllib.request.Request(url, headers={"X-API-Key": KEY, "User-Agent": "saif-lab-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            for h in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "X-Plan"):
                v = r.headers.get(h)
                if v:
                    RATE[h] = v
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        return e.code, body
    except Exception as e:
        return None, str(e)[:200]


def rows_of(resp):
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for k in ("history", "data", "results", "dividends"):
            if isinstance(resp.get(k), list):
                return resp[k]
    return []


def date_fields(rec):
    """كل حقول السجل التي يوحي اسمها بتاريخ، مع قيمها."""
    out = {}
    for k, v in rec.items():
        if any(n in k.lower() for n in DATEISH) and isinstance(v, str):
            out[k] = v
    return out


print("═" * 64)
print("فحص مفكرة التوزيعات — المستقبلية في /dividends/ | اليوم: %s" % TODAY)
print("═" * 64)

found_future = 0
all_fields = set()
for sym, name, ev_date, ev_val, ev_kind in SAMPLE:
    st, resp = call("/dividends/%s/" % sym, "limit=50")
    print("\n── %s %s (حدث معروف: %s ‏%s بـ%s) ──" % (sym, name, ev_kind, ev_date, ev_val))
    if st != 200 or not isinstance(resp, (dict, list)):
        print("  ✗ HTTP %s: %s" % (st, str(resp)[:150]))
        print("  الخلاصة: مستقبلية: لا (تعذر الجلب)")
        continue
    rows = rows_of(resp)
    if isinstance(resp, dict):
        env_keys = sorted(set(resp.keys()) - {"history", "data", "results"})
        if env_keys:
            print("  مفاتيح الغلاف:", env_keys)
    if not rows:
        print("  ✗ صفر سجلات — الشكل: %s" % (sorted(resp.keys()) if isinstance(resp, dict) else type(resp).__name__))
        print("  الخلاصة: مستقبلية: لا (لا سجلات)")
        continue
    # 1) كل مفاتيح أول سجلين — شجرة الحقول (announcement/distribution/status؟)
    for i, rec in enumerate(rows[:2]):
        all_fields.update(rec.keys())
        print("  سجل[%d] مفاتيحه: %s" % (i, sorted(rec.keys())))
    # 2) كل سجل فيه أي حقل تاريخ ≥ اليوم — بقيمه كاملة
    futures = []
    for rec in rows:
        dfs = date_fields(rec)
        if any(v[:10] >= TODAY for v in dfs.values()):
            futures.append(rec)
    if futures:
        for rec in futures[:4]:
            print("  ⏩ سجل مستقبلي كامل:", json.dumps(rec, ensure_ascii=False))
    # 3) خلاصة آلية: هل ظهر الحدث المعروف؟
    hit = None
    for rec in futures:
        dfs = date_fields(rec)
        val = rec.get("value", rec.get("amount"))
        if any(v[:10] == ev_date for v in dfs.values()):
            hit = (dfs, val)
            break
    if hit:
        found_future += 1
        match_val = "بقيمة مطابقة" if (hit[1] is not None and abs(float(hit[1]) - ev_val) < 0.005) \
                    else "⚠️ قيمة مختلفة (%s ≠ %s)" % (hit[1], ev_val)
        print("  الخلاصة: مستقبلية: نعم (%s %s ‏%s — حقول تاريخه: %s)"
              % (ev_kind, ev_date, match_val, hit[0]))
    elif futures:
        print("  الخلاصة: مستقبلية: جزئياً — سجلات مستقبلية موجودة لكن حدث %s المعروف غائب" % ev_date)
    else:
        print("  الخلاصة: مستقبلية: لا (كل السجلات تاريخية)")

# 4) استكشاف حذر للمعاملات المحتملة — على رمز واحد فقط (طلبان إضافيان)
print("\n── استكشاف معاملات (2222 حصراً — طلبان) ──")
base_n = len(rows_of(call("/dividends/2222/", "limit=50")[1] or {}))
for params in ("upcoming=true", "status=upcoming"):
    st, resp = call("/dividends/2222/", params)
    n = len(rows_of(resp)) if st == 200 else None
    print("  ?%s → HTTP %s | سجلات: %s (الأساس بلا معامل: %s)%s"
          % (params, st, n, base_n,
             " — سلوك مختلف يستحق نظرة" if (n is not None and n != base_n) else ""))

print("\n" + "═" * 64)
print("الخلاصة النهائية: ظهرت المستقبلية المعروفة لدى %d/%d من العينة" % (found_future, len(SAMPLE)))
print("الحقول المكتشفة عبر العينة: %s" % sorted(all_fields))
print("حقول التواريخ المرشحة للتفريق (أحقية/إيداع/إعلان): %s"
      % sorted(f for f in all_fields if any(n in f.lower() for n in DATEISH)))
if RATE:
    print("ترويسات الحدود: %s" % RATE)
print("═" * 64)
