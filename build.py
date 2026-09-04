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

def build(tpl_name, out_name, label):
    path = os.path.join(d, tpl_name)
    if not os.path.exists(path):
        print("ℹ️ %s غير موجود — تخطي %s" % (tpl_name, out_name))
        return
    tpl = open(path, encoding="utf-8").read()
    if tpl.count("__STOCKS_DATA__") != 1:
        raise SystemExit("خطأ: __STOCKS_DATA__ يجب أن يظهر مرة واحدة في %s" % tpl_name)
    out = tpl.replace("__STOCKS_DATA__", data, 1)
    open(os.path.join(d, out_name), "w", encoding="utf-8").write(out)
    print("تم البناء [%s]: %d سهم | %d بايت" % (label, n, len(out)))

build("template.html", "index.html", "سيف")
build("template-classic.html", "classic.html", "الكلاسيكية")
