#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار مراقِب الصمت (scripts/lab-watch.py) بلا شبكة.
يحمل الحادثتين الحقيقيتين (GitHub أخّر الجدولة إلى 23:29 و02:08) وحالة الناقد 13-10
(فحصٌ بين نزول المختبر و17:00). الاستعمال: python3 tests/test_lab_watch.py"""
import importlib.util, os, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("lw", os.path.join(HERE, "..", "scripts", "lab-watch.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
R = m.RIYADH

fails = 0


def check(label, ok):
    global fails
    print(("✅ " if ok else "❌ ") + label)
    fails += 0 if ok else 1


def run(now, daily, weekly):
    """يعيد (اليوم المحكوم، هل هو يوم تداول، (daily_stale, weekly_stale))."""
    t = m.judged_day(now)
    return t, t.weekday() in m.TRADING_DAYS, m.judge(t, daily, weekly)


#  (الوصف، الساعة بالرياض، الختم اليومي، الختم الأسبوعي، اليوم المحكوم المتوقع، (daily, weekly) المتوقع)
CASES = [
    ("حادثة الأحد 11-10 (23:29): أسبوعي بائت فقط",
     datetime(2026, 10, 11, 23, 29, tzinfo=R), "2026-10-11", "2026-09-10", "2026-10-11", (False, True)),
    ("حادثة الاثنين 12-10 (02:08 الثلاثاء): لا إنذار يومي",
     datetime(2026, 10, 13, 2, 8, tzinfo=R), "2026-10-12", "2026-09-10", "2026-10-12", (False, True)),
    ("حالة الناقد: يدوي الثلاثاء 16:45 بعد نزول 16:39",
     datetime(2026, 10, 13, 16, 45, tzinfo=R), "2026-10-13", "2026-10-08", "2026-10-12", (False, False)),
    ("الحد 16:59 ⇒ الأمس",
     datetime(2026, 10, 13, 16, 59, tzinfo=R), "2026-10-12", "2026-10-08", "2026-10-12", (False, False)),
    ("الحد 17:00 ⇒ اليوم",
     datetime(2026, 10, 13, 17, 0, tzinfo=R), "2026-10-13", "2026-10-08", "2026-10-13", (False, False)),
    ("الثلاثاء 19:30 والمختبر فشل",
     datetime(2026, 10, 13, 19, 30, tzinfo=R), "2026-10-12", "2026-10-08", "2026-10-13", (True, False)),
    ("الخميس متأخر إلى فجر الجمعة، الأسبوعي سليم",
     datetime(2026, 10, 16, 1, 30, tzinfo=R), "2026-10-15", "2026-10-15", "2026-10-15", (False, False)),
    ("الخميس متأخر إلى فجر الجمعة، الأسبوعي فشل",
     datetime(2026, 10, 16, 1, 30, tzinfo=R), "2026-10-15", "2026-10-08", "2026-10-15", (False, True)),
    ("ملف غير مقروء (الختمان None) ⇒ إنذار على الاثنين",
     datetime(2026, 10, 13, 19, 30, tzinfo=R), None, None, "2026-10-13", (True, True)),
]

for label, now, d, w, exp_day, exp in CASES:
    t, trade, got = run(now, d, w)
    check("%s ⇒ يوم %s %s" % (label, t, got), t.isoformat() == exp_day and trade and got == exp)

# أيام بلا حكم: الأحد صباحاً يُنسب إلى السبت، والجمعة مساءً إلى الجمعة
for label, now in [("الأحد 09:00 يدوي", datetime(2026, 10, 11, 9, 0, tzinfo=R)),
                   ("الجمعة 19:30", datetime(2026, 10, 16, 19, 30, tzinfo=R))]:
    t = m.judged_day(now)
    check("%s ⇒ %s ليس يوم تداول" % (label, t), t.weekday() not in m.TRADING_DAYS)

# قرار البطاقة: الحالات الأربع
for stale, has, exp in [(True, False, "create"), (True, True, "comment"),
                        (False, True, "close"), (False, False, "none")]:
    check("decide(stale=%s, open=%s) = %s" % (stale, has, exp), m.decide(stale, has) == exp)

print("\n%s" % ("الكل سليم" if not fails else "فشل %d" % fails))
sys.exit(1 if fails else 0)
