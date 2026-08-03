#!/usr/bin/env python3
"""يبني index.html من template.html + stocks-data.json"""
import json, os
d = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(d, "template.html"), encoding="utf-8").read()
data = open(os.path.join(d, "stocks-data.json"), encoding="utf-8").read()
if tpl.count("__STOCKS_DATA__") != 1:
    raise SystemExit("خطأ: __STOCKS_DATA__ يجب أن يظهر مرة واحدة")
out = tpl.replace("__STOCKS_DATA__", data, 1)
open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(out)
n = len(json.loads(data).get("stocks", []))
print("تم البناء: %d سهم | %d بايت" % (n, len(out)))
