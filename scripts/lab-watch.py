#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lab-watch.py — مراقِبٌ لا يعيش على الخادم الذي يراقبه (قرار المالك 09-10).

المبدأ: إن مات خادم المختبر فلن يستطيع أن يُبلّغ عن موته. فالمراقِب يسكن عند GitHub
(Actions) ويعمل بـGITHUB_TOKEN المضمَّن — صفر مفاتيح وصفر بنية — ويحكم على **ختمين**
في stocks-data.json على main:

  · اليومي:   lastUpdated يجب أن يكون اليوم (في أيام التداول).
  · الأسبوعي: أكبر financialsUpdated عبر الأسهم يجب ألّا يسبق **آخر خميس**.
    (شرط ختم 09-10: الخميس على مرحلتين يختم lastUpdated كل خميس حتى لو فشلت
     الإضافات — فمراقِبٌ يقرأ الختم اليومي وحده يصير أعمى عن فشل الجلب الأسبوعي
     بعينه. والدليل يوم الإدخال: 244 من 248 سهماً financialsUpdated=2026-09-10 —
     أي أن الجلب الأسبوعي فشل أربعة خميسات متتالية — 5 من آخر 6 — ولم يرَه أحد.)

  · صامت ولا issue مفتوحة بوسم lab-silent  ⇒ ينشئها (وGitHub يُبرِّد المالك — هذه القناة)
  · صامت وissue مفتوحة                      ⇒ تعليق «ما زال صامتاً»
  · حيّ وissue مفتوحة                       ⇒ يغلقها بتعليق «عاد التحديث»
  · حيّ ولا issue                            ⇒ لا شيء

فالـissue المفتوحة = الحالة الراهنة لا سجلّاً تاريخياً، ولا سيلَ إشعارات. و«صامت» =
أحد الختمين متأخر، والجسم يسمّي أيّهما.

الاستعمال:
  python3 scripts/lab-watch.py --check-only [--data stocks-data.json]   # محلياً، بلا API
  python3 scripts/lab-watch.py                                           # من الـworkflow

