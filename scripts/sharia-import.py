#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""استيراد التصنيف الشرعي (§8-ق) — للعرض فقط، لا يدخل أي حساب.

المصدر: الدراسة السنوية لمركز المقاصد (إشراف د. محمد بن سعود العصيمي) لقوائم الشركات
المالية السنوية المدققة — ملف PDF واحد في السنة (عادةً أغسطس). لكل شركة: الرأي الشرعي
(نقية / مختلطة / غير متوافقة / «راجع المنهجية» لشركات القطاع العام كأرامكو) ومبلغ
التطهير للسهم الواحد **بالريال** (لا نسبة). البنوك خارج الدراسة (لها هيئاتها الشرعية).

العزل (قرار المالك 02-11): المخرج ملف مستقل `sharia.json` لا يُكتب في stocks-data.json،
فمحرك التقييم وسكربتات الجلب لا تراه أصلاً؛ يقرؤه build.py ويضمّنه في الصفحة للعرض.

الاستخدام (على الخادم — almaqased.net لا يُبلغ من بيئة السحابة):
  pdftotext -layout study.pdf study.txt
  python3 scripts/sharia-import.py --txt study.txt --study 2025 \
      --url https://almaqased.net/wp-content/uploads/2026/financial-statements-study-2025.pdf \
      [--check-json final_2025.json] [--data stocks-data.json] [--out sharia.json] [--dry]

  --check-json: استخراج طرف ثالث (github.com/anqorithm/naqa-api/sources) للمطابقة فقط؛
  أي اختلاف فوق 2% يوقف الكتابة.
