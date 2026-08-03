#!/bin/bash
# الدفع اليومي الآلي لمستودع الاحتياطي — يعمل بعد لقطة 17:00
# يخرج دائماً بـ0 كي لا يزعج cron
cd /srv/ideas || exit 0
git add -A
if git diff --cached --quiet; then
  echo "$(date "+%F %H:%M") — لا تغييرات"
  exit 0
fi
git commit -q -m "backup: auto $(date "+%F")"
if git push -q origin master 2>/dev/null; then
  echo "$(date "+%F %H:%M") ✅ $(git --no-pager log -1 --format=%h) — $(git --no-pager show --stat --oneline HEAD | tail -1)"
else
  echo "$(date "+%F %H:%M") ❌ فشل الدفع — النسخة محفوظة محلياً"
fi
exit 0
