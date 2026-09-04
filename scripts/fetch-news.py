#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""جالب أخبار الأسهم — تخصيص للسهم + ترتيب زمني + تغطية موسّعة (v2، 04-09).

السياق: v1 (22-08) أنهت تجمد الأخبار منذ 29-07، لكنها كانت استعلاماً واحداً
بترتيب «الصلة» من جوجل (لا الأحدث) بلا أي تحقق أن الخبر يخص السهم فعلاً.
طلب المالك (04-09): موثوقية التخصيص + ترتيب من الأحدث + تغطية أوسع للصحف
المالية (أرقام، مباشر، مال، الاقتصادية…).

ما تفعله v2:
 1. استعلامان لكل سهم (عام + مادي) وثالث موجَّه للمصادر عند شح النتائج (تكيّفي).
 2. بوابة تخصيص: العنوان يجب أن يحمل اسم السهم كاملاً، أو رمزه ككلمة مستقلة،
    أو كل كلماته المميزة — وإلا يُسقط.
 3. حارس الخلط بين الشركات (نمط حادثة 2060/2080): عنوان يحمل اسم شركة أخرى
    من كوننا ولا يحمل اسمنا ⇒ يُسقط قطعاً.
 4. إزالة التكرار عبر المصادر (بالعنوان المطبَّع وبالرابط).
 5. ترتيب تنازلي بالتاريخ الفعلي + حقل dateIso + وسم `trusted` للمصادر المالية.

الكتابة معزولة في news[] + newsUpdatedAt حصراً (حارس مطابقة قانونية)، وفشل
جلب سهمٍ يُبقي أخباره القديمة كما هي.

