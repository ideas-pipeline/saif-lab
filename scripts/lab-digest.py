#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lab-digest.py — التقرير الأسبوعي الوصفي (الطبقة 2 من خطة المراقبة، اعتماد المالك 05-08ب).

تقرير وصفي خالص: قراءة فقط من stocks-data.json وwatchlist-config.json —
صفر شبكة، صفر حسابات تقييم جديدة (أي رقم غير موجود في الملفات لا يُخترع بل
يُعلن غيابه نصاً). يكتب docs/weekly-digest.md ولقطة موجزة .digest-prev.json
للمقارنة الأسبوعية — كتابة ذرية للاثنين.

بنداً المحلل المقران (05-08ب):
  1. عدّاد تجويع العينة: أسابيع منذ آخر مدخل جديد — إنذار نصي عند ≥4 أسابيع
     في نظام غير هابط أو ≥8 مطلقاً.
  2. اتجاه عدادات الحراس لا أعدادها: رفض كل حقل مقارناً بالأسبوع السابق
     (من اللقطة) — أي تصاعد يُبرز إنذاراً مبكراً لعلل المصدر.

شروط الناقد الملزمة (ختم 05-08ب):
  1. توزيع النقاط: وسيط/ربيعيات/أعلى-أدنى 10 بالأسماء — نسخ وترتيب لا حساب جديد.
  2. مدخلات العينة الجديدة (7 أيام) بالاسم والفئة وregimeAtEntry — مميزة عن المفتوحة.
  3. تاريخ نظام السوق الأسبوعي: سجل متراكم في اللقطة (regimeLog) + أسابيع كل نظام
     + السلسلة المتصلة + سطر «محفز م-4» الصريح (غير هابط مستقر ≥4 أسابيع).
  4. قسم شذوذ بعنوان صريح (البند 6)، وتشغيلة معادة لليوم نفسه لا تستبدل لقطة الدلتا.

فشل مسموع (خروج 1 قبل أي كتابة): ملف بلا بصمة تشغيلة v3 (scoringStats/
coverage/priceSource=sahmk-direct-v3) — التقرير يقرأ ناتج الخط ولا يعيد حسابه.
ملف المختبر الحالي بعقد v2.1 → الفشل عليه هو السلوك الصحيح الموثق حتى أول
تشغيلة v3 حقيقية على السيرفر.

الاستخدام:
  python3 scripts/lab-digest.py --data /path/stocks-data.json \
      [--config /path/watchlist-config.json] [--out docs/weekly-digest.md]
