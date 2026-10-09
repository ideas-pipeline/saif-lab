#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lab-watch.py — مراقِبٌ لا يعيش على الخادم الذي يراقبه (قرار المالك 09-10).

المبدأ: إن مات خادم المختبر فلن يستطيع أن يُبلّغ عن موته. فالمراقِب يسكن عند GitHub
(Actions) ويعمل بـGITHUB_TOKEN المضمَّن — صفر مفاتيح وصفر بنية — ويقرأ ختم
lastUpdated في stocks-data.json على main:

  · قديم ولا issue مفتوحة بوسم lab-silent  ⇒ ينشئها (وGitHub يُبرِّد المالك — هذه القناة)
  · قديم وissue مفتوحة                      ⇒ تعليق «ما زال صامتاً — اليوم N»
  · طازج وissue مفتوحة                      ⇒ يغلقها بتعليق «عاد التحديث»
  · طازج ولا issue                           ⇒ لا شيء

فالـissue المفتوحة = الحالة الراهنة لا سجلّاً تاريخياً، ولا سيلَ إشعارات.

الاستعمال:
  python3 scripts/lab-watch.py --check-only [--data stocks-data.json]   # محلياً، بلا API
  python3 scripts/lab-watch.py                                           # من الـworkflow

لماذا الختم لا عدّ الإيداعات: الختم يتقدّم مع كل تشغيلة ناجحة حتى في عطلة لا تتحرك
فيها الأسعار، فالإنذار الكاذب لا يقع إلا إن **فشلت** تشغيلةُ عطلة — وهو ما نريد
معرفته أصلاً. ولا معالجة للعطل في الخط كله (مقيس 09-10)، فلا نخترعها هنا.
"""
import json, os, re, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

RIYADH = timezone(timedelta(hours=3))
LABEL = "lab-silent"
TITLE = "⛔ المختبر لم يحدّث اليوم"
TRADING_DAYS = {6, 0, 1, 2, 3}          # الأحد–الخميس (weekday: الاثنين=0)


def stamp_date(data_path):
    """يقرأ lastUpdated («2026-10-07 16:20 الرياض») ويعيد تاريخه نصاً، أو None."""
    with open(data_path, encoding="utf-8") as f:
        head = f.read(4096)              # الملف 3MB؛ الختم في رأسه
    m = re.search(r'"lastUpdated"\s*:\s*"(\d{4}-\d{2}-\d{2})', head)
    return m.group(1) if m else None


def decide(stale, has_open_issue):
    """القرار نقيٌّ ومعزول كي يُختبر على الحالات الأربع بلا شبكة."""
    if stale and not has_open_issue:
        return "create"
    if stale and has_open_issue:
        return "comment"
    if not stale and has_open_issue:
        return "close"
    return "none"


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
    today = now.strftime("%Y-%m-%d")
    stamp = stamp_date(data_path)
    stale = stamp != today
    age = (now.date() - datetime.strptime(stamp, "%Y-%m-%d").date()).days if stamp else None
    print("اليوم (الرياض): %s · آخر ختم: %s · %s" % (today, stamp, "قديم (%s يوم)" % age if stale else "طازج"))

    if "--check-only" in sys.argv:          # محلياً: الحكم يُطبع أياً كان اليوم
        print("حكم: %s" % ("⛔ صامت" if stale else "✅ حيّ"))
        return 0
    if now.weekday() not in TRADING_DAYS:
        # الجمعة والسبت: ختم الخميس هو المتوقَّع (divcal لا يحرّك lastUpdated) — فلا إنذار كاذب
        print("ليس يوم تداول — لا حكم")
        return 0

    gh = GH()
    cur = gh.open_issue()
    action = decide(stale, cur is not None)
    print("القرار: %s" % action)
    if action == "create":
        body = ("آخر تحديث منشور على `main`: **%s** — واليوم **%s** (توقيت الرياض).\n\n"
                "خطّ المختبر لم يُنشر نتيجته اليوم. المنصة تعرض أرقاماً عمرها %s يوم.\n\n"
                "**افحص على الخادم:**\n```\ntail -40 /srv/ideas/lab-runs.log\n```\n"
                "السجل صار يسمّي الأمر الذي قتل الخط (`❌ FAILED … سطر N:`)، أو يقول "
                "`⛔` إن حجبته بوابة.\n\n_تُغلق هذه البطاقة تلقائياً حين يعود التحديث._"
                % (stamp, today, age))
        r = gh.create(body)
        print("أُنشئت issue #%s" % r.get("number"))
    elif action == "comment":
        gh.comment(cur["number"], "ما زال صامتاً — آخر ختم **%s**، اليوم **%s** (%s يوم)." % (stamp, today, age))
        print("عُلِّق على #%s" % cur["number"])
    elif action == "close":
        gh.close(cur["number"], "عاد التحديث — الختم اليوم **%s**. تُغلق." % stamp)
        print("أُغلقت #%s" % cur["number"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