الاستخدام: python3 scripts/fetch-news.py --data stocks-data.json [--limit N] [--symbols 1120,2222]
"""
import argparse
import copy
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

RATE_SLEEP = 0.6          # ~100 طلب/دقيقة — احترام للمصدر المجاني
TIMEOUT = 8
KEEP = 6                  # أخبار محفوظة لكل سهم
MAX_AGE_DAYS = 150        # سقف عمر الخبر (مع سقوط آمن إن خلت النتائج)
DEEP_THRESHOLD = 2        # أقل من هذا العدد ⇒ استعلام ثالث موجَّه للمصادر

# مصادر مالية موثوقة (وسم عرضي — لا إسقاط لغيرها)
TRUSTED = {
    "argaam": "أرقام", "mubasher": "مباشر", "maaal": "مال", "aleqt": "الاقتصادية",
    "alarabiya": "العربية", "cnbcarabia": "CNBC عربية", "asharqbusiness": "الشرق",
    "saudiexchange": "تداول", "spa.gov.sa": "واس", "alyaum": "اليوم",
    "alriyadh": "الرياض", "okaz": "عكاظ", "aleqtisadiah": "الاقتصادية",
    "sabq": "سبق", "ajel": "عاجل", "arabnews": "Arab News", "reuters": "رويترز",
    "bloomberg": "بلومبرغ", "zawya": "زاوية", "attaqa": "الطاقة",
}
# استعلامات موجَّهة للصحف المالية عند شح النتائج
SITE_QUERY = ("site:argaam.com OR site:mubasher.info OR site:maaal.com "
              "OR site:aleqt.com OR site:cnbcarabia.com")
# كلمات الأحداث المادية — تُوسّع التغطية لما يهم المستثمر
MATERIAL = "(نتائج OR أرباح OR توزيعات OR صفقة OR استحواذ OR عقد OR اكتتاب OR رأس المال)"

# كلمات عامة لا تميّز شركة بعينها
GENERIC = {"شركه", "مجموعه", "القابضه", "السعوديه", "العربيه", "المتحده", "الوطنيه",
           "للاستثمار", "الاستثماريه", "للتنميه", "التنميه", "صندوق", "ريت",
           "للتامين", "التعاوني", "للصناعه", "الصناعيه", "التجاريه", "المحدوده",
           "والتنميه", "الخليجيه", "العالميه", "المتطوره", "الحديثه", "بنك", "مصرف",
           "شركات", "القابضة", "اسمنت", "مدينه", "العقاريه", "التجاري"}


def norm(s):
    """تطبيع عربي: الهمزات والتاء المربوطة والألف المقصورة والتطويل والتشكيل"""
    s = str(s or "")
    s = re.sub(r"[ً-ْـ]", "", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def distinctive(name_norm):
    """كلمات الاسم المميزة (تستبعد العام) — أساس المطابقة الاحتياطية"""
    return [t for t in name_norm.split() if len(t) >= 4 and t not in GENERIC]


def fetch_rss(query):
    """استعلام Google News RSS العربي — يعيد قائمة عناصر أو None عند الفشل"""
    try:
        url = ("https://news.google.com/rss/search?q=%s&hl=ar&gl=SA&ceid=SA:ar"
               % urllib.parse.quote(query))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=TIMEOUT).read())
        out = []
        for it in root.findall(".//item"):
            g = lambda tag: (it.find(tag).text or "") if it.find(tag) is not None else ""
            out.append({"title": g("title"), "date": g("pubDate"),
                        "source": g("source"), "url": g("link")})
        return out
    except Exception:
        return None


def epoch_of(item):
    try:
        return parsedate_to_datetime(item.get("date") or "").timestamp()
    except Exception:
        return 0.0


def iso_of(item):
    try:
        return parsedate_to_datetime(item["date"]).strftime("%Y-%m-%d")
    except Exception:
        return ""


def trusted_of(item):
    blob = (str(item.get("url") or "") + " " + str(item.get("source") or "")).lower()
    for key in TRUSTED:
        if key in blob:
            return True
    return False


def clean_title(t):
    """عنوان جوجل يذيّل المصدر بـ« - المصدر» — يُزال للمقارنة والعرض"""
    return re.sub(r"\s+-\s+[^-]{2,40}$", "", str(t or "")).strip()


def is_about(title, sym, name_norm, dist, other_names):
    """بوابة التخصيص + حارس الخلط بين الشركات. تعيد (مقبول، السبب)"""
    tn = norm(title)
    if not tn:
        return False, "عنوان فارغ"
    mine = (name_norm and name_norm in tn) or bool(re.search(r"(?<!\d)%s(?!\d)" % re.escape(sym), tn))
    if not mine and dist:
        mine = all(t in tn for t in dist)
    # حارس الخلط: اسم شركة أخرى حاضر واسمنا غائب ⇒ إسقاط قاطع (نمط 2060/2080)
    if not mine:
        return False, "لا يخص السهم"
    for other in other_names:
        if other != name_norm and len(other) >= 8 and other in tn and name_norm not in tn:
            return False, "خلط مع شركة أخرى"
    return True, ""


def gather(stock, other_names, counters):
    """يجمع من الاستعلامات، يرشّح بالتخصيص، يزيل التكرار، ويرتب بالأحدث"""
    name = stock.get("name") or stock["symbol"]
    sym = str(stock["symbol"])
    name_norm, dist = norm(name), distinctive(norm(name))
    queries = ['%s سهم' % name, '%s %s' % (name, MATERIAL)]
    seen_url, seen_title, kept, any_ok = set(), set(), [], False

    def absorb(items):
        nonlocal kept
        for it in items:
            it["title"] = clean_title(it.get("title"))
            ok, _ = is_about(it["title"], sym, name_norm, dist, other_names)
            if not ok:
                counters["dropped"] += 1
                continue
            key = norm(it["title"])[:90]
            if it.get("url") in seen_url or key in seen_title:
                counters["dupes"] += 1
                continue
            seen_url.add(it.get("url")); seen_title.add(key)
            it["_e"] = epoch_of(it); it["dateIso"] = iso_of(it)
            it["trusted"] = trusted_of(it)
            kept.append(it)

    for q in queries:
        res = fetch_rss(q)
        time.sleep(RATE_SLEEP)
        if res is None:
            continue
        any_ok = True
        absorb(res)
    # تعميق تكيّفي: استعلام موجَّه للصحف المالية حين تشح النتائج
    if any_ok and len(kept) < DEEP_THRESHOLD:
        res = fetch_rss('%s %s' % (name, SITE_QUERY))
        time.sleep(RATE_SLEEP)
        if res is not None:
            counters["deep"] += 1
            absorb(res)
    if not any_ok:
        return None            # فشل شبكي كامل ⇒ لا مساس بالقديم

    kept.sort(key=lambda x: x["_e"], reverse=True)
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    fresh = [x for x in kept if x["_e"] >= cutoff]
    final = (fresh or kept)[:KEEP]     # سقوط آمن: لا تُفرَّغ الأخبار لمجرد قِدمها
    return [{"title": x["title"][:140], "date": x.get("date", ""), "dateIso": x["dateIso"],
             "source": x.get("source", ""), "url": x.get("url", ""),
             "trusted": x["trusted"]} for x in final]


def canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--limit", type=int, default=0, help="اختبار: أول N سهماً")
    ap.add_argument("--symbols", default="", help="اختبار: رموز محددة")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    baseline = copy.deepcopy(data)
    allstocks = [s for s in data.get("stocks", []) if s.get("symbol") and not s.get("delisted")]
    other_names = [norm(s.get("name") or "") for s in allstocks]

    stocks = allstocks
    if args.symbols:
        want = {x.strip() for x in args.symbols.split(",") if x.strip()}
        stocks = [s for s in stocks if s["symbol"] in want]
    if args.limit:
        stocks = stocks[: args.limit]

    counters = {"dropped": 0, "dupes": 0, "deep": 0}
    ok = fail = empty = 0
    for s in stocks:
        got = gather(s, other_names, counters)
        if got is None:
            fail += 1
            continue
        s["news"] = got
        ok += 1
        if not got:
            empty += 1

    if ok == 0:
        print("⛔ الأخبار: صفر نجاح من %d — لا كتابة (تبقى الأخبار القديمة بختمها)" % len(stocks))
        sys.exit(1)

    data["newsUpdatedAt"] = time.strftime("%Y-%m-%d %H:%M")

    # حارس العزل: لا يتغير شيء خارج news[] وnewsUpdatedAt
    a, b = copy.deepcopy(data), copy.deepcopy(baseline)
    for coll in (a, b):
        coll.pop("newsUpdatedAt", None)
        for st in coll.get("stocks", []):
            st.pop("news", None)
    if canon(a) != canon(b):
        print("⛔ حارس عزل الأخبار: تغيّر حقل خارج news — إجهاض بلا كتابة")
        sys.exit(1)

    tmp = args.data + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, args.data)
    print("📰 الأخبار v2: حُدّث %d سهماً (فشل %d | بلا أخبار %d) | أُسقط غير مخصص %d | "
          "مكرر %d | تعميق %d | ختم %s"
          % (ok, fail, empty, counters["dropped"], counters["dupes"], counters["deep"],
             data["newsUpdatedAt"]))


if __name__ == "__main__":
    main()
