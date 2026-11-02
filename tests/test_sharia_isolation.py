#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§8-ق التصنيف الشرعي — اختبارات العزل والمستورد والبناء.

المبدأ (قرار المالك 02-11): للعرض فقط. لا يقرأه محرك التقييم ولا الجلب ولا أي حساب.
الاستخدام: python3 tests/test_sharia_isolation.py
"""
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = F = 0


def ok(c, m):
    global P, F
    if c:
        P += 1
        print("  ✅ " + m)
    else:
        F += 1
        print("  ❌ " + m)


def load_importer():
    s = importlib.util.spec_from_file_location("shimp", os.path.join(ROOT, "scripts", "sharia-import.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


print("(أ) لا مرجع للتصنيف الشرعي في الحساب")
CALC = ["scripts/scoring-engine.py", "scripts/fetch-inputs-sahmk.py", "scripts/self-check-L1.py",
        "scripts/compute-valuation.py", "scripts/fetch-valuation-inputs.py", "scripts/lab-digest.py",
        "scripts/lab-watch.py", "scripts/fetch-news.py", "scripts/run-lab.sh"]
pat = re.compile(r"sharia|shariah|شرعي|تطهير", re.I)
for f in CALC:
    src = io.open(os.path.join(ROOT, f), encoding="utf-8").read()
    ok(not pat.search(src), "%s لا يذكر sharia/الشرعي/التطهير" % f)
data = json.load(io.open(os.path.join(ROOT, "stocks-data.json"), encoding="utf-8"))
ok(not any(k.lower().startswith("sharia") for s in data.get("stocks", []) for k in s)
   and "sharia" not in data, "stocks-data.json لا يحمل حقلاً شرعياً (الملف مستقل)")

print("(ب) محرك التقييم: المخرج نفسه بايتاً بايتاً بوجود sharia.json وبغيابه")


def run_engine(with_sharia):
    d = tempfile.mkdtemp(prefix="shr-eng-")
    try:
        shutil.copytree(os.path.join(ROOT, "scripts"), os.path.join(d, "scripts"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        for f in ("stocks-data.json", "corporate-actions.json", "tasi-history.json", "watchlist-config.json"):
            if os.path.exists(os.path.join(ROOT, f)):
                shutil.copy(os.path.join(ROOT, f), d)
        if with_sharia:
            shutil.copy(os.path.join(ROOT, "sharia.json"), d)
        r = subprocess.run([sys.executable, "-B", "scripts/scoring-engine.py", "stocks-data.json"],
                           cwd=d, capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, TZ="Asia/Riyadh"))
        h = hashlib.sha256(open(os.path.join(d, "stocks-data.json"), "rb").read()).hexdigest()
        return r.returncode, h
    finally:
        shutil.rmtree(d, ignore_errors=True)


a, b = run_engine(True), run_engine(False)
ok(a[0] == 0 and b[0] == 0, "المحرك يعمل في الحالتين (رمز %s/%s)" % (a[0], b[0]))
ok(a[1] == b[1], "المخرج متطابق بايتاً بايتاً (%s…)" % a[1][:12])

print("(ج) build.py: غياب الملف أو تلفه لا يُسقط البناء")
SAFE_STATES = []


def build_with(content):
    d = tempfile.mkdtemp(prefix="shr-bld-")
    try:
        shutil.copy(os.path.join(ROOT, "build.py"), d)
        open(os.path.join(d, "stocks-data.json"), "w").write('{"stocks":[{"symbol":"2222"}]}')
        open(os.path.join(d, "template.html"), "w").write(
            "<script>const A=__SHARIA_DATA__;const B=__STOCKS_DATA__;</script>")
        if content is not None:
            open(os.path.join(d, "sharia.json"), "w", encoding="utf-8").write(content)
        r = subprocess.run([sys.executable, "-B", "build.py"], cwd=d, capture_output=True, text=True)
        out = open(os.path.join(d, "index.html"), encoding="utf-8").read() if r.returncode == 0 else ""
        return r.returncode, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


rc, out = build_with(None)
ok(rc == 0 and "const A={};" in out, "بلا sharia.json ⇒ {}")
rc, out = build_with("{not json")
ok(rc == 0 and "const A={};" in out, "JSON تالف ⇒ {}")
rc, out = build_with(json.dumps({"meta": {}, "stocks": {"2222": {"c": "halal", "p": 0.05}}}))
ok(rc == 0 and "const A={};" in out, "تصنيف خارج القائمة ⇒ {}")
rc, out = build_with(json.dumps({"meta": {}, "stocks": {"2222": {"c": "pure", "p": 99}}}))
ok(rc == 0 and "const A={};" in out, "مبلغ تطهير خارج النطاق ⇒ {}")
rc, out = build_with(json.dumps({"meta": {"source": "x</script><b>", "study": 2025},
                                 "stocks": {"2222": {"c": "public", "p": 0.05}}}, ensure_ascii=False))
ok(rc == 0 and '"2222":{"c":"public","p":0.05}' in out and "</script><b>" not in out,
   "صالح ⇒ مضمَّن، و«</» مُهرَّب داخل <script>")
rc, out = build_with(json.dumps({"meta": {"evil": "__STOCKS_DATA__"}, "stocks": {}}))
ok(rc == 0 and out.count('{"stocks":[{"symbol":"2222"}]}') == 1,
   "حقول meta غير المعروفة تُسقط (لا مرساة بيانات تتسرّب)")
tpl = io.open(os.path.join(ROOT, "template.html"), encoding="utf-8").read()
ok(tpl.count("__SHARIA_DATA__") == 1, "template.html فيه المرساة مرة واحدة")
ok("__SHARIA_DATA__" not in io.open(os.path.join(ROOT, "template-classic.html"), encoding="utf-8").read(),
   "الكلاسيكية لم تُمس")

print("(د) المستورد")
M = load_importer()
GOOD = "\n".join([
    "رئيسي 0.05 الطاقة راجع المنهجية فقرة ١٨ شركة الزيت أرامكو السعودية 2222 1",
    "رئيسي 0.00 المواد الأساسية نقية شركة أسمنت أم القرى أم القرى 3005 2",
    "موازي 0.02 الرعاية الصحية )موازي( مختلطة شركة س س 9610 3",
    "رئيسي 0.01 المواد الأساسية غير متوافقة شركة تكوين تكوين 1201 3",   # تكرار تسلسل من المصدر
    "نص منهجية فيه 2025 و 12",                                         # ليس صف جدول
])
rows, errs = M.parse_rows(GOOD)
ok(not errs and rows == {"2222": {"c": "public", "p": 0.05, "m": "main"},
                         "3005": {"c": "pure", "p": 0.0, "m": "main"},
                         "9610": {"c": "mixed", "p": 0.02, "m": "nomu"},
                         "1201": {"c": "non", "p": 0.01, "m": "main"}},
   "صفوف سليمة: التصنيفات الأربعة والسوقان، والتسلسل المكرر لا يُفشل")
_, errs = M.parse_rows(GOOD.replace(" 3005 2", " 3005 5"))
ok(any("فجوات" in e for e in errs), "فجوة في التسلسل ⇒ خطأ")
_, errs = M.parse_rows(GOOD + "\nرئيسي 0.03 الطاقة نقية شركة ص ص 3005 4")
ok(any("مكرر" in e for e in errs), "رمز مكرر ⇒ خطأ")
_, errs = M.parse_rows(GOOD.replace("0.00 المواد", "0.00 0.04 المواد"))
ok(any("ملتبس" in e for e in errs), "مبلغان في صف ⇒ ملتبس")
_, errs = M.parse_rows(GOOD.replace("0.05 الطاقة", "7.50 الطاقة"))
ok(any("خارج النطاق" in e for e in errs), "مبلغ تطهير > 5 ريال ⇒ خطأ")
ok(M.parse_rows("مختلطة مختلطة نقية")[0] == {}, "سطر بلا «الرمز التسلسل» في آخره ليس صف جدول")
r1, _ = M.parse_rows("رئيسي 0.10 الطاقة غير متوافقة شركة ز ز 4084 1")
ok(r1["4084"]["c"] == "non", "«غير متوافقة» تُطابق قبل غيرها")

tmpd = tempfile.mkdtemp(prefix="shr-imp-")
try:
    ref = os.path.join(tmpd, "ref.json")
    json.dump({"stocks": [{"code": "2222", "sharia_opinion": "نقية", "purification": "0.05"},
                          {"code": "3005", "sharia_opinion": "نقية", "purification": "0.00"},
                          {"code": "9610", "sharia_opinion": "مختلطة", "purification": "0.02"},
                          {"code": "1201", "sharia_opinion": "غير متوافقة", "purification": "0.01"}]},
              open(ref, "w"), ensure_ascii=False)
    rows, _ = M.parse_rows(GOOD)
    bad, n = M.cross_check(rows, ref)
    ok(bad == [] and n == 4, "المطابقة: القطاع العام «نقية» في المرجع ليس خلافاً")
    j = json.load(open(ref))
    j["stocks"][1]["purification"] = "0.30"
    json.dump(j, open(ref, "w"), ensure_ascii=False)
    bad, _ = M.cross_check(rows, ref)
    ok(len(bad) == 1 and "3005" in bad[0], "المطابقة تلتقط اختلاف المبلغ")

    txt = os.path.join(tmpd, "s.txt")
    open(txt, "w", encoding="utf-8").write(GOOD)
    out = os.path.join(tmpd, "o.json")
    r = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "scripts", "sharia-import.py"),
                        "--txt", txt, "--study", "2025", "--url", "https://almaqased.net/x.pdf",
                        "--out", out], capture_output=True, text=True)
    ok(r.returncode != 0 and not os.path.exists(out), "أقل من 200 صف ⇒ لا كتابة")
    r = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "scripts", "sharia-import.py"),
                        "--txt", txt, "--study", "2025", "--url", "https://evil.example/x.pdf",
                        "--out", out], capture_output=True, text=True)
    ok(r.returncode != 0 and not os.path.exists(out), "رابط من غير almaqased.net ⇒ رفض")
finally:
    shutil.rmtree(tmpd, ignore_errors=True)

print("(هـ) الملف المرفوع")
sh = json.load(io.open(os.path.join(ROOT, "sharia.json"), encoding="utf-8"))
st = sh["stocks"]
ok(sh["meta"]["study"] == 2025 and sh["meta"]["url"].startswith("https://almaqased.net/")
   and len(st) == sh["meta"]["n"] == 382, "الدراسة 2025، 382 شركة، الرابط الرسمي")
ok(st["2222"] == {"c": "public", "p": 0.05} and st["3005"] == {"c": "pure", "p": 0.0}
   and st["2370"] == {"c": "mixed", "p": 0.02}, "عينات: أرامكو، أم القرى، مسك")
BANKS = ["1010", "1020", "1030", "1050", "1060", "1080", "1120", "1140", "1150", "1180"]
ok(not any(b in st for b in BANKS), "البنوك العشرة خارج الدراسة")

print("\n" + ("❌ " if F else "✅ ") + "%d نجحت، %d فشلت" % (P, F))
sys.exit(1 if F else 0)