لماذا الختم لا عدّ الإيداعات: الختم اليومي يتقدّم مع كل تشغيلة ناجحة حتى في عطلة لا
تتحرك فيها الأسعار، فالإنذار الكاذب لا يقع إلا إن **فشلت** تشغيلةُ عطلة — وهو ما نريد
معرفته أصلاً. ولا معالجة للعطل في الخط كله (مقيس 09-10)، فلا نخترعها هنا.
"""
import json, os, re, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

RIYADH = timezone(timedelta(hours=3))
LABEL = "lab-silent"
TITLE = "⛔ المختبر: تحديث متأخر"
TRADING_DAYS = {6, 0, 1, 2, 3}          # الأحد–الخميس (weekday: الاثنين=0)
THURSDAY = 3
CUTOFF_HOUR = 17                        # قبلها يُحسب الفحص على اليوم السابق
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_stamps(data_path):
    """يعيد (تاريخ lastUpdated، أكبر financialsUpdated) نصّين أو None لكلٍّ.
    ملفٌ غير قابل للقراءة ⇒ (None, None) — اتجاهٌ آمن: إنذار لا صمت."""
    try:
        with open(data_path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:                       # noqa: BLE001 — أي عطب في الملف = صامت
        print("⚠️ تعذّرت قراءة البيانات: %s" % e)
        return None, None
    # الختم يُقبل تاريخاً فقط: المقارنة نصّية، فـ«N/A» يُرتَّب بعد «2026» ويُقرأ «حيّاً»
    # فيسكت المراقِب (ملاحظة ختم 13-10). وما ليس تاريخاً ⇒ None ⇒ إنذار.
    def date_or_none(v):
        v = str(v or "")[:10]
        return v if DATE_RE.match(v) else None
    lu = date_or_none(d.get("lastUpdated"))
    fu = [date_or_none(s.get("financialsUpdated")) for s in d.get("stocks", [])]
    fu = [x for x in fu if x]
    return lu, (max(fu) if fu else None)


def judged_day(now):
    """اليوم الذي يُحكم عليه، لا يوم الساعة الجدارية.
    GitHub يؤخّر الجدولة ساعات (مقيس: موعد 19:30 نزل 23:29 الأحد و02:08 فجر الثلاثاء)،
    ففحصٌ يقع بعد منتصف الليل كان يطالب بتحديث يومٍ لم يحن موعده — إنذار كاذب 12-10.
    فما قبل 17:00 الرياض يُنسب إلى اليوم السابق: تحديث اليوم نفسه (~16:35) لم يُنتظر بعد."""
    d = now.date()
    return d - timedelta(days=1) if now.hour < CUTOFF_HOUR else d


def last_thursday(today):
    """آخر خميس ≤ اليوم (اليوم نفسه إن كان خميساً)."""
    return today - timedelta(days=(today.weekday() - THURSDAY) % 7)


def judge(today, daily_stamp, weekly_stamp):
    """يعيد (daily_stale, weekly_stale) — نقيٌّ ومعزول للاختبار."""
    # «أقدم من» لا «يخالف»: فحصٌ قبل 17:00 يُحكم به على الأمس، فإن كان المختبر قد نزل
    # اليوم (~16:35) فختمه أحدث من المحكوم — دليل حياة لا تأخّر (شرط ختم 13-10).
    daily_stale = (daily_stamp is None) or (daily_stamp < today.isoformat())
    weekly_stale = (weekly_stamp is None) or (weekly_stamp < last_thursday(today).isoformat())
    return daily_stale, weekly_stale


def decide(stale, has_open_issue):
    """القرار نقيٌّ ومعزول كي يُختبر على الحالات الأربع بلا شبكة."""
    if stale and not has_open_issue:
        return "create"
    if stale and has_open_issue:
        return "comment"
    if not stale and has_open_issue:
        return "close"
    return "none"


def status_lines(today, daily_stamp, weekly_stamp, daily_stale, weekly_stale):
    lt = last_thursday(today).isoformat()
    a = ("**اليومي**: آخر ختم %s — %s" %
         (daily_stamp, "⛔ متأخر" if daily_stale else "✅ اليوم"))
    b = ("**الأسبوعي (القوائم المالية)**: آخر ختم %s — %s" %
         (weekly_stamp, ("⛔ أقدم من آخر خميس (%s)" % lt) if weekly_stale else "✅ حديث"))
    return a, b


class GH:
    def __init__(self):
        self.repo = os.environ["GITHUB_REPOSITORY"]
        self.tok = os.environ["GITHUB_TOKEN"]

    def _req(self, method, path, body=None):
        req = urllib.request.Request(
            "https://api.github.com/repos/%s%s" % (self.repo, path),
            data=json.dumps(body).encode() if body is not None else None, method=method,
            headers={"Authorization": "Bearer " + self.tok, "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r) if r.status != 204 else None

    def open_issue(self):
        rows = self._req("GET", "/issues?state=open&labels=%s&per_page=5" % LABEL)
        return rows[0] if rows else None

    def create(self, body):
        return self._req("POST", "/issues", {"title": TITLE, "body": body, "labels": [LABEL]})

    def comment(self, num, body):
        return self._req("POST", "/issues/%d/comments" % num, {"body": body})

    def close(self, num, body):
        self.comment(num, body)
        return self._req("PATCH", "/issues/%d" % num, {"state": "closed", "state_reason": "completed"})


def main():
    data_path = "stocks-data.json"
    if "--data" in sys.argv:
        data_path = sys.argv[sys.argv.index("--data") + 1]
    now = datetime.now(RIYADH)
    today = judged_day(now)
    daily_stamp, weekly_stamp = read_stamps(data_path)
    daily_stale, weekly_stale = judge(today, daily_stamp, weekly_stamp)
    stale = daily_stale or weekly_stale
    a, b = status_lines(today, daily_stamp, weekly_stamp, daily_stale, weekly_stale)
    print("الساعة (الرياض): %s ⇒ يُحكم على يوم %s" % (now.strftime("%Y-%m-%d %H:%M"), today))
    print("  " + a.replace("**", ""))
    print("  " + b.replace("**", ""))

    if "--check-only" in sys.argv:          # محلياً: الحكم يُطبع أياً كان اليوم
        print("حكم: %s" % ("⛔ صامت" if stale else "✅ حيّ"))
        return 0
    if today.weekday() not in TRADING_DAYS:
        # الجمعة والسبت: ختم الخميس هو المتوقَّع (divcal لا يحرّك lastUpdated) — فلا إنذار كاذب.
        # ويُقرأ اليوم المحكوم لا الجداري: فحص الخميس المتأخر إلى فجر الجمعة يبقى فحصَ خميس.
        print("ليس يوم تداول — لا حكم")
        return 0

    gh = GH()
    cur = gh.open_issue()
    action = decide(stale, cur is not None)
    print("القرار: %s" % action)
    if action == "create":
        body = ("%s\n%s\n\n(توقيت الرياض، يوم %s.)\n\n"
                "**افحص على الخادم:**\n```\ntail -60 /srv/ideas/lab-runs.log\n```\n"
                "السجل يسمّي الأمر الذي قتل الخط (`❌ FAILED … سطر N:`)، أو يقول `⛔` إن حجبته "
                "بوابة، أو `❌ ALERT: الإضافات الأسبوعية فشلت` إن نُشر الأساسي وحده يوم الخميس.\n\n"
                "_تُغلق هذه البطاقة تلقائياً حين يعود الختمان._" % (a, b, today))
        r = gh.create(body)
        print("أُنشئت issue #%s" % r.get("number"))
    elif action == "comment":
        gh.comment(cur["number"], "ما زال متأخراً (%s):\n%s\n%s" % (today, a, b))
        print("عُلِّق على #%s" % cur["number"])
    elif action == "close":
        gh.close(cur["number"], "عاد التحديث (%s):\n%s\n%s\nتُغلق." % (today, a, b))
        print("أُغلقت #%s" % cur["number"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
