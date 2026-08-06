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

# تحصين ضد التحديث الذاتي (06-08): git pull الداخلي قد يحدّث هذا الملف أثناء تنفيذه،
# وbash يقرأ السكربتات تزايدياً — لذا التنفيذ الفعلي يجري دائماً من نسخة مؤقتة تحذف نفسها.
if [ -z "$RUNLAB_EXEC_COPY" ]; then
  cp -- "$0" "$LAB/.run-lab.exec.$$"
  export RUNLAB_EXEC_COPY="$LAB/.run-lab.exec.$$"
  exec bash "$RUNLAB_EXEC_COPY" "$@"
fi
trap 'rm -f -- "$RUNLAB_EXEC_COPY"' EXIT

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

# تحقق نشر Pages (مقتبس من نمط stocks-push.sh المجرب — حادثة فشل Pages الصامت 06-08)
verify_pages() {
  local sha rsha status concl res i
  sha=$(git rev-parse HEAD)
  for i in $(seq 1 9); do
    sleep 10
    res=$(curl -s -m 20 "https://api.github.com/repos/ideas-pipeline/saif-lab/actions/runs?per_page=1" \
      | python3 -c "import json,sys; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['head_sha'], r['status'], r['conclusion'])" 2>/dev/null || true)
    rsha=$(echo "$res" | cut -d' ' -f1); status=$(echo "$res" | cut -d' ' -f2); concl=$(echo "$res" | cut -d' ' -f3)
    if [ "$rsha" = "$sha" ] && [ "$status" = "completed" ]; then echo "$concl"; return; fi
  done
  echo "timeout"
}

# النشر: إيداع ودفع نتائج التشغيلة (يغذي GitHub Pages) + تأكيد النشر
git add -A
if ! git diff --cached --quiet; then
  git -c user.email="server@saif" -c user.name="server" commit -qm "lab: تشغيلة $MODE آلية"
  git push -q origin main
  RESULT=$(verify_pages)
  if [ "$RESULT" = "success" ]; then
    echo "✅ نُشر ونشر Pages مؤكد"
  elif [ "$RESULT" = "failure" ]; then
    echo "⚠️ نشر Pages فشل — إعادة إطلاق تلقائية (إيداع فارغ)"
    git -c user.email="server@saif" -c user.name="server" commit -q --allow-empty -m "retrigger pages deploy"
    git push -q origin main
    RESULT2=$(verify_pages)
    if [ "$RESULT2" = "success" ]; then echo "✅ نشر Pages نجح بعد إعادة الإطلاق"
    else echo "❌ ALERT: نشر Pages فشل نهائياً ($RESULT2) — تدخل يدوي"; fi
  else
    echo "⚠️ لم يُحسم فحص Pages ($RESULT) — راجع يدوياً"
  fi
else
  echo "ℹ️ لا تغييرات للنشر"
fi
echo "════ اكتمل [$MODE] $(date '+%H:%M') ════"