"""
import argparse, json, os, sys
from collections import Counter
from datetime import datetime

CODE_LABELS = (
    ("strong_buy", "⭐⭐⭐ شراء قوي"), ("buy", "⭐⭐ شراء"),
    ("buy_wait", "⭐⭐ شراء-انتظر"), ("conditional_buy", "⭐ مشروط"),
    ("hold", "⏳ انتظار"), ("sell", "🔻 بيع"), ("strong_sell", "🔻🔻 بيع قوي"),
    ("unrated", "⏸ غير مُقيَّم"), ("filtered", "⛔ مستبعد"),
)
BUY_FAMILY = ("strong_buy", "buy", "buy_wait", "conditional_buy")


def atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def age_days(stamp):
    try:
        return (datetime.now() - datetime.strptime(str(stamp)[:10], "%Y-%m-%d")).days
    except (ValueError, TypeError):
        return None


def main():
    ap = argparse.ArgumentParser(description="التقرير الأسبوعي الوصفي (طبقة المراقبة 2)")
    ap.add_argument("--data", required=True, help="مسار stocks-data.json (إلزامي — لا افتراضيات)")
    ap.add_argument("--config", default="", help="مسار watchlist-config.json (افتراضي: بجوار --data)")
    ap.add_argument("--out", default="docs/weekly-digest.md")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    cfg_path = args.config or os.path.join(os.path.dirname(os.path.abspath(args.data)),
                                           "watchlist-config.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    # ── بصمة v3 — فشل مسموع قبل أي كتابة ──
    stats = (data.get("scoringStats") or {}).get("counts")
    missing = []
    if stats is None:
        missing.append("scoringStats")
    if not data.get("coverage"):
        missing.append("coverage")
    if data.get("priceSource") != "sahmk-direct-v3":
        missing.append("priceSource=%s" % data.get("priceSource"))
    if missing:
        print("⛔ lab-digest: الملف بلا بصمة تشغيلة v3 (%s) — التقرير الوصفي يقرأ ناتج"
              " الخط ولا يعيد حسابه. شغّل جالب v3 والمحرك أولاً." % "، ".join(missing))
        sys.exit(1)

    S = [s for s in data.get("stocks", []) if s.get("symbol") and not s.get("delisted")]
    today_dt = datetime.now()
    today = today_dt.strftime("%Y-%m-%d")
    prev_path = os.path.join(os.path.dirname(os.path.abspath(args.out)) or ".",
                             ".digest-prev.json")
    prev = {}
    if os.path.exists(prev_path):
        try:
            prev = json.load(open(prev_path, encoding="utf-8"))
        except Exception:
            prev = {}
    has_prev = bool(prev.get("counts"))

    L = []   # أسطر التقرير

    # ═══ الرأس ═══
    L.append("# التقرير الأسبوعي الوصفي — مختبر سيف تداول (criteria v3)")
    L.append("")
    L.append("**تقرير وصفي — لا يعدل شيئاً ولا يوصي بتعديل.**")
    L.append("")
    L.append("| | |")
    L.append("|---|---|")
    L.append("| تاريخ التقرير | %s |" % today)
    L.append("| التشغيلة | runType=%s (‏%s) |" % (data.get("runType"), data.get("runTypeAt")))
    L.append("| بيانات | lastUpdated=%s — priceSource=%s |" % (data.get("lastUpdated"), data.get("priceSource")))
    L.append("| المعايير | scoringVersion=%s / criteriaVersion=%s |" % (data.get("scoringVersion"), data.get("criteriaVersion")))
    L.append("| المقارنة | %s |" % ("مع لقطة %s" % prev.get("at") if has_prev
                                     else "لا لقطة سابقة — هذه أساس المقارنة"))
    L.append("")

    # ═══ 1) التوزيع والتغير الأسبوعي — من scoringStats حرفياً ═══
    L.append("## 1. توزيع الفئات (من scoringStats حرفياً) والتغير الأسبوعي")
    L.append("")
    L.append("| الفئة | العدد | الأسبوع السابق | Δ |")
    L.append("|---|---|---|---|")
    pc = prev.get("counts") or {}
    for code, label in CODE_LABELS:
        n = stats.get(code, 0)
        if has_prev:
            p = pc.get(code, 0)
            L.append("| %s | %d | %d | %+d |" % (label, n, p, n - p))
        else:
            L.append("| %s | %d | — | — |" % (label, n))
    L.append("| **المجموع (كون المحرك)** | **%d** | %s | |" % (
        (data.get("scoringStats") or {}).get("universe", sum(stats.values())),
        prev.get("universe", "—") if has_prev else "—"))
    L.append("")

    # توزيع النقاط (شرط الناقد 1): نسخ وترتيب لا حساب جديد — totals المقيَّمين من الملف
    rated_sc = sorted(((s.get("investmentScore") or {}).get("total"), s["symbol"], s.get("name", ""))
                      for s in S
                      if (s.get("investmentScore") or {}).get("filtered") is False
                      and (s.get("investmentScore") or {}).get("classCode") != "unrated"
                      and (s.get("investmentScore") or {}).get("total") is not None)
    L.append("### توزيع النقاط (المقيَّمون، n=%d)" % len(rated_sc))
    if rated_sc:
        arr = [x[0] for x in rated_sc]
        n = len(arr)
        L.append("- وسيط %s | ‏Q1 (الربيع الأدنى) %s | ‏Q3 (الربيع الأعلى) %s | المدى %s-%s"
                 % (arr[n // 2] if n % 2 else round((arr[n//2 - 1] + arr[n//2]) / 2, 1),
                    arr[n // 4], arr[(3 * n) // 4], arr[0], arr[-1]))
        top10 = list(reversed(rated_sc[-10:]))
        bot10 = rated_sc[:10]
        L.append("- **أعلى 10:** " + "، ".join("%s %s (%s)" % (sym, name, sc) for sc, sym, name in top10))
        L.append("- **أدنى 10:** " + "، ".join("%s %s (%s)" % (sym, name, sc) for sc, sym, name in bot10))
    else:
        L.append("- لا مقيَّمين في الملف.")
    L.append("")

    # عائلة الشراء بالأسماء + الاستقرار
    fam = [(s["symbol"], s.get("name", ""),
            (s.get("investmentScore") or {}).get("classCode"),
            (s.get("investmentScore") or {}).get("total"))
           for s in S if (s.get("investmentScore") or {}).get("classCode") in BUY_FAMILY]
    fam.sort(key=lambda x: (BUY_FAMILY.index(x[2]), -(x[3] or 0)))
    L.append("### عائلة الشراء بالأسماء (%d)" % len(fam))
    if fam:
        L.append("")
        L.append("| الرمز | الاسم | الفئة | النقاط |")
        L.append("|---|---|---|---|")
        for sym, name, code, tot in fam:
            L.append("| %s | %s | %s | %s |" % (sym, name, dict(CODE_LABELS).get(code, code), tot))
    else:
        L.append("لا أسهم في عائلة الشراء هذا الأسبوع.")
    fam_syms = [x[0] for x in fam]
    if has_prev:
        prev_fam = prev.get("buyFamily") or []
        entered = [x for x in fam_syms if x not in prev_fam]
        left = [x for x in prev_fam if x not in fam_syms]
        L.append("")
        L.append("**استقرار العائلة:** دخل %d %s | خرج %d %s | ثابت %d"
                 % (len(entered), entered or "", len(left), left or "",
                    len([x for x in fam_syms if x in prev_fam])))
    L.append("")

    # ═══ 2) حالة العينة ═══
    L.append("## 2. حالة العينة (watchlist-config)")
    L.append("")
    wl = cfg.get("stocks", [])
    # عينة الظل الثانية (قيمة-تحت-الفلتر) مسار مستقل — تُستثنى من عدادات العينة الرسمية
    # وعدّاد التجويع (دخولها لا يطفئ جوع العينة الرسمية) ولها سطرها الخاص أدناه
    vs_all = [e for e in wl if e.get("sampleType") == "value-shadow"]
    auto = [e for e in wl if e.get("track") == "auto" and e.get("sampleType") != "value-shadow"]
    opens = [e for e in auto if e.get("status", "open") == "open"]
    closed = [e for e in auto if e.get("status") == "closed"]
    samp = lambda e: "ظل" if e.get("category") == "buy_wait" else "مطبقة"
    oc = Counter((samp(e), e.get("category", "؟")) for e in opens)
    L.append("- مفتوحة: %d (%s) | مغلقة تراكمياً: %d" % (
        len(opens),
        "، ".join("%s/%s: %d" % (k[0], k[1], v) for k, v in sorted(oc.items())) or "لا شيء",
        len(closed)))
    # مدخلات العينة الجديدة هذا الأسبوع (شرط الناقد 2) — تُميز عن المفتوحة الإجمالية
    new_entries = [e for e in auto if (age_days(e.get("entryDate")) or 99) <= 7]
    if new_entries:
        L.append("- **مدخلات جديدة هذا الأسبوع (%d):**" % len(new_entries))
        for e in new_entries:
            L.append("  - %s %s — فئة %s، النظام عند الدخول: %s (نقاط %s)" % (
                e.get("symbol"), e.get("name", ""), e.get("category"),
                e.get("regimeAtEntry", "غير مسجل"), e.get("scoreAtEntry")))
    else:
        L.append("- لا مدخلات جديدة خلال 7 أيام.")
    new_closed = [e for e in closed if (age_days(e.get("closeDate")) or 99) <= 7]
    if new_closed:
        L.append("- إغلاقات الأسبوع (%d):" % len(new_closed))
        for e in new_closed:
            L.append("  - %s %s: ‏%s → %s (سبب: %s)" % (
                e.get("symbol"), e.get("name", ""), e.get("entryPrice"),
                e.get("closePrice"), e.get("closeReason")))
    else:
        L.append("- لا إغلاقات جديدة خلال 7 أيام.")
    # العائد الزائد الجاري — من حقول المدخلات حصراً (عقد measurement v3)
    ex_open = [e.get("excessNet") for e in opens if e.get("excessNet") is not None]
    ex_closed = [e.get("excessNet") for e in closed if e.get("excessNet") is not None]
    if ex_open or ex_closed:
        if ex_open:
            L.append("- متوسط العائد الزائد الجاري (مفتوحة، n=%d): ‏%+.2f%%"
                     % (len(ex_open), sum(ex_open) / len(ex_open)))
        if ex_closed:
            L.append("- متوسط العائد الزائد (مغلقة، n=%d): ‏%+.2f%%"
                     % (len(ex_closed), sum(ex_closed) / len(ex_closed)))
    else:
        L.append("- العائد الزائد: حقول excessNet غير متوفرة في المدخلات — لا يُحسب بديل"
                 " (يظهر حين يكتبها خط القياس).")

    # سطر عينة الظل الثانية (قيمة-تحت-الفلتر — ظل بحثي)
    vs_open = [e for e in vs_all if e.get("status", "open") == "open"]
    vs_ex = [e.get("excessNet") for e in vs_open if e.get("excessNet") is not None]
    if vs_all:
        L.append("- **ظل القيمة (بحثي — ليست توصيات):** مفتوحة %d | مغلقة %d | متوسط الزائد الجاري: %s"
                 % (len(vs_open), len(vs_all) - len(vs_open),
                    ("‏%+.2f%% (n=%d)" % (sum(vs_ex) / len(vs_ex), len(vs_ex))) if vs_ex
                    else "غير متوفر بعد"))

    # ── بند المحلل 1: عدّاد تجويع العينة ──
    regime = (data.get("marketRegime") or {}).get("regime", "")
    entry_dates = [e.get("entryDate") for e in auto if e.get("entryDate")]
    last_entry = max(entry_dates) if entry_dates else None
    if last_entry:
        d = age_days(last_entry)
        weeks_since = (d // 7) if d is not None else None
        line = "- **تجويع العينة:** آخر مدخل جديد %s — ‏%s أسبوعاً (أيام: %s) | النظام: %s" % (
            last_entry, weeks_since, d, regime or "؟")
        L.append(line)
        if weeks_since is not None and (weeks_since >= 8 or (weeks_since >= 4 and regime != "هابط")):
            L.append("  - ⚠️ **إنذار تجويع (حارس المحلل 1):** ‏%d أسابيع بلا مدخل جديد%s —"
                     " راجع عتبات الدخول مقابل حالة السوق" % (
                         weeks_since,
                         " في نظام غير هابط" if weeks_since < 8 else " (يتجاوز 8 مطلقاً)"))
    else:
        started = cfg.get("activatedAt")
        if started:
            d = age_days(started)
            weeks_since = (d // 7) if d is not None else None
            L.append("- **تجويع العينة:** لا مدخلات منذ تفعيل العينة (%s — ‏%s أسبوعاً) | النظام: %s"
                     % (started, weeks_since, regime or "؟"))
            if weeks_since is not None and (weeks_since >= 8 or (weeks_since >= 4 and regime != "هابط")):
                L.append("  - ⚠️ **إنذار تجويع (حارس المحلل 1):** عينة فارغة منذ ‏%d أسابيع" % weeks_since)
        else:
            L.append("- **تجويع العينة:** عينة فارغة بلا تاريخ تفعيل مسجل (activatedAt=null) —"
                     " العدّاد يبدأ من أول مدخل أو من تسجيل التفعيل.")
    L.append("")

    # ═══ 3) طبقة الدخول ونظام السوق ═══
    L.append("## 3. طبقة الدخول ونظام السوق")
    L.append("")
    mr = data.get("marketRegime") or {}
    L.append("- النظام: %s %s — %s (تاسي %s، ‏%s%% عن SMA200D)" % (
        mr.get("icon", ""), mr.get("regime", "غير متوفر"), mr.get("advice", ""),
        mr.get("indexValue", "؟"), mr.get("pctVsSma", "؟")))
    rated = [s for s in S
             if (s.get("investmentScore") or {}).get("filtered") is False
             and (s.get("investmentScore") or {}).get("classCode") != "unrated"]
    ec = Counter(((s["investmentScore"].get("entry") or {}).get("displayState") or "بلا طبقة دخول")
                 for s in rated)
    order = {"green": "🟢 دخول الآن", "yellow": "🟡 تدريجي", "red": "🔴 انتظر", "neutral": "⚪ محايد"}
    parts = ["%s: %d" % (order.get(k, k), ec[k]) for k in
             list(order) + [k for k in ec if k not in order]
             if k in ec]
    L.append("- توزيع الدخول للمقيَّمين (n=%d): %s" % (len(rated), " | ".join(parts) or "لا مقيَّمين"))
    if ec.get("بلا طبقة دخول"):
        L.append("  - ملاحظة: %d مقيَّماً بلا حقل entry — بيانات أقدم من عقد v3 لهذا الجزء (لا يُخترع)"
                 % ec["بلا طبقة دخول"])
    L.append("")

    # ── قسم الانعكاس (اجتماع 11-08 — ملف أدلة م-3: عتبة RSI>50 في فلتر الانعكاس) ──
    REV_REASON = "تحت SMA200W لكن إشارات انعكاس"
    rev = [s for s in S if (s.get("investmentScore") or {}).get("filterReason") == REV_REASON]
    rev_syms = sorted(s["symbol"] for s in rev)
    L.append("### قسم الانعكاس «الاتجاه لم يثبت بعد» (ملف أدلة م-3)")
    L.append("- أعضاء اليوم: %d — قفزة الأحد سلوك متوقع لا علة: المؤشرات الأسبوعية"
             " تتحدث جماعياً عند اكتمال كل أسبوع فيُتوقع churn صباح أول جلسة بعده." % len(rev))
    if rev:
        L.append("")
        L.append("| الرمز | النقاط | مسافة الاستعادة | حالة الحجم (vol20/vol50) |")
        L.append("|---|---|---|---|")
        for s in sorted(rev, key=lambda x: -((x.get("investmentScore") or {}).get("total") or 0)):
            wt_ = s.get("weeklyTechnical") or {}
            dx_ = s.get("dailyExtra") or {}
            dist = ("%+.1f%%" % ((s.get("currentPrice") / wt_["sma200w"] - 1) * 100)
                    if s.get("currentPrice") and wt_.get("sma200w") else "—")
            vt = (round(dx_["avgVol20"] / dx_["avgVol50"], 2)
                  if dx_.get("avgVol20") and dx_.get("avgVol50") else "—")
            L.append("| %s | %s | %s | %s |" % (
                s["symbol"], (s.get("investmentScore") or {}).get("total"), dist, vt))
        secs = Counter(s.get("sector") or "؟" for s in rev)
        L.append("")
        L.append("- التركيبة القطاعية: " + "، ".join("%s: %d" % kv for kv in secs.most_common()))
    prev_rev = prev.get("reversalMembers")
    if prev_rev is not None:
        ent_r = [x for x in rev_syms if x not in prev_rev]
        left_r = [x for x in prev_rev if x not in rev_syms]
        L.append("- تقلب العضوية أسبوعياً: دخل %d %s | خرج %d %s | ثابت %d"
                 % (len(ent_r), ent_r or "", len(left_r), left_r or "",
                    len([x for x in rev_syms if x in prev_rev])))
    else:
        L.append("- تقلب العضوية: لا لقطة سابقة — هذه أساس المقارنة.")
    L.append("")

    # ── تاريخ النظام الأسبوعي (شرط الناقد 3 — مصدر محفز م-4) ──
    same_day_rerun = prev.get("at") == today
    regime_log = list(prev.get("regimeLog") or [])
    cur_regime = mr.get("regime") or "غير متوفر"
    if same_day_rerun and regime_log and regime_log[-1].get("date") == today:
        pass   # تشغيلة معادة — السجل ثابت
    else:
        regime_log.append({"date": today, "regime": cur_regime})
    L.append("### تاريخ نظام السوق الأسبوعي (مصدر محفز م-4)")
    rc = Counter(e.get("regime") for e in regime_log)
    L.append("- النظام الحالي: %s | أسابيع كل نظام منذ التفعيل (بعدد تشغيلات digest): %s"
             % (cur_regime, "، ".join("%s: %d" % kv for kv in sorted(rc.items())) or "—"))
    streak = 0
    for e in reversed(regime_log):
        if e.get("regime") == cur_regime:
            streak += 1
        else:
            break
    L.append("- طول السلسلة الحالية المتصلة: %d أسبوعاً (%s)" % (streak, cur_regime))
    nonbear = 0
    for e in reversed(regime_log):
        if e.get("regime") and e["regime"] != "هابط":
            nonbear += 1
        else:
            break
    m4 = nonbear >= 4
    L.append("- **محفز م-4: %s** (نظام غير هابط مستقر ≥4 أسابيع — الحالي: %d متصلة غير هابطة)"
             % ("محقق ✅" if m4 else "غير محقق", nonbear))
    L.append("")

    # ═══ 4) عدادات الصحة والشذوذ ═══
    L.append("## 4. عدادات الصحة")
    L.append("")
    n_unrated = stats.get("unrated", 0)
    if has_prev:
        pu = prev.get("unrated")
        delta = ("Δ %+d عن الأسبوع السابق (%s)" % (n_unrated - pu, pu)) if pu is not None else ""
        L.append("- unrated: ‏%d %s — الانكماش الرتيب متوقع (نمو التاريخ الأسبوعي)؛ أي **زيادة** تستحق نظرة."
                 % (n_unrated, delta))
    else:
        L.append("- unrated: ‏%d — الانكماش الرتيب متوقع (نمو التاريخ الأسبوعي)؛ أي زيادة تستحق نظرة." % n_unrated)
    cov = data.get("coverage") or {}
    L.append("- التغطية (من data.coverage حرفياً): SMA200W=%s | قادرو Z=%s | بتاريخ %s"
             % (cov.get("smaCapable"), cov.get("zCapable"), cov.get("at")))
    stale_fin = sum(1 for s in S if (age_days(s.get("financialsUpdated")) or 0) > 10)
    stale_daily = sum(1 for s in S
                      if (age_days((s.get("dailyExtra") or {}).get("updatedAt")) or 0) > 3)
    L.append("- أعمار الكتل: financials أقدم من 10 أيام: %d | dailyExtra أقدم من 3 أيام: %d"
             % (stale_fin, stale_daily))
    L.append("")

    # ═══ 5) الشذوذ — عنوان صريح (شرط الناقد 4-أ، البند 6 من عقد الطبقة 2) ═══
    L.append("## 5. الشذوذ (البند 6 من عقد الطبقة 2)")
    L.append("")
    rej = Counter()
    for s in S:
        for g in (s.get("guardRejected") or []):
            rej[g.get("field")] += 1
    prev_rej = prev.get("guardByField") or {}
    if rej or prev_rej:
        L.append("- الحراس الراسبون بالحقل (الاتجاه مقابل الأسبوع السابق — حارس المحلل 4):")
        rising = []
        for fld in sorted(set(rej) | set(prev_rej), key=lambda x: str(x)):
            now_n, prev_n = rej.get(fld, 0), prev_rej.get(fld, 0)
            trend = ""
            if has_prev:
                trend = " (سابق %d، ‏Δ %+d)" % (prev_n, now_n - prev_n)
                if now_n > prev_n:
                    rising.append((fld, prev_n, now_n))
            L.append("  - %s: ‏%d%s" % (fld, now_n, trend))
        if rising:
            L.append("  - ⚠️ **تصاعد رفض (إنذار مبكر لعلل المصدر):** %s"
                     % "، ".join("%s ‏%d→%d" % r for r in rising))
    else:
        L.append("- الحراس الراسبون: لا رفض هذا الأسبوع%s." % (" ولا السابق" if has_prev else ""))
    if has_prev and prev.get("unrated") is not None and n_unrated > prev["unrated"]:
        L.append("- ⚠️ **شذوذ:** unrated زاد (%d→%d) والمتوقع انكماش رتيب — راجع عمق السلاسل"
                 % (prev["unrated"], n_unrated))
    L.append("")
    L.append("---")
    L.append("*مولد آلياً من scripts/lab-digest.py — قراءة فقط من stocks-data.json"
             " وwatchlist-config.json؛ كل الأعداد من scoringStats/coverage/الملفات حرفياً.*")
    L.append("")

    # ═══ الكتابة الذرية: التقرير ثم اللقطة ═══
    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    atomic_write(args.out, "\n".join(L))
    # شرط الناقد 4-ب: تشغيلة معادة لليوم نفسه لا تستبدل لقطة الدلتا (أساس المقارنة
    # الأسبوعي يبقى) — وسجل الأنظمة المتراكم محفوظ كما هو في هذه الحالة
    if same_day_rerun:
        print("ℹ️ lab-digest: تشغيلة معادة لليوم نفسه (%s) — لقطة الدلتا محفوظة بلا استبدال" % today)
    else:
        snap = {"at": today, "counts": dict(stats),
                "universe": (data.get("scoringStats") or {}).get("universe"),
                "buyFamily": fam_syms, "unrated": n_unrated,
                "guardByField": {str(k): v for k, v in rej.items()},
                "reversalMembers": rev_syms,
                "regimeLog": regime_log}
        atomic_write(prev_path, json.dumps(snap, ensure_ascii=False, indent=1))
    print("✅ lab-digest: كُتب %s (ذرياً)%s | فئات المحرك: %s"
          % (args.out, "" if same_day_rerun else " + لقطة " + os.path.basename(prev_path),
             dict(stats)))


if __name__ == "__main__":
    main()
