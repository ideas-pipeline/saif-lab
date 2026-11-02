#!/usr/bin/env python3
"""يبني index.html من template.html + stocks-data.json، وclassic.html من القالب الكلاسيكي.

ترقية 04-09 (قرار المالك): الصفحة الرئيسية صارت تجربة سيف الجديدة (مولّدة من uat.html
عبر scripts/make-template.py)، والنسخة السابقة تبقى حية على classic.html — جسر بنقرة
واحدة حتى تُسد فجواتها الأربعة، ومسار تراجع فوري.
"""
import json, os
d = os.path.dirname(os.path.abspath(__file__))
data = open(os.path.join(d, "stocks-data.json"), encoding="utf-8").read()
n = len(json.loads(data).get("stocks", []))


def load_sharia():
    """§8-هـ: التصنيف الشرعي — للعرض فقط. ملف مستقل لا يدخل stocks-data.json ولا التقييم.
    أي خلل فيه (غياب، JSON تالف، مخطط غير متوقع) ⇒ "{}" فتعرض الصفحة «—» ولا يتوقف البناء.
    يُضمَّن من الملف ما يخص أسهم المنصة وحدها، بحقلين {c,p} لا غير (ختم الناقد 02-11:
    أقل إعادة نشر للدراسة، ولا حقل غير متوقع يصل إلى <script>)."""
    path = os.path.join(d, "sharia.json")
    if not os.path.exists(path):
        return "{}", "غير موجود"
    try:
        sh = json.loads(open(path, encoding="utf-8").read())
        st = sh["stocks"]
        ok = isinstance(st, dict) and all(
            isinstance(k, str) and k.isascii() and k.isdigit() and len(k) == 4 and isinstance(v, dict)
            and v.get("c") in ("pure", "mixed", "non", "public")
            and isinstance(v.get("p"), (int, float)) and not isinstance(v.get("p"), bool)
            and 0 <= v["p"] <= 5
            for k, v in st.items())
        if not ok or not isinstance(sh.get("meta"), dict):
            raise ValueError("مخطط غير متوقع")
        syms = {str(s.get("symbol")) for s in json.loads(data).get("stocks", [])}
        keep = {k: {"c": v["c"], "p": v["p"]} for k, v in sorted(st.items()) if k in syms}
        meta = {k: sh["meta"][k] for k in ("source", "study", "url", "imported", "unit")
                if isinstance(sh["meta"].get(k), (str, int)) and not isinstance(sh["meta"].get(k), bool)}
        out = json.dumps({"meta": meta, "stocks": keep}, ensure_ascii=False, separators=(",", ":"))
        if "__STOCKS_DATA__" in out or "__SHARIA_DATA__" in out:
            raise ValueError("مرساة بناء داخل الملف")
        # «<» كله لا «</» وحده: «<!--<script» يُدخل المحلل حالة تبتلع </script> الحقيقي
        return out.replace("<", "\\u003c"), "%d سهماً من %d في الدراسة" % (len(keep), len(st))
    except Exception as e:  # noqa: BLE001 — العرض لا يُسقط البناء
        print("⚠️ sharia.json غير صالح (%s) — يُعرض «—»" % e)
        return "{}", "غير صالح"


sharia, sharia_note = load_sharia()

def build(tpl_name, out_name, label):
    path = os.path.join(d, tpl_name)
    if not os.path.exists(path):
        print("ℹ️ %s غير موجود — تخطي %s" % (tpl_name, out_name))
        return
    tpl = open(path, encoding="utf-8").read()
    if tpl.count("__STOCKS_DATA__") != 1:
        raise SystemExit("خطأ: __STOCKS_DATA__ يجب أن يظهر مرة واحدة في %s" % tpl_name)
    # الشرعي أولاً، ومخرجه مرفوض إن حمل أي مرساة (load_sharia) — فلا تتسرّب إليه البيانات
    has_sh = "__SHARIA_DATA__" in tpl
    if tpl.count("__SHARIA_DATA__") > 1:
        raise SystemExit("خطأ: __SHARIA_DATA__ مكرر في %s" % tpl_name)
    tpl = tpl.replace("__SHARIA_DATA__", sharia, 1)
    out = tpl.replace("__STOCKS_DATA__", data, 1)
    open(os.path.join(d, out_name), "w", encoding="utf-8").write(out)
    print("تم البناء [%s]: %d سهم | %d بايت%s" % (label, n, len(out),
          " | الشرعي: " + sharia_note if has_sh else ""))

build("template.html", "index.html", "سيف")
build("template-classic.html", "classic.html", "الكلاسيكية")