"""
import argparse
import datetime
import io
import json
import os
import re
import sys
import unicodedata

LABELS = (("غير متوافقة", "non"), ("مختلطة", "mixed"), ("نقية", "pure"),
          ("راجع المنهجية", "public"))
JSON_LABELS = {"نقية": "pure", "مختلطة": "mixed", "غير متوافقة": "non"}
BIDI = re.compile("[‎‏‪-‮⁦-⁩]")
ROW = re.compile(r"(?<![\d.])(\d{4})\s+(\d{1,4})\s*$")       # «… الرمز التسلسل» آخر السطر
AMT = re.compile(r"(?<![\d.])(\d{1,2}\.\d{2})(?![\d.])")
MAX_P = 5.0        # ريال/سهم — أعلى من هذا خطأ استخراج لا تطهير
MAX_MISMATCH = 0.02


def norm(line):
    return BIDI.sub("", unicodedata.normalize("NFKC", line))


def parse_rows(text):
    """يعيد {code: {"c","p","m"}} وقائمة أخطاء. يُفشل عند أي صف ملتبس."""
    out, seqs, errs = {}, [], []
    for raw in text.splitlines():
        line = norm(raw).strip()
        m = ROW.search(line)
        if not m:
            continue
        head = line[:m.start()]
        amts = AMT.findall(head)
        labs = [c for k, c in LABELS if k in head]
        first = (head.split() or [""])[0]
        market = {"رئيسي": "main", "موازي": "nomu"}.get(first)
        if market is None:
            continue                       # ليس صف جدول (نص منهجية فيه رقم)
        code, seq = m.group(1), int(m.group(2))
        if len(amts) != 1 or len(labs) != 1:
            errs.append("%s: صف ملتبس (مبالغ %d، تصنيفات %d)" % (code, len(amts), len(labs)))
            continue
        p = float(amts[0])
        if not 0 <= p <= MAX_P:
            errs.append("%s: مبلغ تطهير خارج النطاق %s" % (code, amts[0]))
            continue
        if code in out:
            errs.append("%s: رمز مكرر" % code)
            continue
        out[code] = {"c": labs[0], "p": p, "m": market}
        seqs.append(seq)
    # فجوة في التسلسل = صف ضاع في الاستخراج. أما التكرار فمن الدراسة نفسها (2025: الرقم 367
    # لشركتين مختلفتين، 9610 و1201) فلا يُفشل؛ تفرّد الرمز هو الحارس.
    if seqs and set(seqs) != set(range(1, max(seqs) + 1)):
        gaps = sorted(set(range(1, max(seqs) + 1)) - set(seqs))
        errs.append("فجوات في التسلسل %s — صفوف ضائعة في الاستخراج" % gaps[:10])
    return out, errs


def cross_check(rows, path):
    ref = json.load(io.open(path, encoding="utf-8"))
    ref = ref.get("stocks", ref) if isinstance(ref, dict) else ref
    bad = []
    for r in ref:
        code = str(r.get("code", "")).strip()
        mine = rows.get(code)
        if mine is None:
            bad.append("%s: في المرجع لا في الدراسة" % code)
            continue
        c = JSON_LABELS.get(str(r.get("sharia_opinion", "")).strip())
        try:
            p = round(float(r.get("purification")), 2)
        except (TypeError, ValueError):
            p = None
        # «راجع المنهجية» (القطاع العام) يرد في المرجع «نقية» — تبسيط منه لا خلاف
        if (c != mine["c"] and not (mine["c"] == "public" and c == "pure")) or p != mine["p"]:
            bad.append("%s: الدراسة %s/%.2f ≠ المرجع %s/%s" % (code, mine["c"], mine["p"], c, p))
    extra = set(rows) - {str(r.get("code", "")).strip() for r in ref}
    bad += ["%s: في الدراسة لا في المرجع" % c for c in sorted(extra)]
    return bad, len(ref)


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--txt", required=True, help="ناتج pdftotext -layout لدراسة المقاصد")
    ap.add_argument("--study", required=True, type=int, help="سنة القوائم المالية المدروسة (مثل 2025)")
    ap.add_argument("--url", required=True, help="رابط ملف الدراسة الرسمي (يُعرض مع كل تصنيف)")
    ap.add_argument("--check-json", default="", help="استخراج طرف ثالث للمطابقة (اختياري)")
    ap.add_argument("--data", default="", help="stocks-data.json لتقرير التغطية فقط (قراءة)")
    ap.add_argument("--out", default=os.path.join(root, "sharia.json"))
    ap.add_argument("--dry", action="store_true", help="تحقق وتقرير بلا كتابة")
    a = ap.parse_args()

    if not a.url.startswith("https://almaqased.net/"):
        sys.exit("⛔ الرابط يجب أن يكون من almaqased.net")
    rows, errs = parse_rows(io.open(a.txt, encoding="utf-8").read())
    if errs:
        sys.exit("⛔ الاستخراج غير سليم — لا كتابة:\n  " + "\n  ".join(errs[:20]))
    if len(rows) < 200:
        sys.exit("⛔ %d صفاً فقط — ليس جدول الدراسة؟ لا كتابة" % len(rows))
    cnt = {}
    for r in rows.values():
        cnt[r["c"]] = cnt.get(r["c"], 0) + 1
    print("📗 الدراسة %d: %d شركة — %s" % (a.study, len(rows),
          " · ".join("%s %d" % (k, v) for k, v in sorted(cnt.items()))))

    if a.check_json:
        bad, n = cross_check(rows, a.check_json)
        share = len(bad) / max(n, 1)
        print("🔁 المطابقة مع المرجع: %d اختلاف من %d (%.1f%%)" % (len(bad), n, 100 * share))
        for b in bad[:10]:
            print("   · " + b)
        if share > MAX_MISMATCH:
            sys.exit("⛔ الاختلاف فوق %d%% — لا كتابة" % int(100 * MAX_MISMATCH))

    if a.data:
        d = json.load(io.open(a.data, encoding="utf-8"))
        syms = [str(s.get("symbol")) for s in d.get("stocks", []) if s.get("symbol") and not s.get("delisted")]
        miss = [s for s in syms if s not in rows]
        print("🧭 التغطية: %d من %d سهماً في المنصة؛ خارج الدراسة: %s"
              % (len(syms) - len(miss), len(syms), " ".join(miss) or "لا شيء"))

    out = {"meta": {"source": "مركز المقاصد — د. محمد بن سعود العصيمي",
                    "study": a.study, "url": a.url,
                    "imported": datetime.date.today().isoformat(), "n": len(rows),
                    "unit": "ريال للسهم", "note": "للعرض فقط — لا يدخل تقييم سيف"},
           "stocks": {k: {"c": v["c"], "p": v["p"]} for k, v in sorted(rows.items())}}
    if a.dry:
        print("🧪 --dry: لا كتابة")
        return
    tmp = a.out + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
        f.write("\n")
    os.replace(tmp, a.out)
    print("💾 كُتب %s (%d بايت)" % (a.out, os.path.getsize(a.out)))


if __name__ == "__main__":
    main()
