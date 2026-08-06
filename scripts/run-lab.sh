#!/bin/bash
# run-lab.sh — خط تشغيل المختبر المستقل (sahmk-direct-v3)
# =========================================================
# يجسد قيود جدولة الناقد الثلاثة (ختم 05-08ب):
#   1) مسارات صريحة في كل استدعاء (لا افتراضيات إنتاجية)
#   2) يُجدول بعد الإقفال (>15:10 الرياض) — وإلا runType=intraday فيتعطل المغذي بالتصميم
#   3) ترتيب الخط: جالب ← محرك ← مغذٍ/إغلاقات ← L1 على الملف ذاته
#
# الاستخدام:  run-lab.sh [daily|weekly|universe]
# الجدولة المقترحة (crontab — توقيت السيرفر الرياض):
#   50 16 * * 0-3  /srv/ideas/lab-mirror/scripts/run-lab.sh daily    >> /srv/ideas/lab-runs.log 2>&1
#   50 16 * * 4    /srv/ideas/lab-mirror/scripts/run-lab.sh weekly   >> /srv/ideas/lab-runs.log 2>&1
#   30 17 1 * *    /srv/ideas/lab-mirror/scripts/run-lab.sh universe >> /srv/ideas/lab-runs.log 2>&1
set -e
LAB="/srv/ideas/lab-mirror"
KEYFILE="/srv/ideas/.sahmk.key"
MODE="${1:-daily}"

cd "$LAB"
exec 200>.lab.lock
flock -w 900 200 || { echo "⛔ تشغيلة أخرى قائمة — انسحاب"; exit 1; }

echo "════ run-lab [$MODE] $(date '+%Y-%m-%d %H:%M') ════"

# درس انسداد git الموثق: index.html ناتج بناء محلي يعيق pull
git checkout -- index.html 2>/dev/null || true
git pull -q origin main

export SAHMK_KEY="$(cat "$KEYFILE")"
DATA="$LAB/stocks-data.json"

case "$MODE" in
  weekly)   python3 scripts/fetch-inputs-sahmk.py --data "$DATA" --weekly ;;
  universe) python3 scripts/fetch-inputs-sahmk.py --data "$DATA" --maintain-universe
            python3 scripts/fetch-inputs-sahmk.py --data "$DATA" ;;
  *)        python3 scripts/fetch-inputs-sahmk.py --data "$DATA" ;;
esac

python3 scripts/scoring-engine.py "$DATA"

# المغذي والإغلاقات — مسارات صريحة، ويرفضان ذاتياً أي ملف intraday/بلا ختم
STOCKS_JSON="$DATA" CONFIG_JSON="$LAB/watchlist-config.json" ARCHIVE_DIR="$LAB/archive" \
  bash scripts/feed-watchlist.sh
STOCKS_JSON="$DATA" CONFIG_JSON="$LAB/watchlist-config.json" ARCHIVE_DIR="$LAB/archive" \
  python3 scripts/close_sma200w.py

python3 build.py
python3 scripts/self-check-L1.py "$DATA"

# الطبقة 2 (أسبوعي): التقرير الوصفي — فشله يُنبه ولا يُسقط السلسلة (قرار مقر 05-08ب)،
# ويسبق النشر كي يُدفع docs/weekly-digest.md مع التشغيلة
if [ "$MODE" = "weekly" ]; then
  python3 scripts/lab-digest.py --data "$DATA" \
    --config "$LAB/watchlist-config.json" --out "$LAB/docs/weekly-digest.md" \
    || echo "⚠️ ALERT: lab-digest فشل — التشغيلة تكمل"
fi

# النشر: إيداع ودفع نتائج التشغيلة (يغذي GitHub Pages)
git add -A
if ! git diff --cached --quiet; then
  git -c user.email="server@saif" -c user.name="server" commit -qm "lab: تشغيلة $MODE آلية"
  git push -q origin main
  echo "✅ نُشر"
else
  echo "ℹ️ لا تغييرات للنشر"
fi
echo "════ اكتمل [$MODE] $(date '+%H:%M') ════"
