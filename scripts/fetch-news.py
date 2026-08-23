#!/usr/bin/env python3
"""جالب الأخبار اليومي — يحدّث حقل news[] حصراً (+ ختم newsUpdatedAt).

السياق (22-08): الأخبار كان يكتبها fetch-stock-analysis.sh (العالم القديم) غير المجدول
في run-lab.sh فتجمدت منذ 29-07. هذا السكربت يرث استعلامه حرفياً (Google News RSS
العربي: "{الاسم} سهم") ويعزل الكتابة: أي حقل غير news يُرفض بحارس مطابقة قانونية
كنهج divcal — فشل جلب سهمٍ يُبقي أخباره القديمة كما هي (لا مسح).

الاستخدام: python3 scripts/fetch-news.py --data stocks-data.json [--limit N]
"""
import argparse
import copy
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RATE_SLEEP = 1.0   # ~250 طلباً بمهلة ثانية — احترام للمصدر المجاني
TIMEOUT = 8
PER_STOCK = 3      # كما في السكربت القديم


def fetch_news(stock_name):
    """استعلام السكربت القديم حرفياً: '{الاسم} سهم' على Google News العربي"""
    try:
        query = "%s سهم" % stock_name
        url = ("https://news.google.com/rss/search?q=%s&hl=ar&gl=SA&ceid=SA:ar"
               % urllib.parse.quote(query))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        root = ET.fromstring(resp.read())
        news = []
        for item in root.findall(".//item")[:PER_STOCK]:
            g = lambda tag: (item.find(tag).text or "") if item.find(tag) is not None else ""
            news.append({"title": g("title")[:100], "date": g("pubDate"),
                         "source": g("source"), "url": g("link")})
        return news
    except Exception:
        return None  # فشل ⇒ لا مساس بالقديم


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--limit", type=int, default=0, help="لأغراض الاختبار: أول N سهماً فقط")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    baseline = copy.deepcopy(data)

    stocks = [s for s in data.get("stocks", []) if s.get("symbol") and not s.get("delisted")]
    if args.limit:
        stocks = stocks[: args.limit]

    ok = fail = 0
    for s in stocks:
        news = fetch_news(s.get("name") or s["symbol"])
        if news:
            s["news"] = news
            ok += 1
        else:
            fail += 1
        time.sleep(RATE_SLEEP)

    if ok == 0:
        print("⛔ الأخبار: صفر نجاح من %d — لا كتابة (تبقى الأخبار القديمة بختمها)" % len(stocks))
        sys.exit(1)

    data["newsUpdatedAt"] = time.strftime("%Y-%m-%d %H:%M")

    # حارس العزل: لا يتغير شيء خارج news[] وnewsUpdatedAt — أي فرق آخر يجهض الكتابة
    chk_new = copy.deepcopy(data)
    chk_old = copy.deepcopy(baseline)
    chk_new.pop("newsUpdatedAt", None)
    chk_old.pop("newsUpdatedAt", None)
    for coll in (chk_new, chk_old):
        for s in coll.get("stocks", []):
            s.pop("news", None)
    if canon(chk_new) != canon(chk_old):
        print("⛔ حارس عزل الأخبار: تغيّر حقل خارج news — إجهاض بلا كتابة")
        sys.exit(1)

    tmp = args.data + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, args.data)
    print("📰 الأخبار: حُدّث %d سهماً (فشل %d — أبقى القديم) | ختم %s"
          % (ok, fail, data["newsUpdatedAt"]))


if __name__ == "__main__":
    main()
